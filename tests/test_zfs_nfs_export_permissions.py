from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DATASET_TASKS = yaml.safe_load((ROOT / "roles/zfs_pools/tasks/datasets.yml").read_text())
EXPORT_TASKS = yaml.safe_load((ROOT / "roles/zfs_pools/tasks/nfs_export.yml").read_text())


def test_export_permissions_require_a_declared_nfs_export():
    guard = next(
        task
        for task in DATASET_TASKS
        if task["name"].startswith("Require an NFS export when dataset export permissions")
    )

    assert guard["when"] == "item.value.nfs_export_permissions is defined"
    assert guard["ansible.builtin.assert"]["that"] == [
        "item.value.nfs_export is defined",
        "item.value.nfs_export | string | length > 0",
    ]


def test_root_squashed_directory_permissions_follow_the_export_restriction():
    set_export = next(
        index
        for index, task in enumerate(EXPORT_TASKS)
        if task["name"].startswith("Set sharenfs for")
    )
    validate = next(
        index
        for index, task in enumerate(EXPORT_TASKS)
        if task["name"].startswith("Validate NFS export permissions")
    )
    set_permissions = next(
        index
        for index, task in enumerate(EXPORT_TASKS)
        if task["name"].startswith("Set the dataset root directory permissions")
    )

    assert set_export < validate < set_permissions
    assert EXPORT_TASKS[validate]["when"] == "zfs_dataset.value.nfs_export_permissions is defined"
    assert all(
        task["check_mode"] is False
        for task in EXPORT_TASKS
        if task["name"].startswith(("Read the dataset mountpoint", "Read the dataset mounted state"))
    )
    assert EXPORT_TASKS[validate]["ansible.builtin.assert"]["that"] == [
        "zfs_dataset.value.nfs_export_permissions is mapping",
        "zfs_dataset.value.nfs_export_permissions.owner is defined",
        "zfs_dataset.value.nfs_export_permissions.owner | string | length > 0",
        "zfs_dataset.value.nfs_export_permissions.group is defined",
        "zfs_dataset.value.nfs_export_permissions.group | string | length > 0",
        "zfs_dataset.value.nfs_export_permissions.mode is defined",
        "zfs_dataset.value.nfs_export_permissions.mode | string is match('^[0-7]{4}$')",
        "zfs_pools_nfs_mountpoint.stdout | trim is match('^/')",
        "zfs_pools_nfs_mountpoint.stdout | trim != '/'",
        "zfs_pools_nfs_mounted.stdout | trim == 'yes'",
        "zfs_pools_nfs_mountpoint_stat.stat.exists",
        "zfs_pools_nfs_mountpoint_stat.stat.isdir",
        "not zfs_pools_nfs_mountpoint_stat.stat.islnk",
    ]

    permissions = EXPORT_TASKS[set_permissions]["ansible.builtin.file"]
    assert permissions["path"] == "{{ zfs_pools_nfs_mountpoint.stdout | trim }}"
    assert permissions["state"] == "directory"
    assert permissions["owner"] == "{{ zfs_dataset.value.nfs_export_permissions.owner }}"
    assert permissions["group"] == "{{ zfs_dataset.value.nfs_export_permissions.group }}"
    assert permissions["mode"] == "{{ zfs_dataset.value.nfs_export_permissions.mode }}"
    assert EXPORT_TASKS[set_permissions]["when"] == "zfs_dataset.value.nfs_export_permissions is defined"
