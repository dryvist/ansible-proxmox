"""The sanoid role must read the pvesr guest list before it evaluates syncoid_jobs.

syncoid_jobs on pve-r710 is built from syncoid_rootpool_jobs_json, which
requires syncoid_pvesr_guest_ids. That fact comes from the cluster replication
read (`pvesh get /cluster/replication`) which used to run only at the top of
the syncoid role — imported by playbooks/backup-dr.yml, which site.yml loads
AFTER the sanoid role has already evaluated syncoid_jobs. The sanoid role
therefore loads that read itself, as its first task, from the shared
pvesr_guests.yml file.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SANOID_TASKS = ROOT / "roles/sanoid/tasks/main.yml"
SYNCOID_TASKS = ROOT / "roles/syncoid/tasks/main.yml"
PVESR_GUESTS = ROOT / "roles/syncoid/tasks/pvesr_guests.yml"


def test_task_files_exist():
    assert SANOID_TASKS.is_file()
    assert SYNCOID_TASKS.is_file()


def test_first_task_includes_pvesr_guest_read():
    first = yaml.safe_load(SANOID_TASKS.read_text())[0]
    include_role = first.get("ansible.builtin.include_role")
    assert include_role is not None, "first sanoid task must be an include_role"
    assert include_role["name"] == "syncoid"
    assert include_role["tasks_from"] == "pvesr_guests.yml"
    assert "sanoid" in first.get("tags", [])
    assert "sanoid" in include_role.get("apply", {}).get("tags", [])


def test_pvesr_guests_file_sets_syncoid_pvesr_guest_ids():
    assert PVESR_GUESTS.is_file()
    tasks = yaml.safe_load(PVESR_GUESTS.read_text())
    set_facts = [
        task for task in tasks
        if "syncoid_pvesr_guest_ids" in task.get("ansible.builtin.set_fact", {})
    ]
    assert set_facts, "pvesr_guests.yml must set syncoid_pvesr_guest_ids"


def test_syncoid_main_imports_pvesr_guests_before_any_syncoid_jobs_use():
    tasks = yaml.safe_load(SYNCOID_TASKS.read_text())
    import_indexes = [
        i for i, task in enumerate(tasks)
        if task.get("ansible.builtin.import_tasks") == "pvesr_guests.yml"
    ]
    assert import_indexes, "syncoid/tasks/main.yml must import pvesr_guests.yml"
    for i, task in enumerate(tasks[: min(import_indexes)], start=1):
        assert "syncoid_jobs" not in str(task), (
            f"task {i} ({task.get('name')}) references syncoid_jobs before "
            "pvesr_guests.yml is imported"
        )
