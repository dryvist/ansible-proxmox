"""Contracts for idrac_power chassis state reporting and shutdown timeout."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
TASKS = yaml.safe_load((ROOT / "roles/idrac_power/tasks/main.yml").read_text())
DEFAULTS = yaml.safe_load((ROOT / "roles/idrac_power/defaults/main.yml").read_text())


def _task(name: str) -> dict:
    return next(task for task in TASKS if task.get("name") == name)


def nested_tasks(tasks):
    for task in tasks:
        yield task
        for section in ("block", "rescue", "always"):
            yield from nested_tasks(task.get(section, []))


def process_argument_values(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.rsplit(".", 1)[-1] in {"command", "cmd", "argv", "shell"}:
                yield item
            yield from process_argument_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from process_argument_values(item)


def test_current_status_report_prints_only_query_stdout() -> None:
    query = _task("Query current chassis power status")
    report = _task("Report current chassis power status")

    assert TASKS.index(report) == TASKS.index(query) + 1
    assert report["ansible.builtin.debug"] == {"msg": "{{ idrac_power_status.stdout }}"}
    assert report["when"] == query["when"]
    ipmitool_tasks = [
        task
        for task in TASKS
        if "ipmitool" in task.get("ansible.builtin.command", {}).get("cmd", "")
    ]
    assert ipmitool_tasks
    assert all(task.get("no_log") is True for task in ipmitool_tasks)


def test_ipmitool_password_is_not_a_process_argument() -> None:
    ipmitool_tasks = []
    for task in nested_tasks(TASKS):
        for argument in process_argument_values(task):
            rendered = str(argument)
            assert "idrac_power_password" not in rendered
            if "ipmitool" in rendered:
                ipmitool_tasks.append((task, rendered))

    assert ipmitool_tasks
    for task, command in ipmitool_tasks:
        assert "-E" in command
        assert task.get("environment") == {
            "IPMI_PASSWORD": "{{ idrac_power_password }}"
        }


def test_status_runs_report_read_only_fault_evidence() -> None:
    query = _task("Query chassis faults and recent BMC events")
    report = _task("Report chassis faults and recent BMC events")

    assert query["loop"] == ["chassis status", "sel elist last 40"]
    assert query["changed_when"] is False
    assert query["no_log"] is True
    assert "idrac_power_action == 'status'" in query["when"]
    assert report["when"] == query["when"]
    assert "idrac_power_diagnostics.results" in report["ansible.builtin.debug"]["msg"]


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
