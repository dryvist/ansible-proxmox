"""Contract checks for the PBS-only pve_backup_jobs target and its node layout."""

import ast
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "roles/pve_backup_jobs"
DEFAULTS = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
MAIN = yaml.safe_load((ROLE / "tasks/main.yml").read_text())
TASK_TEXT = "\n".join(path.read_text() for path in sorted((ROLE / "tasks").glob("*.yml")))
RECONCILE = (ROLE / "tasks/reconcile.yml").read_text()
INVENTORY = yaml.safe_load((ROOT / "inventory/group_vars/proxmox.yml").read_text())
JOBS = INVENTORY["pve_backup_jobs_jobs"]

# community.proxmox 2.1.0, the pin in requirements.yml: proxmox_storage pbs_options.
PINNED_PBS_OPTIONS = {"server", "datastore", "username", "password", "namespace", "fingerprint", "encryption_key"}
MODULE = Path.home() / ".ansible/collections/ansible_collections/community/proxmox/plugins/modules/proxmox_storage.py"


def walk(tasks):
    for task in tasks:
        yield task
        for section in ("block", "rescue", "always"):
            yield from walk(task.get(section, []))


def module_pbs_options():
    """The pbs_options keys. Read from the installed module when present, else the pin."""
    if not MODULE.exists():
        return PINNED_PBS_OPTIONS
    tree = ast.parse(MODULE.read_text())
    docs = next(
        node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Constant)
        and any(isinstance(target, ast.Name) and target.id == "DOCUMENTATION" for target in node.targets)
    )
    keys = set(yaml.safe_load(docs)["options"]["pbs_options"]["suboptions"])
    assert keys == PINNED_PBS_OPTIONS, "installed proxmox_storage differs from the pin in requirements.yml"
    return keys


def storage_options():
    tasks = [task for task in walk(MAIN) if "community.proxmox.proxmox_storage" in task]
    assert len(tasks) == 1
    return tasks[0]["community.proxmox.proxmox_storage"]


def test_storage_is_pbs_with_only_valid_options():
    storage = storage_options()
    assert storage["type"] == "pbs"
    assert set(storage["pbs_options"]) == {"server", "datastore", "username", "password", "fingerprint"}
    assert set(storage["pbs_options"]) <= module_pbs_options()
    assert "dir_options" not in storage


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
            any(key.startswith(("community.proxmox.", "community.hashi_vault.")) for key in task)
            or "PBS_" in yaml.safe_dump(task)
        )
    ]
    assert credential_tasks
    for task in credential_tasks:
        assert task.get("no_log") is True, task.get("name")


def test_declared_jobs_ship_disabled():
    assert DEFAULTS["pve_backup_jobs_jobs"] == []
    assert "item.enabled | default(false)" in RECONCILE
    assert JOBS
    assert all(job["enabled"] is False for job in JOBS)


def test_retention_is_owned_by_pbs():
    assert DEFAULTS["pve_backup_jobs_default_prune"] == "keep-all=1"
    assert all(job["prune"] == "keep-all=1" for job in JOBS)


def test_each_job_runs_on_one_node_that_is_not_the_backup_node():
    backup = INVENTORY["pve_backup_jobs_pbs_node"]
    nodes = [job["node"] for job in JOBS]
    assert all("," not in node for node in nodes)
    assert backup not in nodes
    assert set(nodes) == {"pve-r540", "pve-r710", "pve-w5900"}
    assert len({job["id"] for job in JOBS}) == len(JOBS)
    assert {job["pool"] for job in JOBS} == {"protected"}


def test_undeclared_vzdump_jobs_are_not_removed():
    assert INVENTORY["pve_backup_jobs_prune_unmanaged"] is False
    assert INVENTORY["pve_backup_jobs_manage"] is False
