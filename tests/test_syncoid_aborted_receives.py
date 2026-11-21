"""The aborted-receive guard accepts only literal replica dataset names; the abort runs only on a saved receive."""

from pathlib import Path
import re

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS = yaml.safe_load((ROOT / "roles/syncoid/tasks/aborted_receives.yml").read_text(encoding="utf-8"))
DECLARED = yaml.safe_load(
    (ROOT / "inventory/host_vars/pve-r710/05-aborted-replica-receives.yml").read_text(encoding="utf-8")
)["syncoid_aborted_replica_receives"]
DEFAULTS = yaml.safe_load((ROOT / "roles/syncoid/defaults/main.yml").read_text(encoding="utf-8"))


def _accepted(name):
    that = TASKS[0]["ansible.builtin.assert"]["that"]
    pattern = re.search(r"match\('(.*)'\)", that[1]).group(1).replace("\\\\", "\\")
    return bool(re.match(pattern, name)) and ".." not in name


def test_the_default_is_empty():
    assert DEFAULTS["syncoid_aborted_replica_receives"] == []


@pytest.mark.parametrize("name", DECLARED)
def test_every_declared_dataset_passes_the_guard(name):
    assert _accepted(name)


@pytest.mark.parametrize(
    "name",
    [
        "bulk/backups/x",
        "bulk/databases",
        "bulk/replica/pve-r540/subvol-1-disk-0@rebuild-final",
        "bulk/replica/pve-r540/subvol-1-disk-0/%recv",
        "bulk/replica/pve-r540/*",
        "bulk/replica/../backups",
        "bulk/replica/pve-r540/a b",
    ],
)
def test_the_guard_refuses(name):
    assert not _accepted(name)


def test_the_token_read_runs_in_check_mode_and_the_abort_does_not():
    assert TASKS[1]["check_mode"] is False
    assert TASKS[1]["ansible.builtin.command"]["argv"][:5] == ["zfs", "get", "-H", "-o", "value"]
    assert "check_mode" not in TASKS[-1]


def test_the_abort_is_receive_dash_a_on_one_dataset_with_a_saved_receive():
    abort = TASKS[-1]
    assert abort["ansible.builtin.command"]["argv"] == ["zfs", "receive", "-A", "{{ item.item }}"]
    assert "rejectattr('stdout', 'in', ['', '-'])" in abort["loop"]


def test_the_import_has_its_own_tag_and_runs_before_the_snapshot_destroy():
    main = yaml.safe_load((ROOT / "roles/syncoid/tasks/main.yml").read_text(encoding="utf-8"))
    imports = [t.get("ansible.builtin.import_tasks") for t in main]
    entry = main[imports.index("aborted_receives.yml")]
    assert entry["tags"] == ["syncoid", "syncoid_aborted_receives"]
    assert imports.index("aborted_receives.yml") < imports.index("retired_snapshots.yml")
