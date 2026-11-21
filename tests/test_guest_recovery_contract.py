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
    assert "mode in ['unit-stop', 'unit-kill', 'guest-restart', 'backup-release']" in request_assert["that"]


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


def _commands_with_conditions(tasks: list[dict], inherited: tuple = ()) -> list[tuple[list | str, tuple]]:
    """Every command argv with the when conditions it runs under, block conditions included."""
    found = []
    for task in tasks:
        when = task.get("when", [])
        conditions = inherited + tuple(when if isinstance(when, list) else [when])
        if "ansible.builtin.command" in task:
            found.append((task["ansible.builtin.command"]["argv"], conditions))
        for section in ("block", "rescue", "always"):
            found.extend(_commands_with_conditions(task.get(section, []), conditions))
    return found


def _tool(argv: list | str) -> str:
    # The memory restore builds its argv in a template expression.
    return argv[0] if isinstance(argv, list) else argv.split("'")[1]


def test_a_qemu_guest_never_takes_a_pct_branch() -> None:
    commands = _commands_with_conditions(_plays()[1]["tasks"])
    pct = [conditions for argv, conditions in commands if _tool(argv) == "pct"]
    qm = [conditions for argv, conditions in commands if _tool(argv) == "qm"]
    assert pct and qm
    assert all("guest_recovery_type == 'lxc'" in conditions for conditions in pct)
    assert all("guest_recovery_type == 'qemu'" in conditions for conditions in qm)


def test_the_vm_path_never_stops_or_destroys_the_vm() -> None:
    qm_actions = {
        argv[1] for argv, _ in _commands_with_conditions(_plays()[1]["tasks"]) if _tool(argv) == "qm"
    }
    assert qm_actions == {"reboot", "reset", "status"}


def test_the_guest_type_is_read_live_even_in_check_mode() -> None:
    read = next(task for task in _plays()[1]["tasks"] if task["name"] == "Read live guest placement from the cluster")
    assert read["ansible.builtin.command"]["argv"][:3] == ["pvesh", "get", "/cluster/resources"]
    assert read["check_mode"] is False
    assert read["changed_when"] is False


def test_backup_release_stops_only_tasks_backing_up_this_guest() -> None:
    release = next(
        task for task in _plays()[1]["tasks"] if task["name"] == "Release a container held by a running backup"
    )
    assert "guest_recovery_type == 'lxc'" in release["when"]
    names = [task["name"] for task in release["block"]]
    stop = next(task for task in release["block"] if task["name"] == "Stop each vzdump task that is backing up this VMID")
    assert stop["loop"] == "{{ guest_recovery_vzdump_upids }}"
    # The log is printed and the tasks are selected before anything is stopped.
    assert names.index("Print each active vzdump task log") < names.index(stop["name"])
    assert names.index("Select the tasks whose current guest is this VMID") < names.index(stop["name"])
