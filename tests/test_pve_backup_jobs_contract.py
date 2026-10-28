"""Contract checks for the PBS-only pve_backup_jobs target and its node layout."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "roles/pve_backup_jobs"
DEFAULTS = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
MAIN = yaml.safe_load((ROLE / "tasks/main.yml").read_text())
TASK_TEXT = "\n".join(path.read_text() for path in sorted((ROLE / "tasks").glob("*.yml")))
RECONCILE = (ROLE / "tasks/reconcile.yml").read_text()
INVENTORY = yaml.safe_load((ROOT / "inventory/group_vars/proxmox/01-storage.yml").read_text())
JOBS = INVENTORY["pve_backup_jobs_jobs"]

def walk(tasks):
    for task in tasks:
        yield task
        for section in ("block", "rescue", "always"):
            yield from walk(task.get(section, []))


def task_named(name):
    return next(task for task in walk(MAIN) if task.get("name") == name)


def test_storage_needs_no_api_token_or_proxmoxer():
    tasks = list(walk(MAIN))
    assert not any("community.proxmox.proxmox_storage" in task for task in tasks)
    assert not any("ansible.builtin.uri" in task for task in tasks)
    assert not any(key.startswith("pve_backup_jobs_api_") for key in DEFAULTS)


def test_storage_argv_never_carries_the_secret():
    define = task_named("Define or update the PBS backup target storage")
    argv = define["ansible.builtin.command"]["argv"]
    assert "PBS_TOKEN_SECRET" not in argv
    assert "--password" not in argv
    # server and datastore are fixed after creation, so only create sets them.
    create, update = argv.split("| ternary(")[1].split("],", 1)
    assert "'--server'" in create and "'--datastore'" in create
    assert "--server" not in update and "--datastore" not in update


def test_storage_is_created_disabled_and_enabled_after_the_password():
    tasks = list(walk(MAIN))
    define = task_named("Define or update the PBS backup target storage")
    write = task_named("Write the PBS token secret to the storage password file")
    enable = task_named("Enable the PBS storage once its password file is in place")
    create = define["ansible.builtin.command"]["argv"].split("| ternary(")[1].split("],", 1)[0]
    assert "'--disable', '1'" in create
    assert enable["ansible.builtin.command"]["argv"][-2:] == ["--delete", "disable"]
    assert tasks.index(define) < tasks.index(write) < tasks.index(enable)


def test_password_directory_exists_before_the_write():
    tasks = list(walk(MAIN))
    directory = task_named("Create the PVE storage secrets directory")
    write = task_named("Write the PBS token secret to the storage password file")
    assert directory["ansible.builtin.file"] == {"path": "/etc/pve/priv/storage", "state": "directory", "mode": "0700"}
    assert tasks.index(directory) < tasks.index(write)


def test_secret_goes_to_the_pve_password_file():
    read = task_named("Read the current PBS storage password file")
    write = task_named("Write the PBS token secret to the storage password file")
    path = "/etc/pve/priv/storage/{{ pve_backup_jobs_storage_id }}.pw"
    assert read["ansible.builtin.slurp"]["src"] == path
    command = write["ansible.builtin.command"]
    assert command["argv"] == ["dd", "of=" + path, "status=none"]
    assert command["stdin"] == "{{ pve_backup_jobs_pbs_secret.secret.PBS_TOKEN_SECRET }}"
    assert "PBS_TOKEN_SECRET" in write["when"]
    assert read["no_log"] is True and write["no_log"] is True


def test_no_directory_storage_branch_remains():
    for forbidden in ("dir_options", "is_mountpoint", "prune_backups", "pve_backup_jobs_storage.", "type: dir"):
        assert forbidden not in TASK_TEXT, forbidden
    assert "pve_backup_jobs_storage" not in DEFAULTS


def test_credentials_are_read_from_openbao_on_the_config_host():
    read = next(task for task in walk(MAIN) if "community.hashi_vault.vault_kv2_get" in task)
    assert read["delegate_to"] == "localhost"
    assert read["community.hashi_vault.vault_kv2_get"]["path"] == "{{ pve_backup_jobs_pbs_secret_path }}"
    assert DEFAULTS["pve_backup_jobs_pbs_secret_path"] == "platform/pbs/pve-nodes"
    assert DEFAULTS["pve_backup_jobs_bao_kv_mount"] == "secret"


def test_credential_tasks_are_censored():
    # Leaf tasks only: a block's dump contains its children, so it would match
    # on their credentials and be judged for them.
    credential_tasks = [
        task
        for task in walk(MAIN)
        if "block" not in task
        # An assert only tests field lengths; no_log would hide its fail_msg.
        and "ansible.builtin.assert" not in task
        and (
            any(key.startswith("community.hashi_vault.") for key in task)
            or "PBS_" in yaml.safe_dump(task)
        )
    ]
    assert credential_tasks
    for task in credential_tasks:
        assert task.get("no_log") is True, task.get("name")


def test_declared_jobs_state_enabled_explicitly():
    assert DEFAULTS["pve_backup_jobs_jobs"] == []
    assert "item.enabled | default(false)" in RECONCILE
    assert JOBS
    assert all(isinstance(job["enabled"], bool) for job in JOBS)


def test_exclusions_are_desired_state_names():
    for job in (job for job in JOBS if job.get("exclude_names")):
        assert all(isinstance(name, str) and not name.isdigit() for name in job["exclude_names"])
        assert job.get("mode", DEFAULTS["pve_backup_jobs_default_mode"]) == "snapshot"
        assert "vmid" not in job


def test_retention_is_owned_by_pbs():
    assert DEFAULTS["pve_backup_jobs_default_prune"] == "keep-all=1"
    assert all(job.get("prune", "keep-all=1") == "keep-all=1" for job in JOBS)


def test_each_job_selects_all_guests_on_one_non_backup_node():
    backup = INVENTORY["pve_backup_jobs_pbs_node"]
    nodes = [job["node"] for job in JOBS]
    assert all("," not in node for node in nodes)
    assert backup not in nodes
    assert set(nodes) == {"pve-r540", "pve-r710", "pve-w5900"}
    assert len({job["id"] for job in JOBS}) == len(JOBS)
    assert all(job["all"] is True for job in JOBS)
    assert all("pool" not in job for job in JOBS)
    assert not any(job.get("pool") == "protected" for job in JOBS)
    assert {job["id"]: job["schedule"] for job in JOBS} == {
        "guests-pve-r540": "06:30",
        "guests-pve-r710": "06:15",
        "guests-pve-w5900": "06:00",
    }


def test_undeclared_vzdump_jobs_are_not_removed():
    assert INVENTORY["pve_backup_jobs_prune_unmanaged"] is False
    assert INVENTORY["pve_backup_jobs_manage"] is True
