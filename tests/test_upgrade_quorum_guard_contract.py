"""Contracts for the Proxmox upgrade schedule, targeting, and quorum waits."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _task(tasks: list[dict], name: str) -> dict:
    return next(task for task in tasks if task["name"] == name)


def test_upgrade_targets_and_uses_the_utc_first_saturday_guard() -> None:
    playbook = yaml.safe_load((ROOT / "playbooks/upgrade.yml").read_text())
    snapshot = yaml.safe_load((ROOT / "playbooks/snapshot.yml").read_text())[0]
    upgrade = playbook[-1]

    assert playbook[0]["hosts"] == "localhost"
    tasks = playbook[0]["tasks"]
    date = _task(tasks, "Read the UTC weekday and day of month")
    assert date["ansible.builtin.command"]["argv"] == ["date", "-u", "+%u %d"]
    skip = _task(tasks, "Mark upgrades outside the first-Saturday window")
    expression = skip["ansible.builtin.set_fact"]["upgrade_schedule_skip"]
    assert "| int == 6" in expression
    assert "| int > 7" in expression
    assert "{{ upgrade_nodes | default('proxmox') }}" == upgrade["hosts"]
    assert "{{ upgrade_nodes | default('proxmox') }}" == snapshot["hosts"]
    assert any(task.get("ansible.builtin.meta") == "end_host" for task in upgrade["pre_tasks"])
    assert any(task.get("ansible.builtin.meta") == "end_host" for task in snapshot["pre_tasks"])


def test_upgrade_checks_full_quorum_before_snapshots_and_before_each_reboot() -> None:
    playbook = yaml.safe_load((ROOT / "playbooks/upgrade.yml").read_text())
    snapshot_index = next(i for i, play in enumerate(playbook) if "import_playbook" in play)
    preflight = playbook[snapshot_index - 1]
    upgrade = playbook[-1]

    assert preflight["vars"]["pve_quorum_guard_min_headroom"] == 1
    assert preflight["roles"][0]["role"] == "pve_quorum_guard"
    assert any(
        task["name"] == "Require all configured voters before snapshots"
        for task in preflight["pre_tasks"]
    )
    start_guard = _task(upgrade["pre_tasks"], "Recheck quorum headroom before starting this node")
    assert start_guard["ansible.builtin.import_role"]["name"] == "pve_quorum_guard"

    role_tasks = yaml.safe_load((ROOT / "roles/pve_upgrade/tasks/main.yml").read_text())
    block = _task(role_tasks, "Upgrade the node, always returning it to normal HA scheduling")["block"]
    names = [task["name"] for task in block]
    guard_index = names.index("Recheck quorum headroom before this node reboots")
    reboot_index = names.index("Reboot when the running kernel differs from the selected installed kernel")
    assert guard_index < reboot_index
    assert block[guard_index]["ansible.builtin.include_role"]["name"] == "pve_quorum_guard"
    assert names.index("Require every configured vote before reboot") < reboot_index

    cluster_wait = _task(block, "Wait for quorum and every expected vote after reboot")
    assert cluster_wait["ansible.builtin.command"]["cmd"] == "pvecm status"
    assert cluster_wait["changed_when"] is False
    ha_wait = _task(block, "Wait for HA resources to clear error and fence states")
    assert ha_wait["ansible.builtin.command"]["cmd"] == (
        "pvesh get /cluster/ha/resources --output-format json"
    )
    assert ha_wait["changed_when"] is False
