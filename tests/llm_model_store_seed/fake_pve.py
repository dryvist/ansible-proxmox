#!/usr/bin/env python3
"""Stand-in for the PVE CLIs the llm_model_store_seed removal tasks call.

Run as `python3 fake_pve.py <pct|pvesh|pvesm> ...` through wrappers named like the CLIs in a scratch
bin directory by verify_duplicate_removal.yml. State lives in the JSON file at
$FAKE_PVE_STATE; every state change is appended to $FAKE_PVE_LOG.

state = {
  "vmid": 503000, "protection": 0, "status": "running",
  "detach_pending_while_running": false,   # real PVE queues an mp delete on a running CT
  "root": "<dir holding one subdirectory per volume name>",
  "config": {"mp0": "<volid>,mp=...", ...}, "pending_delete": []
}
"""

import json
import os
import shutil
import sys
from pathlib import Path

STATE = Path(os.environ["FAKE_PVE_STATE"])
LOG = Path(os.environ["FAKE_PVE_LOG"])
state = json.loads(STATE.read_text())


def log(line):
    with LOG.open("a") as f:
        f.write(line + "\n")


def save():
    STATE.write_text(json.dumps(state))


def volid(value):
    return value.split(",")[0]


def detach(key):
    value = state["config"].pop(key)
    free = next(i for i in range(100) if f"unused{i}" not in state["config"])
    state["config"][f"unused{free}"] = volid(value)
    log(f"detach {key} {volid(value)}")


def pvesh(args):
    path = args[1]
    if path.endswith("/config"):
        print(json.dumps(state["config"]))
    elif path.endswith("/pending"):
        rows = [{"key": k, "value": v} for k, v in state["config"].items()]
        for row in rows:
            if row["key"] in state["pending_delete"]:
                row["delete"] = 1
        print(json.dumps(rows))
    elif path.endswith("/status/current"):
        print(json.dumps({"status": state["status"], "vmid": state["vmid"]}))
    else:
        sys.exit(f"fake pvesh: unhandled {args}")


def pvesm(args):
    if args[0] != "path":
        sys.exit(f"fake pvesm: unhandled {args}")
    print(Path(state["root"], args[1].split(":", 1)[1]))


def pct(args):
    cmd = args[0]
    if cmd == "config":
        print(f"protection: {state['protection']}")
        for k, v in state["config"].items():
            print(f"{k}: {v}")
    elif cmd == "reboot":
        for key in state.pop("pending_delete", []):
            detach(key)
        state["pending_delete"] = []
        log(f"reboot {args[1]}")
    elif cmd == "set" and args[2] == "--protection":
        state["protection"] = int(args[3])
        log(f"protection {args[3]}")
    elif cmd == "set" and args[2] == "--delete":
        if state["protection"] == 1:
            sys.exit(25)  # a protected container refuses disk changes, as PVE does
        key = args[3]
        if key.startswith("unused"):
            vol = state["config"].pop(key)
            shutil.rmtree(Path(state["root"], vol.split(":", 1)[1]), ignore_errors=True)
            log(f"destroy {vol}")
        elif state["detach_pending_while_running"] and state["status"] == "running":
            state["pending_delete"].append(key)
            log(f"detach-pending {key}")
        else:
            detach(key)
    else:
        sys.exit(f"fake pct: unhandled {args}")
    save()


{"pvesh": pvesh, "pvesm": pvesm, "pct": pct}[sys.argv[1]](sys.argv[2:])
