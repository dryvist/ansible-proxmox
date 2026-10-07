#!/usr/bin/env python3
"""Run the actual read-only budget tasks against sanitized PVE API output.

Run: python3 tests/guest_placement/test_memory_budget.py
The fixtures retain observed allocations and physical RAM; node labels are
synthetic. No measured-use admission shortcut.
"""

import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[2]
RESOURCES = [
    row
    for path in sorted(Path(__file__).parent.glob("resources-*.json"))
    for row in json.loads(path.read_text())
]
TASKS = ROOT / "playbooks/tasks/verify_guest_memory.yml"
MIB = 1048576


def run_case(name, node, budget, resources, passes, evidence):
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        variables = {
            "placement_resources": resources,
            "placement_node": node,
            "placement_node_config": budget,
        }
        play = [{
            "name": name,
            "hosts": "localhost",
            "gather_facts": False,
            "become": False,
            "vars": variables,
            "tasks": [{
                "name": "Exercise the production memory guard",
                "ansible.builtin.include_tasks": str(TASKS),
            }],
        }]
        path = work / "test.yml"
        path.write_text(yaml.safe_dump(play))
        result = subprocess.run(
            ["ansible-playbook", "-i", "localhost,", "-c", "local", str(path)],
            env=dict(os.environ, ANSIBLE_LOCAL_TEMP=str(work / "ansible")),
            capture_output=True, text=True, cwd=ROOT,
        )
        output = result.stdout + result.stderr
        assert (result.returncode == 0) == passes, f"{name}:\n{output}"
        assert evidence in output, f"{name}: missing evidence {evidence!r}\n{output}"
        print(f"PASS: {name}")


def main():
    cases = []
    # Real-node observed commitments: 184.5, 130, 128.5 and 48 GiB.
    for node, budget, passes in [
        ("server-a", 178 * 1024, False),
        ("server-b", 228 * 1024, True),
        ("gpu-a", 27 * 1024, False),
        ("gpu-b", 86 * 1024, True),
    ]:
        cases.append((node, node, {"memory_budget_mb": budget}, RESOURCES,
                      passes, "Allocated guest memory"))

    cases.append(("missing budget", "server-b", {}, RESOURCES,
                  False, "A node memory budget"))
    for budget in (None, "233472", 0, -1, 233472.5, True):
        cases.append((f"malformed budget {budget!r}", "server-b",
                      {"memory_budget_mb": budget}, RESOURCES,
                      False, "A node memory budget"))
    cases.append(("budget exceeds physical memory", "gpu-b",
                  {"memory_budget_mb": 100 * 1024}, RESOURCES,
                  False, "Allocated guest memory"))
    cases.append(("missing resource list", "gpu-b",
                  {"memory_budget_mb": 86 * 1024}, None,
                  False, "A node memory budget"))
    without_node = [row for row in RESOURCES if not (
        row["type"] == "node" and row["node"] == "gpu-b")]
    cases.append(("missing physical telemetry", "gpu-b",
                  {"memory_budget_mb": 86 * 1024}, without_node,
                  False, "Physical memory telemetry"))
    for field in ("maxmem", "template"):
        rows = copy.deepcopy(RESOURCES)
        guest = next(row for row in rows if row["type"] == "lxc"
                     and row["node"] == "server-b")
        guest.pop(field)
        cases.append((f"missing guest {field}", "server-b",
                      {"memory_budget_mb": 228 * 1024}, rows,
                      False, "A guest allocation"))

    # No declared-guest filter exists: all API guests count. A stopped VM can
    # make an otherwise fitting node fail even when usage is zero.
    rows = copy.deepcopy(RESOURCES)
    rows.append({"node": "gpu-b", "type": "qemu", "template": 0,
                 "vmid": 20000, "status": "stopped", "mem": 0,
                 "maxmem": 40 * 1024 * MIB})
    cases.append(("unmanaged stopped VM counts", "gpu-b",
                  {"memory_budget_mb": 86 * 1024}, rows,
                  False, "Allocated guest memory"))
    rows = copy.deepcopy(rows)
    rows[-1]["template"] = 1
    cases.append(("templates do not reserve guest memory", "gpu-b",
                  {"memory_budget_mb": 86 * 1024}, rows,
                  True, "Allocated guest memory"))
    allocated = sum(row["maxmem"] for row in RESOURCES
                    if row["node"] == "gpu-b" and row["type"] in ("qemu", "lxc")
                    and row["template"] == 0)
    cases.append(("exact budget boundary", "gpu-b",
                  {"memory_budget_mb": allocated // MIB}, RESOURCES,
                  True, "Allocated guest memory"))
    cases.append(("one MiB over budget", "gpu-b",
                  {"memory_budget_mb": allocated // MIB - 1}, RESOURCES,
                  False, "Allocated guest memory"))

    for case in cases:
        run_case(*case)
    print(f"PASS: {len(cases)} actual Ansible memory-budget cases")


if __name__ == "__main__":
    main()
