#!/usr/bin/env python3
"""pve_disk_inventory shapes the Proxmox disk list correctly for Nautobot.

The consumer of this artifact DELETES drives it stops seeing, so every failure
mode here is silent and destructive rather than loud: a filter that stops
excluding removable media churns the inventory on every converge, and a
transform that drops the node stamp orphans every drive from its machine.

The expression is EXTRACTED from the role rather than restated here, so this
test cannot pass against a transform the role no longer uses -- restating it
would only assert that I typed it twice.
"""

import json
import sys
from pathlib import Path

import yaml
from ansible.plugins.filter.core import FilterModule as CoreFilters
from ansible.plugins.filter.mathstuff import FilterModule as MathFilters
from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "roles" / "pve_disk_inventory" / "tasks" / "main.yml"
DEFAULTS = ROOT / "roles" / "pve_disk_inventory" / "defaults" / "main.yml"

# One real disk, one removable stick, one BMC virtual device. The last two are
# exactly what a hand-rolled lsblk parser seeds into the estate inventory by
# mistake; `type` tells them apart without heuristics.
FIXTURE = [
    {"devpath": "/dev/sda", "serial": "EXAMPLESERIAL1", "type": "hdd", "used": "ZFS"},
    {"devpath": "/dev/sdz", "serial": "0123456789", "type": "usb", "used": ""},
    {"devpath": "/dev/nvme0n1", "serial": "EXAMPLESERIAL2", "type": "nvme", "used": "ZFS"},
]


def extract_transform() -> str:
    """Pull the node-drives expression out of the role's own task file."""
    tasks = yaml.safe_load(TASKS.read_text())
    for task in _walk(tasks):
        fact = task.get("ansible.builtin.set_fact") or {}
        if "pve_disk_inventory_node_drives" in fact:
            return fact["pve_disk_inventory_node_drives"]
    raise AssertionError(
        f"no task in {TASKS} sets pve_disk_inventory_node_drives -- the role was "
        "restructured and this test is now asserting nothing."
    )


def _walk(tasks):
    """Yield every task, descending into block/rescue/always."""
    for task in tasks or []:
        yield task
        for key in ("block", "rescue", "always"):
            yield from _walk(task.get(key))


def render(expression, **context):
    """Evaluate an Ansible expression with the filters the role actually uses."""
    env = Environment(autoescape=False)  # noqa: S701 - not HTML, and never rendered
    env.filters.update(CoreFilters().filters())
    env.filters.update(MathFilters().filters())
    # The role's value is a bare `{{ ... }}` block; wrap so Jinja returns the
    # native object rather than its string repr.
    return env.compile_expression(expression.strip().removeprefix("{{").removesuffix("}}"))(
        **context
    )


def check_partial_run_guard() -> None:
    """A limited play must be refused before the artifact is rewritten.

    The artifact is written WHOLE, so `--limit one-node` drops every untargeted
    node's drives and the consumer then deletes them downstream. This happened
    for real: a stray --limit run cut a 19-drive artifact to 8, with every task
    reporting ok. The zero-drive guard cannot catch it -- one node's disks is a
    non-empty, plausible result.

    The variable choice is the fragile part. `ansible_play_hosts` is who
    SURVIVED the play; `ansible_play_hosts_all` is who it TARGETED. Using the
    former makes an unreachable host look like a limit, which would block a
    legitimate full run on any estate with a decommissioned node still listed.
    """
    tasks = yaml.safe_load(TASKS.read_text())
    guard = next(
        (t for t in _walk(tasks) if "assert" in str(t.get("name", "")).lower()
         or "refuse" in str(t.get("name", "")).lower()),
        None,
    )
    assert guard is not None, (
        f"no partial-run guard in {TASKS} -- a --limit run would silently "
        "publish a truncated artifact and delete the missing nodes' drives."
    )
    condition = str(guard.get("ansible.builtin.assert", {}).get("that", ""))
    assert "ansible_play_hosts_all" in condition, (
        "the guard does not use ansible_play_hosts_all. ansible_play_hosts is "
        "survivors, not targets, so an unreachable node would read as a limit "
        f"and block a legitimate full run: {condition}"
    )
    assert "run_once" in guard, "the guard must run once, not per host"


def main() -> int:
    expression = extract_transform()
    excluded = yaml.safe_load(DEFAULTS.read_text())["pve_disk_inventory_exclude_types"]

    result = render(
        expression,
        pve_disk_inventory_raw={"stdout": json.dumps(FIXTURE)},
        pve_disk_inventory_exclude_types=excluded,
        ansible_hostname="pve-test",
    )

    kept = {d["devpath"] for d in result}
    assert kept == {"/dev/sda", "/dev/nvme0n1"}, f"wrong disks kept: {sorted(kept)}"

    # The stamp is what ties a drive to its machine. Without it every drive in
    # the aggregated artifact is unattributable, and the consumer cannot pick a
    # parent Device.
    assert all(d["node"] == "pve-test" for d in result), result

    # Fields the consumer keys on must survive the transform untouched.
    sda = next(d for d in result if d["devpath"] == "/dev/sda")
    assert sda["serial"] == "EXAMPLESERIAL1", sda
    assert sda["used"] == "ZFS", sda

    # A negative control: with nothing excluded, the removable stick comes back.
    # Without this, a transform that dropped `rejectattr` entirely and a
    # transform that hard-codes the exclusion would both pass the check above.
    unfiltered = render(
        expression,
        pve_disk_inventory_raw={"stdout": json.dumps(FIXTURE)},
        pve_disk_inventory_exclude_types=[],
        ansible_hostname="pve-test",
    )
    assert len(unfiltered) == 3, (
        "excluding nothing still dropped a disk -- the exclusion is hard-coded "
        f"rather than driven by pve_disk_inventory_exclude_types: {unfiltered}"
    )

    check_partial_run_guard()

    print(
        f"pve_disk_inventory transform + partial-run guard: OK "
        f"({len(result)}/3 kept, excluded={excluded}, node stamp applied)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
