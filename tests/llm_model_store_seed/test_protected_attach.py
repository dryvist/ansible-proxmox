#!/usr/bin/env python3
"""The models-mount attach works on a protected container and leaves it protected.

Runs the task's own shell script against a fake `pct` that refuses disk changes
while protection=1, as Proxmox does. Also renders the task's mount spec: pct
takes a new volume size as plain GiB (`storage:120`), never `120G`.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import jinja2
import yaml
from ansible.plugins.filter.core import regex_replace

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
ATTACH = next(t for t in tasks if t.get("name") == "Attach each missing models mount (pct set)")
ARGV = ATTACH["ansible.builtin.command"]["argv"]
SCRIPT = ARGV[2]
SPEC = ARGV[-1]


def render_spec(size, read_only=False):
    env = jinja2.Environment()
    env.filters["regex_replace"] = regex_replace
    item = {"models_mount_storage": "bulk", "models_mount_size": size, "models_mount_path": "/var/lib/llm",
            "models_mount_read_only": read_only}
    return env.from_string(SPEC).render(item=item)


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
        rc = subprocess.run(["sh", "-c", SCRIPT, "sh", "503010", "--mp1", "bulk:120,mp=/var/lib/llm"],
                            env=env).returncode
        return rc, state.read_text().strip(), log.read_text()


rc, state, log = run(1)
assert rc == 0 and state == "1" and "set 503010 --mp1 bulk:120,mp=/var/lib/llm" in log, (rc, state, log)
rc, state, log = run(0)
assert rc == 0 and state == "0" and "--protection" not in log, (rc, log)
rc, state, _ = run(1, fail_mp=True)
assert rc != 0 and state == "1", (rc, state)
assert render_spec("120G") == "bulk:120,mp=/var/lib/llm", render_spec("120G")
assert render_spec("120") == "bulk:120,mp=/var/lib/llm", render_spec("120")
assert render_spec("120G", read_only=True) == "bulk:120,mp=/var/lib/llm,ro=1", render_spec("120G", True)
print("ok")
