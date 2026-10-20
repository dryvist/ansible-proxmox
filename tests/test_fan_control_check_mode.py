"""Keep fan-control reads available and repository installs check-mode safe."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS = yaml.safe_load((ROOT / "roles/fan_control/tasks/main.yml").read_text())
TOKEN_TASKS = yaml.safe_load((ROOT / "roles/fan_control/tasks/read_openbao_token.yml").read_text())


def task(name: str) -> dict:
    if name in {item.get("name") for item in TOKEN_TASKS}:
        return next(item for item in TOKEN_TASKS if item.get("name") == name)
    return next(item for item in TASKS[0]["block"] if item.get("name") == name)


def test_read_only_lookups_run_in_check_mode_without_reporting_changes() -> None:
    read_names = (
        "Read the CoolerControl write token from OpenBao",
        "Wait for the local CoolerControl API",
        "Read configured functions",
        "Read configured profiles",
        "Read existing modes",
        "Read every host PWM and fan RPM before max mode",
        "Read every host PWM and fan RPM after max mode",
    )

    for name in read_names:
        read = task(name)
        assert read["check_mode"] is False, name
        assert read["changed_when"] is False, name

    token_read = task("Read the CoolerControl write token from OpenBao")
    assert "community.hashi_vault.vault_kv2_get" in token_read
    assert token_read["no_log"] is True


def test_package_install_waits_for_new_repository_outside_check_mode() -> None:
    repository = task("Configure the official CoolerControl stable repository")
    install = task("Install CoolerControl and the it87 DKMS module")
    daemon = task("Enable and start CoolerControl daemon")

    assert repository["register"] == "_fan_control_repository"
    assert install["when"] == [
        "not ansible_check_mode or not (_fan_control_repository.changed | default(false))"
    ]
    assert install["register"] == "_fan_control_install"
    daemon_guard = " ".join(daemon["when"])
    assert daemon_guard.startswith("not ansible_check_mode or (")
    assert "_fan_control_install is not skipped" in daemon_guard
    assert "_fan_control_install is not changed" in daemon_guard


def test_pending_install_ends_daemon_work_after_the_openbao_gate() -> None:
    block = TASKS[0]["block"]
    token_read = task("Read and require the CoolerControl write token")
    stop_daemon_work = task(
        "Skip pending daemon configuration in check mode"
    )

    assert stop_daemon_work["ansible.builtin.meta"] == "end_role"
    assert stop_daemon_work["when"][0] == "ansible_check_mode"
    stop_guard = " ".join(stop_daemon_work["when"][1:])
    assert "_fan_control_install is skipped" in stop_guard
    assert "_fan_control_install is changed" in stop_guard
    assert block.index(stop_daemon_work) == block.index(token_read) + 1
    assert block.index(stop_daemon_work) < block.index(task("Wait for the local CoolerControl API"))
