"""ZFS filesystem identity parser: tab-delimited fields, ambiguity rejection."""

from pathlib import Path

import pytest

from conftest import ROLE, flatten_included_tasks, run_zfs_dataset_identity_parser


def test_zfs_dataset_identity_parser_uses_actual_tab_delimited_fields(tmp_path: Path) -> None:
    """Run the extracted parser tasks against representative live ZFS output."""
    source_line = "bulk/subvol-519010-disk-1\t/bulk/subvol-519010-disk-1"
    target_line = "rpool/data/subvol-519010-disk-1\t/rpool/data/subvol-519010-disk-1"
    # This is the failure mode from the live output: matching a literal
    # backslash followed by t cannot find either actual tab-delimited record.
    assert [line for line in (source_line, target_line) if "\\t" in line] == []

    expected_mappings = [
        {
            "key": "mp0",
            "source_path": "/bulk/subvol-519010-disk-1",
            "target_path": "/rpool/data/subvol-519010-disk-1",
            "source_dataset_identity": [
                {"name": "bulk/subvol-519010-disk-1", "mountpoint": "/bulk/subvol-519010-disk-1"}
            ],
            "target_dataset_identity": [
                {
                    "name": "rpool/data/subvol-519010-disk-1",
                    "mountpoint": "/rpool/data/subvol-519010-disk-1",
                }
            ],
        }
    ]
    result = run_zfs_dataset_identity_parser(
        tmp_path,
        [source_line],
        [target_line],
        expected_mappings,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("source_lines", "target_lines", "failure_message"),
    [
        (
            ["bulk/subvol-519010-disk-1"],
            ["rpool/data/subvol-519010-disk-1\t/rpool/data/subvol-519010-disk-1"],
            "returned a ZFS filesystem inventory without one exact dataset-name",
        ),
        (
            ["bulk/subvol-519010-disk-1\t/bulk/subvol-519010-disk-1\textra"],
            ["rpool/data/subvol-519010-disk-1\t/rpool/data/subvol-519010-disk-1"],
            "returned a ZFS filesystem inventory without one exact dataset-name",
        ),
        (
            [
                "bulk/subvol-519010-disk-1\t/bulk/subvol-519010-disk-1",
                "bulk/duplicate\t/bulk/subvol-519010-disk-1",
            ],
            ["rpool/data/subvol-519010-disk-1\t/rpool/data/subvol-519010-disk-1"],
            "does not resolve to exactly one mounted ZFS dataset",
        ),
    ],
    ids=["one-field-record", "three-field-record", "duplicate-mountpoint-record"],
)
def test_zfs_dataset_identity_parser_rejects_ambiguous_records(
    tmp_path: Path,
    source_lines: list[str],
    target_lines: list[str],
    failure_message: str,
) -> None:
    result = run_zfs_dataset_identity_parser(tmp_path, source_lines, target_lines)

    assert result.returncode != 0
    assert failure_message in result.stdout + result.stderr


def test_zfs_dataset_identity_parser_contract_uses_field_parsing() -> None:
    transfer = flatten_included_tasks(ROLE / "tasks" / "transfer.yml")

    assert "Require two-field ZFS filesystem identity records" in transfer
    assert "pve_guest_evacuation_lxc_managed_volumes_zfs_record_separator: '{{ \"%c\" | format(9) }}'" in transfer
    assert "map('split', pve_guest_evacuation_lxc_managed_volumes_zfs_record_separator)" in transfer
    assert "Parse source ZFS filesystem identity records into name and mountpoint fields" in transfer
    assert "Parse target ZFS filesystem identity records into name and mountpoint fields" in transfer
    assert "selectattr('mountpoint', 'equalto', item.source_path)" in transfer
    assert "selectattr('mountpoint', 'equalto', item.target_path)" in transfer
    assert "select('match', '^.+\\\\t'" not in transfer


if __name__ == "__main__":
    test_zfs_dataset_identity_parser_contract_uses_field_parsing()
