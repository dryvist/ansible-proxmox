#!/usr/bin/env python3
"""Static safety contract for the standalone archive-only evacuation role."""

from pathlib import Path


ROLE = Path(__file__).resolve().parents[2] / "roles" / "pve_guest_evacuation"


def test_archive_uses_stop_mode_and_has_snapshot_gate() -> None:
    archive = (ROLE / "tasks" / "archive.yml").read_text()

    assert "Assert no ZFS snapshots exist on either evacuation node" in archive
    assert "- snapshot" in archive
    assert "- --mode\n      - stop" in archive
    assert "- snapshot\n" not in archive.split("Create a stop-mode VZDump archive", 1)[1]


def test_unsupported_phases_and_external_resources_are_fail_closed() -> None:
    contract = (ROLE / "tasks" / "preflight_contract.yml").read_text()
    gates = (ROLE / "tasks" / "resource_gates.yml").read_text()

    assert "pve_guest_evacuation_phase == 'archive'" in contract
    assert "unsupported and fail closed" in contract
    assert "lxc_bind_mount_keys" in gates
    assert "lxc_unbacked_mount_keys" in gates
    assert "lxc_external_keys" in gates
    assert "Read each node's independent staging storage view" in (ROLE / "tasks" / "archive.yml").read_text()
    assert "vma verify -" in (ROLE / "tasks" / "archive.yml").read_text()


if __name__ == "__main__":
    test_archive_uses_stop_mode_and_has_snapshot_gate()
    test_unsupported_phases_and_external_resources_are_fail_closed()
