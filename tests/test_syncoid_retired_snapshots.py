"""The retired-replica-snapshot guard accepts only literal non-autosnap replica snapshot names."""

from pathlib import Path
import re

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS = yaml.safe_load((ROOT / "roles/syncoid/tasks/retired_snapshots.yml").read_text(encoding="utf-8"))
DECLARED = yaml.safe_load(
    (ROOT / "inventory/host_vars/pve-r710/04-retired-replica-snapshots.yml").read_text(encoding="utf-8")
)["syncoid_retired_replica_snapshots"]


def _accepted(name):
    that = TASKS[0]["ansible.builtin.assert"]["that"]
    pattern = re.search(r"match\('(.*)'\)", that[1]).group(1).replace("\\\\", "\\")
    return bool(re.match(pattern, name)) and ".." not in name and not name.split("@")[1].startswith("autosnap_")


@pytest.mark.parametrize("name", DECLARED)
def test_every_declared_snapshot_passes_the_guard(name):
    assert _accepted(name)


@pytest.mark.parametrize(
    "name",
    [
        "bulk/replica/pve-r540/subvol-1-disk-0@autosnap_2026-11-01_00:00:01_daily",
        "bulk/backups/x@rebuild-final",
        "bulk/databases@rebuild-final",
        "bulk/replica/pve-r540/subvol-1-disk-0",
        "bulk/replica/pve-r540/*@rebuild-final",
        "bulk/replica/pve-r540/subvol-1-disk-0@rebuild*",
        "bulk/replica/../backups@rebuild-final",
        "bulk/replica/pve-r540/subvol-1-disk-0@a b",
        "bulk/replica/pve-r540/subvol-1-disk-0@a@b",
    ],
)
def test_the_guard_refuses(name):
    assert not _accepted(name)


def test_no_declared_snapshot_is_a_clone_origin():
    assert not [name for name in DECLARED if name.endswith("@__base__")]


def test_the_destroy_never_recurses():
    destroy = TASKS[-1]["ansible.builtin.command"]["argv"]
    assert destroy[:2] == ["zfs", "destroy"] and len(destroy) == 3


def test_the_listing_runs_in_check_mode_and_the_destroy_does_not():
    assert TASKS[1]["check_mode"] is False
    assert "check_mode" not in TASKS[-1]
