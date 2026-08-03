"""Static safety contract for manifested LXC mpN evacuation transfers."""

from pathlib import Path


ROLE = Path(__file__).resolve().parents[2] / "roles" / "pve_guest_evacuation_lxc_managed_volumes"


def test_role_is_inert_and_requires_exact_three_record_identity() -> None:
    defaults = (ROLE / "defaults" / "main.yml").read_text()
    contract = (ROLE / "tasks" / "preflight_contract.yml").read_text()
    transfer = (ROLE / "tasks" / "transfer.yml").read_text()

    assert "pve_guest_evacuation_lxc_managed_volumes_enabled: false" in defaults
    for value in (
        "archive_run_id",
        "restore_run_id",
        "expected_vmid",
        "expected_config_digest",
        "expected_archive_sha256",
        "target_storage",
    ):
        assert f"pve_guest_evacuation_lxc_managed_volumes_{value}" in contract
    assert "archive_verified" in transfer
    assert "restore_pending_managed_mount_copy" in transfer
    assert "source_config.digest == pve_guest_evacuation_lxc_managed_volumes_expected_config_digest" in transfer
    assert "Require a root-only non-symlink pve3 evidence directory" in transfer
    assert "pve_guest_evacuation_lxc_managed_volumes_evidence_dir_stat.stat.mode == '0700'" in transfer
    assert transfer.index("Check managed-volume evidence paths before transfer gates") < transfer.index(
        "Read pve3 archive and pending-restore evidence"
    )
    assert "hostvars[pve_guest_evacuation_lxc_managed_volumes_target_node].ansible_host is defined" in contract


def test_transfer_requires_stopped_source_empty_target_and_no_snapshots() -> None:
    transfer = (ROLE / "tasks" / "transfer.yml").read_text()

    assert "pve_guest_evacuation_lxc_managed_volumes_source_status.status == 'stopped'" in transfer
    assert "pve_guest_evacuation_lxc_managed_volumes_target_status.status == 'stopped'" in transfer
    assert "Require the target managed volumes to be empty skeletons" in transfer
    assert "Refuse to overwrite any preexisting target managed-volume content" in transfer
    assert "Assert no ZFS snapshots exist on either evacuation node" in transfer
    assert "zfs, snapshot" not in transfer
    assert "zfs, destroy" not in transfer
    assert "pct, destroy" not in transfer
    assert "pct, start" not in transfer


def test_transfer_preserves_metadata_and_proves_each_volume() -> None:
    transfer = (ROLE / "tasks" / "transfer.yml").read_text()

    for rsync_flag in (
        "--hard-links",
        "--acls",
        "--xattrs",
        "--numeric-ids",
        "--checksum",
        "--dry-run",
    ):
        assert rsync_flag in transfer
    for manifest in ("bytes", "files", "metadata", "content", "hardlinks", "acl", "xattr"):
        assert f"printf '{manifest} " in transfer
    assert "getfacl --absolute-names --numeric" in transfer
    assert "getfattr --absolute-names --no-dereference --encoding=hex" in transfer
    assert "-printf '%y\\t%m\\t%U\\t%G\\t%s" in transfer
    assert "(?:[^,]+,)*mp=/[^,]+" in transfer
    assert transfer.count("set -euo pipefail") >= 2
    assert "Require exact source and target manifest equality for every volume" in transfer
    assert "Require one exact ZFS dataset identity for each source and target volume" in transfer


def test_evidence_is_immutable_and_failure_preserves_the_target() -> None:
    main = (ROLE / "tasks" / "main.yml").read_text()
    writer = (ROLE / "tasks" / "write_evidence.yml").read_text()
    evidence = (ROLE / "templates" / "managed-volumes-evidence.json.j2").read_text()
    transfer = (ROLE / "tasks" / "transfer.yml").read_text()

    assert "Refuse to overwrite managed-volume transfer evidence" in writer
    assert "- ln" in writer
    assert "preserved" in main
    assert "source_dataset_identity" in transfer
    assert "target_dataset_identity" in transfer
    assert "source_manifests" in evidence
    assert "target_manifests" in evidence


if __name__ == "__main__":
    test_role_is_inert_and_requires_exact_three_record_identity()
    test_transfer_requires_stopped_source_empty_target_and_no_snapshots()
    test_transfer_preserves_metadata_and_proves_each_volume()
    test_evidence_is_immutable_and_failure_preserves_the_target()
