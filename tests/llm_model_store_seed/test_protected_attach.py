#!/usr/bin/env python3
"""The models-mount attach must work on a protected container and leave it protected.

Proxmox refuses every disk change while `protection=1`, including a new mpN, so the
attach lifts protection for the one `pct set` and always restores it. This runs the
task's own shell script against a fake `pct` that enforces that refusal.
"""

import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

TASK_FILE = (
    Path(__file__).resolve().parents[2]
    / "roles/llm_model_store_seed/tasks/attach_missing_mounts.yml"
)

# Fake pct: state in $STATE (protection flag), every call logged to $LOG.
# A disk change while protected fails, as on a real node. FAIL_MP=1 forces the
# mount itself to fail so the restore-on-failure path is exercised.
FAKE_PCT = """#!/bin/sh
echo "$*" >> "$LOG"
if [ "$3" = --protection ]; then echo "$4" > "$STATE"; exit 0; fi
[ "$(cat "$STATE")" = 1 ] && { echo "protection mode enabled" >&2; exit 25; }
[ "${FAIL_MP:-0}" = 1 ] && exit 3
exit 0
"""


def attach_script():
    tasks = yaml.safe_load(TASK_FILE.read_text())
    task = next(t for t in tasks if t.get("name") == "Attach each missing models mount (pct set)")
    argv = task["ansible.builtin.command"]["argv"]
    assert argv[:2] == ["sh", "-c"], argv[:2]
    return argv[2]


def run(script, protected, fail_mp=False):
    with tempfile.TemporaryDirectory() as d:
        pct = Path(d, "pct")
        pct.write_text(FAKE_PCT)
        pct.chmod(pct.stat().st_mode | stat.S_IEXEC)
        state, log = Path(d, "state"), Path(d, "log")
        state.write_text(f"{protected}\n")
        log.write_text("")
        env = dict(os.environ, PATH=f"{d}:{os.environ['PATH']}", STATE=str(state), LOG=str(log),
                   FAIL_MP="1" if fail_mp else "0")
        rc = subprocess.run(["sh", "-c", script, "sh", "503010", "--mp1", "bulk:120G,mp=/var/lib/llm",
                             str(protected)], env=env).returncode
        return rc, state.read_text().strip(), log.read_text().splitlines()


def main():
    script = attach_script()
    failures = []

    rc, state, log = run(script, 1)
    if rc != 0 or state != "1" or "503010 --mp1 bulk:120G,mp=/var/lib/llm" not in " ".join(log):
        failures.append(f"protected attach: rc={rc} state={state} log={log}")

    rc, state, log = run(script, 0)
    if rc != 0 or state != "0" or any("--protection" in line for line in log):
        failures.append(f"unprotected attach must not touch protection: rc={rc} log={log}")

    rc, state, _ = run(script, 1, fail_mp=True)
    if rc == 0 or state != "1":
        failures.append(f"failed attach must fail AND restore protection: rc={rc} state={state}")

    for f in failures:
        print(f"FAIL {f}")
    print("ok" if not failures else f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
