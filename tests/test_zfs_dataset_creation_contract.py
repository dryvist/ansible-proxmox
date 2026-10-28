from pathlib import Path

import pytest
import yaml
from jinja2 import Environment


ROOT = Path(__file__).resolve().parents[1]
MISSING = "cannot open 'tank/cache': dataset does not exist"


def _read_task(path, prefix):
    tasks = yaml.safe_load((ROOT / path).read_text())
    return next(task for task in tasks if task["name"].startswith(prefix))


@pytest.mark.parametrize(
    ("path", "prefix", "var"),
    [
        ("roles/zfs_pools/tasks/datasets.yml", "Read current dataset quotas", "zfs_pools_ds_quota"),
        ("roles/zfs_pools/tasks/dataset_properties.yml", "Read current properties", "zfs_pools_ds_prop"),
    ],
)
def test_check_mode_tolerates_only_a_not_yet_created_dataset(path, prefix, var):
    failed = Environment().compile_expression(_read_task(path, prefix)["failed_when"])

    def result(rc, stderr, check_mode):
        return failed(**{var: {"rc": rc, "stderr": stderr}, "ansible_check_mode": check_mode})

    assert result(1, MISSING, check_mode=True) is False
    assert result(1, MISSING, check_mode=False) is True
    assert result(1, "permission denied", check_mode=True) is True
    assert result(0, "", check_mode=False) is False
