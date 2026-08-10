"""Static safety contract for the frozen pve2 to pve540 host-bind copy."""

import re
from pathlib import Path


ROLE = Path(__file__).resolve().parents[2] / "roles" / "pve_frozen_host_bind_copy"


def _flattened_tasks() -> str:
    """tasks/main.yml is a thin dispatcher over ordered phase files (split out
    for the token budget); inline them so the grep-based assertions below see
    the same content main.yml held before the split."""
    text = (ROLE / "tasks" / "main.yml").read_text()
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


def test_frozen_contract_covers_exactly_the_six_live_media_containers() -> None:
    contract = (ROLE / "vars" / "main.yml").read_text()

    expected = {
        "703040": ["/bulk/data", "/bulk/appdata/plex"],
        "715240": ["/bulk/data", "/bulk/appdata/sonarr"],
        "715340": ["/bulk/data", "/bulk/appdata/radarr"],
        "725140": ["/bulk/data", "/bulk/appdata/prowlarr"],
        "736030": ["/bulk/appdata/seerr"],
        "736040": ["/bulk/appdata/sortarr"],
    }

    for vmid, paths in expected.items():
        assert f'"{vmid}":' in contract
        for path in paths:
            assert f"source: {path}" in contract

    assert "source_dataset: bulk/data" in contract
    assert "target_dataset: bulk/data" in contract
    assert "source_dataset: bulk/appdata" in contract
    assert "target_dataset: bulk/appdata" in contract


def test_live_guards_are_exact_and_fail_closed() -> None:
    tasks = _flattened_tasks()

    assert "inventory_hostname == 'pve2'" in tasks
    assert "pve_frozen_host_bind_copy_target_inventory_host == 'pve540'" in tasks
    assert "pve_frozen_host_bind_copy_evidence_inventory_host == 'pve3'" in tasks
    assert "^mp[0-9]+:" in tasks
    assert "regex_escape" in tasks
    assert "pve_frozen_host_bind_copy_tun_cgroup_line" in tasks
    assert "pve_frozen_host_bind_copy_tun_mount_line" in tasks
    assert "Require the frozen six-container and dataset contract" in tasks
    assert "pve_frozen_host_bind_copy_source_pool == 'bulk'" in tasks
    assert "pve_frozen_host_bind_copy_target_pool == 'bulk'" in tasks
    assert "zpool, get, -H, -p, -o, value, freeing" in tasks
    assert "zfs, get, -H, -p, -o, value, freeing" not in tasks
    assert "if item.side == 'target' else inventory_hostname" in tasks
    assert "mountpoint" in tasks


def test_rsync_is_strict_one_way_and_non_destructive() -> None:
    tasks = _flattened_tasks()

    for flag in [
        "--archive",
        "--hard-links",
        "--acls",
        "--xattrs",
        "--numeric-ids",
        "--sparse",
        "--one-file-system",
        "--checksum",
        "--dry-run",
        "StrictHostKeyChecking=yes",
        "BatchMode=yes",
        "IdentitiesOnly=yes",
        "GlobalKnownHostsFile=/dev/null",
        "reject('match', '^# ')",
    ]:
        assert flag in tasks

    assert "root@{{ pve_frozen_host_bind_copy_target_rsync_host }}:" in tasks
    assert "Require every approved target directory to be empty" in tasks
    assert "--delete" not in tasks
    assert "zfs, snapshot" not in tasks
    assert "zfs, destroy" not in tasks
    assert "zpool, destroy" not in tasks
    assert "pvesm, free" not in tasks
    assert "pct, destroy" not in tasks
    assert "pct, start" not in tasks


def test_evidence_is_immutable_and_manifests_are_numeric() -> None:
    tasks = _flattened_tasks()

    assert "pve_frozen_host_bind_copy_run_id" in tasks
    assert "copy_gated" in tasks
    assert "copy_verified" in tasks
    assert "Refuse to overwrite existing pve3 frozen-copy evidence" in tasks
    assert "force: false" in tasks
    assert "%u\\t%g" in tasks
    assert "%l\\t%p" in tasks
    assert "printf 'hardlinks '" in tasks
    assert "-links +1" in tasks


if __name__ == "__main__":
    test_frozen_contract_covers_exactly_the_six_live_media_containers()
    test_live_guards_are_exact_and_fail_closed()
    test_rsync_is_strict_one_way_and_non_destructive()
    test_evidence_is_immutable_and_manifests_are_numeric()
