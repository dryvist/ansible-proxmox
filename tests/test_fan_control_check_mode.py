"""Keep fan-control reads available and repository installs check-mode safe."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS = yaml.safe_load((ROOT / "roles/fan_control/tasks/main.yml").read_text())


def task(name: str) -> dict:
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

    assert repository["register"] == "_fan_control_repository"
    assert install["when"] == [
        "not ansible_check_mode or not (_fan_control_repository.changed | default(false))"
    ]
