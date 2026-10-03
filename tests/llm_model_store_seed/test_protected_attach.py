#!/usr/bin/env python3
"""The models-mount attach works on a protected container and leaves it protected.

Runs the task's own shell script against a fake `pct` that refuses disk changes
while protection=1, as Proxmox does.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import yaml

TASK_FILE = Path(__file__).resolve().parents[2] / "roles/llm_model_store_seed/tasks/attach_missing_mounts.yml"

FAKE_PCT = """#!/bin/sh
echo "$*" >> "$LOG"
case "$1 $3" in
  "config "*) echo "protection: $(cat "$STATE")"; exit 0 ;;
  "set --protection") echo "$4" > "$STATE"; exit 0 ;;
esac
[ "$(cat "$STATE")" = 1 ] && exit 25
[ "${FAIL_MP:-0}" = 1 ] && exit 3
exit 0
"""

tasks = yaml.safe_load(TASK_FILE.read_text())
SCRIPT = next(t for t in tasks if t.get("name") == "Attach each missing models mount (pct set)")[
    "ansible.builtin.command"]["argv"][2]


def run(protected, fail_mp=False):
    with tempfile.TemporaryDirectory() as d:
        pct = Path(d, "pct")
        pct.write_text(FAKE_PCT)
        pct.chmod(0o755)
        state, log = Path(d, "state"), Path(d, "log")
        state.write_text(str(protected))
        log.write_text("")
        env = dict(os.environ, PATH=f"{d}:{os.environ['PATH']}", STATE=str(state), LOG=str(log),
                   FAIL_MP=str(int(fail_mp)))
        rc = subprocess.run(["sh", "-c", SCRIPT, "sh", "503010", "--mp1", "bulk:120G,mp=/var/lib/llm"],
                            env=env).returncode
        return rc, state.read_text().strip(), log.read_text()


rc, state, log = run(1)
assert rc == 0 and state == "1" and "set 503010 --mp1 bulk:120G,mp=/var/lib/llm" in log, (rc, state, log)
rc, state, log = run(0)
assert rc == 0 and state == "0" and "--protection" not in log, (rc, log)
rc, state, _ = run(1, fail_mp=True)
assert rc != 0 and state == "1", (rc, state)
print("ok")
