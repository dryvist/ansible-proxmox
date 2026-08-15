#!/usr/bin/env python3
"""Static safety contract for the standalone archive-only evacuation role."""

import re
from pathlib import Path


ROLE = Path(__file__).resolve().parents[2] / "roles" / "pve_guest_evacuation"


def _flattened_archive() -> str:
    """tasks/archive.yml is a thin dispatcher over ordered phase files (split
    out for the token budget); inline them so the grep-based assertions below
    see the same content archive.yml held before the split."""
    text = (ROLE / "tasks" / "archive.yml").read_text()
    out = []
    pos = 0
    resolved = 0
    for match in re.finditer(
        r"- name:.*\n\s*ansible\.builtin\.include_tasks:\s*(\S+)\s*\n", text
    ):
        out.append(text[pos : match.start()])
        included = re.sub(r"^---\n", "", (ROLE / "tasks" / match.group(1)).read_text())
        out.append(included)
        pos = match.end()
        resolved += 1
    out.append(text[pos:])
    # Without this, a dispatcher entry the pattern fails to match is silently
    # dropped from the flattened text, and every assertion that greps for
    # something inside that phase file starts passing on absence instead.
    assert resolved == text.count("include_tasks:"), (
        f"{resolved} of {text.count('include_tasks:')} dispatcher includes were "
        "inlined — the assertions below would grep text that is not there"
    )
    return "".join(out)


def test_archive_uses_stop_mode_and_has_snapshot_gate() -> None:
    archive = _flattened_archive()

    assert "Assert no ZFS snapshots exist on either evacuation node" in archive
    assert "- snapshot" in archive
    assert "- --mode\n      - stop" in archive
    assert '- "{{ pve_guest_evacuation_tmpdir }}"' in archive
    assert "- snapshot\n" not in archive.split("Create a stop-mode VZDump archive", 1)[1]

    defaults = (ROLE / "defaults" / "main.yml").read_text()
    contract = (ROLE / "tasks" / "preflight_contract.yml").read_text()
    assert "pve_guest_evacuation_tmpdir: /var/tmp" in defaults
    assert "pve_guest_evacuation_tmpdir is match" in contract
    assert "pve_guest_evacuation_zstd_threads: 0" in defaults
    assert "pve_guest_evacuation_zstd_threads | int >= 0" in contract

    # The node variables must stay undefaulted and required: a default here is
    # what pinned this role to one node and made it unusable against any other.
    for var in ("source_node", "target_node", "staging_host"):
        assert not re.search(rf"^pve_guest_evacuation_{var}:", defaults, re.M)
        assert f"pve_guest_evacuation_{var} is defined" in contract
        assert f"pve_guest_evacuation_{var} | default('') | length > 0" in contract


def test_unsupported_phases_and_external_resources_are_fail_closed() -> None:
    contract = (ROLE / "tasks" / "preflight_contract.yml").read_text()
    gates = (ROLE / "tasks" / "resource_gates.yml").read_text()

    assert "pve_guest_evacuation_phase == 'archive'" in contract
    assert "unsupported and fail closed" in contract
    assert "lxc_bind_mount_keys" in gates
    assert "lxc_unbacked_mount_keys" in gates
    assert "lxc_external_keys" in gates
    archive = _flattened_archive()
    assert "Read each node's independent staging storage view" in archive
    assert "vma verify -" in archive


if __name__ == "__main__":
    test_archive_uses_stop_mode_and_has_snapshot_gate()
    test_unsupported_phases_and_external_resources_are_fail_closed()
