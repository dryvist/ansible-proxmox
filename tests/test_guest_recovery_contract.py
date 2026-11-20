"""Contract checks for the guest recovery playbook."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "playbooks" / "guest-recovery.yml"


def _tasks(play: dict) -> list[dict]:
    result = []
    for task in play.get("tasks", []):
        result.append(task)
        for section in ("block", "rescue", "always"):
            result.extend(_tasks({"tasks": task.get(section, [])}))
    return result


def _plays() -> list[dict]:
    return [play for play in yaml.safe_load(PLAYBOOK.read_text()) if "hosts" in play]


def test_loads_tofu_before_its_proxmox_hosts() -> None:
    # ansible_user on the proxmox hosts resolves from proxmox_user_from_tofu, which only load_tofu.yml sets.
    entries = yaml.safe_load(PLAYBOOK.read_text())
    assert entries[0].get("ansible.builtin.import_playbook") == "load_tofu.yml"
    assert [entry.get("ansible.builtin.import_playbook") for entry in entries].count("load_tofu.yml") == 1


def test_targets_are_limited_to_inventory_group() -> None:
    plays = _plays()
    assert [play["hosts"] for play in plays] == ["localhost", "proxmox"]

    request_assert = plays[0]["tasks"][0]["ansible.builtin.assert"]
    assert "node | string in (groups['proxmox'] | default([]))" in request_assert["that"]
    assert "mode in ['unit-stop', 'unit-kill', 'guest-restart']" in request_assert["that"]


def test_mutating_commands_use_fixed_argv() -> None:
    plays = yaml.safe_load(PLAYBOOK.read_text())
    commands = [
        task["ansible.builtin.command"]
        for play in plays
        for task in _tasks(play)
        if "ansible.builtin.command" in task
    ]

    assert commands
    assert all("argv" in command for command in commands)


def test_unit_kill_restores_memory_in_always_block() -> None:
    plays = _plays()
    kill = next(
        task
        for task in plays[1]["tasks"]
        if task["name"] == "Kill the service cgroup and restore temporary memory headroom"
    )
    restore = kill["always"][0]

    assert restore["name"] == "Restore the original guest memory setting"
    assert "ansible.builtin.command" in restore
    assert "guest_recovery_headroom_mb" in restore["when"][0]
