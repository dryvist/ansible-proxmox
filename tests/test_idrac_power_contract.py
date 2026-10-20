"""Contracts for idrac_power chassis state reporting and shutdown timeout."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
TASKS = yaml.safe_load((ROOT / "roles/idrac_power/tasks/main.yml").read_text())
DEFAULTS = yaml.safe_load((ROOT / "roles/idrac_power/defaults/main.yml").read_text())


def _task(name: str) -> dict:
    return next(task for task in TASKS if task.get("name") == name)


def test_current_status_report_prints_only_query_stdout() -> None:
    query = _task("Query current chassis power status")
    report = _task("Report current chassis power status")

    assert TASKS.index(report) == TASKS.index(query) + 1
    assert report["ansible.builtin.debug"] == {"msg": "{{ idrac_power_status.stdout }}"}
    assert report["when"] == query["when"]
    password_commands = [
        task
        for task in TASKS
        if "idrac_power_password"
        in task.get("ansible.builtin.command", {}).get("cmd", "")
    ]
    assert password_commands
    assert all(task.get("no_log") is True for task in password_commands)


def test_off_timeout_reports_final_state_and_fails_by_default() -> None:
    wait = _task("Wait for the graceful power-off to complete")
    report = _task("Report final chassis power status")
    fail = _task("Fail when graceful power-off does not complete")

    assert TASKS.index(wait) < TASKS.index(report) < TASKS.index(fail)
    assert report["ansible.builtin.debug"] == {"msg": "{{ idrac_power_off_check.stdout }}"}
    assert "idrac_power_action == 'off'" in fail["when"]
    assert "idrac_power_off_fail_on_timeout | bool" in fail["when"]
    assert "'is off' not in (idrac_power_off_check.stdout | default(''))" in fail["when"]
    assert "idrac_power_off_fail_on_timeout" in DEFAULTS
    assert DEFAULTS["idrac_power_off_fail_on_timeout"] is True
