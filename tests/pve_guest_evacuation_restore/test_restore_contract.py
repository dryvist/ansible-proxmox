"""Static safety contract for the standalone restore-only evacuation role."""

import re
from pathlib import Path


ROLE = Path(__file__).resolve().parents[2] / "roles" / "pve_guest_evacuation_restore"


def _flattened_restore() -> str:
    """tasks/restore.yml is a thin dispatcher over ordered phase files (split
    out for the token budget); inline them so the grep-based assertions below
    see the same content restore.yml held before the split."""
    text = (ROLE / "tasks" / "restore.yml").read_text()
    out = []
    pos = 0
    for match in re.finditer(
        r"- name:.*\n\s*ansible\.builtin\.include_tasks:\s*(\S+)\s*\n", text
    ):
        out.append(text[pos : match.start()])
        included = re.sub(r"^---\n", "", (ROLE / "tasks" / match.group(1)).read_text())
        out.append(included)
        pos = match.end()
    out.append(text[pos:])
    return "".join(out)


def test_restore_requires_exact_verified_archive_identity() -> None:
    contract = (ROLE / "tasks" / "preflight_contract.yml").read_text()
    restore = _flattened_restore()

    assert "pve_guest_evacuation_restore_expected_vmid" in contract
    assert "pve_guest_evacuation_restore_expected_guest_type" in contract
    assert "pve_guest_evacuation_restore_expected_config_digest" in contract
    assert "pve_guest_evacuation_restore_expected_archive_sha256" in contract
    assert "checkpoint == 'archive_verified'" in restore
    assert "guest.source_node == pve_guest_evacuation_restore_source_node" in restore
    assert "guest.config.digest == pve_guest_evacuation_restore_expected_config_digest" in restore
    assert "archive.sha256 == pve_guest_evacuation_restore_expected_archive_sha256" in restore


def test_restore_verifies_archive_before_writing_target() -> None:
    restore = _flattened_restore()

    assert "zstd" in restore
    assert "vma verify" not in restore
    assert "pvesm\n      - extractconfig" in restore
    assert restore.index("Require the archive SHA-256") < restore.index("Restore the verified QEMU archive")
    assert restore.index("Require the archived configuration") < restore.index("Restore the verified QEMU archive")


def test_restore_preserves_target_and_uses_only_native_restore_commands() -> None:
    main = (ROLE / "tasks" / "main.yml").read_text()
    restore = _flattened_restore()
    writer = (ROLE / "tasks" / "write_evidence.yml").read_text()

    assert "qmrestore" in restore
    assert "pct\n      - restore" in restore
    assert "--storage" in restore
    assert "status == 'stopped'" in restore
    assert "pvesm\n      - free" not in restore
    assert "qm\n      - destroy" not in restore
    assert "pct\n      - destroy" not in restore
    assert "zfs\n      - snapshot" not in restore
    assert "qm\n      - start" not in restore
    assert "pct\n      - start" not in restore
    assert "preserved for investigation" in main
    assert "- ln" in writer


def test_restore_refuses_lxc_mountpoint_volumes_before_creating_a_target() -> None:
    restore = _flattened_restore()

    assert "pve_guest_evacuation_restore_lxc_mountpoint_volume_keys" in restore
    assert "Refuse automatic restore of LXC archives with additional backed mounts" in restore
    assert "Proxmox can recreate their volume configuration without restoring their" in restore
    assert "pve_guest_evacuation_restore_lxc_mountpoint_strategy == 'manifested_copy'" in restore
    assert restore.index("Refuse automatic restore of LXC archives with additional backed mounts") < restore.index(
        "Restore the verified LXC archive"
    )


def test_manifested_lxc_restore_is_explicitly_pending_not_verified() -> None:
    restore = _flattened_restore()
    defaults = (ROLE / "defaults" / "main.yml").read_text()

    assert "pve_guest_evacuation_restore_lxc_mountpoint_strategy: refuse" in defaults
    assert "restore_pending_managed_mount_copy" in restore


if __name__ == "__main__":
    test_restore_requires_exact_verified_archive_identity()
    test_restore_verifies_archive_before_writing_target()
    test_restore_preserves_target_and_uses_only_native_restore_commands()
    test_restore_refuses_lxc_mountpoint_volumes_before_creating_a_target()
