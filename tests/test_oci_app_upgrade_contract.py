"""Contract checks for the oci_app_upgrade role and playbook.

Reads the role's own YAML and asserts the order of destructive steps, the
guards around them, and the rescue behaviour. Nothing runs against a node.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "roles" / "oci_app_upgrade"
TASKS = ROLE / "tasks"
PLAYBOOK = ROOT / "playbooks" / "oci_app_upgrade.yml"


def _tasks(name: str) -> list:
    return yaml.safe_load((TASKS / name).read_text())


def _role_text() -> str:
    return "\n".join(p.read_text() for p in sorted(ROLE.rglob("*")) if p.is_file())


def _subsequence_in_order(tasks: list, tokens: list) -> None:
    """Assert each token appears in some task, in the given order, greedily."""
    position = 0
    for token in tokens:
        found = None
        for index in range(position, len(tasks)):
            if token in repr(tasks[index]):
                found = index
                break
        assert found is not None, f"no task after position {position} mentions {token!r}"
        position = found + 1


def test_dry_run_is_the_default() -> None:
    defaults = yaml.safe_load((ROLE / "defaults" / "main.yml").read_text())
    assert defaults["oci_app_upgrade_dry_run"] is True


def test_apply_is_gated_on_explicit_opt_out_and_not_check_mode() -> None:
    upgrade_one = _tasks("upgrade_one.yml")
    apply_task = next(t for t in upgrade_one if t.get("name", "").startswith("Replace the image"))
    when = apply_task["when"]
    assert "not (oci_app_upgrade_dry_run | bool)" in when
    assert "not ansible_check_mode" in when


def test_destructive_steps_run_in_the_procedure_order() -> None:
    swap = _tasks("swap_template.yml")
    _subsequence_in_order(
        swap,
        [
            "ha-manager",
            "pvesr",
            "pct shutdown",
            "'move-volume'",
            "--purge",
            "build_create_argv.yml",
            "oci_app_upgrade_create_argv",
            "'move-volume'",
            "pct destroy {{ oci_app_upgrade_holder_vmid | string }}",
            "pct start",
            "restore_ha.yml",
        ],
    )


def test_the_ha_entry_is_restored_only_after_the_start() -> None:
    swap = _tasks("swap_template.yml")
    start = next(i for i, t in enumerate(swap) if "pct start" in repr(t))
    restore = next(i for i, t in enumerate(swap) if "restore_ha.yml" in repr(t))
    assert start < restore


def test_every_ct_destroy_purges_and_follows_the_volume_move() -> None:
    text = (TASKS / "swap_template.yml").read_text()
    ct_destroys = re.findall(r"pct destroy \{\{ oci_app_upgrade_vmid \}\}[^\n]*", text)
    assert ct_destroys, "the swap destroys the CT"
    assert all("--purge" in line for line in ct_destroys)


def test_holder_is_destroyed_only_after_an_empty_check() -> None:
    swap = _tasks("swap_template.yml")
    guard = next(
        i for i, t in enumerate(swap)
        if "Require the holder to own no mpN or unusedN volume" in t.get("name", "")
    )
    destroy = next(i for i, t in enumerate(swap) if "pct destroy {{ oci_app_upgrade_holder_vmid" in repr(t))
    assert guard < destroy
    assert "oci_app_upgrade_holder_mp_keys | length == 0" in repr(swap[guard])
    assert "oci_app_upgrade_holder_unused_keys | length == 0" in repr(swap[guard])


def test_no_volume_is_detached_to_unused_or_restored_from_archive() -> None:
    text = _role_text()
    assert not re.search(r"pct set[^\n]*--delete", text), "a volume must never be detached with pct set --delete"
    assert "pct restore" not in text, "the rescue must not restore from the archive"


def test_the_archive_is_taken_only_in_apply() -> None:
    vzdump_command = re.compile(r"(?:command:\s*vzdump|^\s*-\s*vzdump\s*$)", re.MULTILINE)
    assert vzdump_command.search((TASKS / "apply.yml").read_text())
    for name in ("swap_template.yml", "recover.yml", "notify.yml", "read_state.yml", "preflight.yml"):
        assert not vzdump_command.search((TASKS / name).read_text()), name


def test_rescue_posts_the_notice_before_recovering() -> None:
    apply_tasks = _tasks("apply.yml")
    block = next(t for t in apply_tasks if "block" in t)
    rescue = block["rescue"]
    tasks = [inner for t in rescue for inner in (t.get("block") or [t])]
    includes = [t["ansible.builtin.include_tasks"] for t in tasks if "ansible.builtin.include_tasks" in t]
    assert includes.index("notify.yml") < includes.index("recover.yml")


def test_rescue_rebuilds_from_the_previous_template() -> None:
    recover = (TASKS / "recover.yml").read_text()
    assert "oci_app_upgrade_item.current_template" in recover


def test_notice_goes_to_the_keystone_topic() -> None:
    defaults = yaml.safe_load((ROLE / "defaults" / "main.yml").read_text())
    assert defaults["oci_app_upgrade_ntfy_url"].endswith("/keystone")


def test_health_window_is_ten_minutes() -> None:
    defaults = yaml.safe_load((ROLE / "defaults" / "main.yml").read_text())
    assert defaults["oci_app_upgrade_health_retries"] * defaults["oci_app_upgrade_health_delay"] == 600


def test_playbook_is_serial_and_stops_on_the_first_failure() -> None:
    plays = yaml.safe_load(PLAYBOOK.read_text())
    upgrade = next(p for p in plays if p.get("hosts") == "proxmox")
    assert upgrade["serial"] == 1
    assert upgrade["max_fail_percentage"] == 0
    assert upgrade["roles"][0]["role"] == "oci_app_upgrade"


def test_playbook_loads_the_inventory_first() -> None:
    plays = yaml.safe_load(PLAYBOOK.read_text())
    assert plays[0]["ansible.builtin.import_playbook"] == "load_tofu.yml"


def test_restore_uses_the_existing_pve_ha_tasks() -> None:
    restore = (TASKS / "restore_ha.yml").read_text()
    for task_file in ("tier0_resources", "replication_jobs", "replication_apply"):
        assert f"tasks_from: {task_file}" in restore


def test_no_literal_addresses_in_committed_text() -> None:
    address = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
    assert not address.search(_role_text())
    assert not address.search(PLAYBOOK.read_text())


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("oci_app_upgrade contract: OK")
