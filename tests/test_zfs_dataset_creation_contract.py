from pathlib import Path

import yaml
from jinja2 import Environment


ROOT = Path(__file__).resolve().parents[1]
TASKS = yaml.safe_load((ROOT / "roles/zfs_pools/tasks/datasets.yml").read_text())
MISSING = "cannot open 'tank/cache': dataset does not exist"
GUARD = "not (ansible_check_mode and zfs_dataset.key in zfs_pools_ds_pending)"


def _task(prefix):
    return next(task for task in TASKS if task["name"].startswith(prefix))


def test_check_mode_quota_read_tolerates_only_a_not_yet_created_dataset():
    failed = Environment().compile_expression(_task("Read current dataset quotas")["failed_when"])

    def result(rc, stderr, check_mode):
        return failed(zfs_pools_ds_quota={"rc": rc, "stderr": stderr}, ansible_check_mode=check_mode)

    assert result(1, MISSING, check_mode=True) is False
    assert result(1, MISSING, check_mode=False) is True
    assert result(1, "permission denied", check_mode=True) is True
    assert result(0, "", check_mode=False) is False


def test_check_mode_skips_per_dataset_steps_for_pending_datasets():
    expression = _task("List datasets still to be created")["ansible.builtin.set_fact"]["zfs_pools_ds_pending"]
    pending = Environment().compile_expression(expression.strip().removeprefix("{{").removesuffix("}}"))
    results = [{"rc": 0, "item": {"key": "present"}}, {"rc": 1, "item": {"key": "cache"}}]
    assert pending(zfs_pools_ds_check={"results": results}) == ["cache"]

    guard = Environment().compile_expression(GUARD)
    for check_mode, key, runs in [(True, "cache", False), (True, "present", True), (False, "cache", True)]:
        assert guard(ansible_check_mode=check_mode, zfs_dataset={"key": key}, zfs_pools_ds_pending=["cache"]) is runs

    for prefix in ("Apply per-dataset properties", "Apply NFS exports", "Register datasets as Proxmox"):
        assert GUARD in _task(prefix)["when"]
