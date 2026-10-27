"""Contracts for the Proxmox upgrade schedule, targeting, and quorum waits."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = yaml.safe_load((ROOT / "playbooks/upgrade.yml").read_text())
ROLE = yaml.safe_load((ROOT / "roles/pve_upgrade/tasks/main.yml").read_text())
WAIT = yaml.safe_load((ROOT / "roles/pve_upgrade/tasks/wait_full_quorum.yml").read_text())
DEFAULTS = yaml.safe_load((ROOT / "roles/pve_upgrade/defaults/main.yml").read_text())


def _walk(tasks):
    for task in tasks:
        yield task
        yield from _walk(task.get("block", []))


def _block() -> list[dict]:
    return next(t["block"] for t in ROLE if t.get("name") == "Upgrade the node, always returning it to normal HA scheduling")


def test_targets_resolve_once_with_first_saturday_and_blank_defaults() -> None:
    resolve = PLAYBOOK[0]
    assert resolve["hosts"] == "localhost"
    expression = resolve["tasks"][0]["ansible.builtin.set_fact"]["upgrade_hosts"]
    assert "now(utc=true, fmt='%w') == '6'" in expression
    assert "| int > 7" in expression
    assert "upgrade_nodes | default('proxmox', true)" in expression
    group = resolve["tasks"][2]["ansible.builtin.add_host"]
    assert group["groups"] == "upgrade_targets"
    assert PLAYBOOK[-1]["hosts"] == "upgrade_targets"
    snapshot = next(p for p in PLAYBOOK if p.get("import_playbook") == "snapshot.yml")
    assert snapshot["vars"]["pve_snapshot_hosts"] == "upgrade_targets"


def test_voters_power_on_and_each_node_needs_full_votes_and_headroom() -> None:
    power = PLAYBOOK[1]
    voter_block = next(t for t in power["tasks"] if t.get("name") == "Power on and rejoin listed voters")
    assert voter_block["when"] == [
        "not ansible_check_mode",
        "groups['upgrade_targets'] | default([]) | length > 0",
        "(proxmox_node_name | default(inventory_hostname)) in pve_quorum_guard_powered_off_voters",
    ]
    assert all("when" not in t for t in voter_block["block"])
    roles = [t.get("ansible.builtin.include_role", {}) for t in _walk(power["tasks"])]
    assert {"name": "idrac_power"} in roles
    assert {"name": "pve_upgrade", "tasks_from": "wait_full_quorum"} in roles

    upgrade = PLAYBOOK[-1]
    assert upgrade["serial"] == 1
    assert upgrade["vars"]["pve_quorum_guard_min_headroom"] == 1
    assert upgrade["vars"]["pve_quorum_guard_powered_off_voters"] == []
    pre = upgrade["pre_tasks"]
    assert pre[0]["ansible.builtin.include_role"] == {"name": "pve_upgrade", "tasks_from": "wait_full_quorum"}
    assert pre[1]["ansible.builtin.import_role"] == {"name": "pve_quorum_guard"}


def test_reboot_is_followed_by_vote_and_ha_waits() -> None:
    names = [t["name"] for t in _walk(_block())]
    reboot = names.index("Reboot when the running kernel differs from the selected installed kernel")
    assert names.index("Wait for every expected vote after the reboot") > reboot
    assert names.index("Wait for HA resources to clear error and fence states") > reboot
    wait_block = next(t for t in _block() if t.get("name") == "Wait for quorum and HA resources after reboot")
    assert wait_block["when"] == "pve_upgrade_reboot_result.rebooted | default(false)"
    assert all("when" not in t for t in wait_block["block"])
    wait = WAIT[0]
    assert wait["ansible.builtin.command"]["cmd"] == "pvecm status"
    assert any("Total votes" in c for c in wait["until"])


def test_major_version_is_asserted_without_a_pin() -> None:
    names = [t["name"] for t in _block()]
    assert names.index("Query Proxmox VE version before the package upgrade") < names.index("Update apt cache")
    assert "Assert the Proxmox VE major version is unchanged" in names


def test_active_vzdump_tasks_clear_before_the_node_upgrade() -> None:
    wait = next(
        t for t in ROLE if t.get("name") == "Wait for active vzdump tasks before upgrading this node"
    )
    upgrade = next(
        t for t in ROLE if t.get("name") == "Upgrade the node, always returning it to normal HA scheduling"
    )
    assert ROLE.index(wait) < ROLE.index(upgrade)

    query = wait["block"][0]
    argv = query["ansible.builtin.command"]["argv"]
    assert argv == [
        "pvesh",
        "get",
        "/nodes/{{ pve_upgrade_node_name }}/tasks",
        "--source",
        "active",
        "--typefilter",
        "vzdump",
        "--output-format",
        "json",
    ]
    assert query["changed_when"] is False
    assert query["check_mode"] is False
    assert "length == 0" in query["until"]
    assert "pve_upgrade_vzdump_wait_timeout_seconds" in query["retries"]
    assert wait["rescue"][0]["ansible.builtin.fail"]
    assert DEFAULTS["pve_upgrade_vzdump_wait_timeout_seconds"] == 10800
    assert DEFAULTS["pve_upgrade_vzdump_poll_interval_seconds"] == 60
