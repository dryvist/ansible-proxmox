"""Transfer safety contract: stopped/empty/no-snapshot gates, metadata preservation."""

from conftest import ROLE, flatten_included_tasks


def test_transfer_requires_stopped_source_empty_target_and_no_snapshots() -> None:
    transfer = flatten_included_tasks(ROLE / "tasks" / "transfer.yml")

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
    transfer = flatten_included_tasks(ROLE / "tasks" / "transfer.yml")

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
    assert "getfacl --physical --absolute-names --numeric" in transfer
    assert "getfattr --absolute-names --no-dereference --encoding=hex" in transfer
    assert "-printf '%y\\t%m\\t%U\\t%G\\t%s" in transfer
    assert "(?:[^,]+,)*mp=/[^,]+" in transfer
    assert transfer.count("set -euo pipefail") >= 2
    assert "Require exact source and target manifest equality for every volume" in transfer
    assert "Require one exact ZFS dataset identity for each source and target volume" in transfer


def test_checksum_verification_rejects_extra_target_content_and_acl_is_physical() -> None:
    transfer = flatten_included_tasks(ROLE / "tasks" / "transfer.yml")
    verify = transfer[transfer.index("- name: Require checksum dry run"):]
    verify = verify[:verify.index("- name: Assert checksum dry runs")]
    assert "- --dry-run" in verify
    assert "- --delete" in verify
    assert transfer.count("getfacl --physical --absolute-names --numeric") == 2


if __name__ == "__main__":
    test_transfer_requires_stopped_source_empty_target_and_no_snapshots()
    test_transfer_preserves_metadata_and_proves_each_volume()
    test_checksum_verification_rejects_extra_target_content_and_acl_is_physical()
