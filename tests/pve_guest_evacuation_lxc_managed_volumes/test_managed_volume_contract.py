"""Safety contract and parser regression for manifested LXC mpN transfers."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROLE = Path(__file__).resolve().parents[2] / "roles" / "pve_guest_evacuation_lxc_managed_volumes"


def run_zfs_dataset_identity_parser(
    tmp_path: Path,
    source_lines: list[str],
    target_lines: list[str],
    expected_mappings: list[dict[str, object]] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Execute the role's extracted parser tasks with fixture ZFS output."""
    ansible_playbook = shutil.which("ansible-playbook")
    if ansible_playbook is None:
        pytest.skip("ansible-playbook is required to execute the parser regression")

    transfer = (ROLE / "tasks" / "transfer.yml").read_text()
    parser_start = transfer.index("- name: Define the ZFS filesystem record separator")
    parser_end = transfer.index("- name: Assert no ZFS snapshots exist on either evacuation node")
    parser_path = tmp_path / "zfs-parser.yml"
    parser_path.write_text(transfer[parser_start:parser_end])

    zfs_filesystems = {
        "results": [
            {"item": "pve2", "stdout_lines": source_lines},
            {"item": "pve540", "stdout_lines": target_lines},
        ]
    }
    resolved_mappings = [
        {
            "key": "mp0",
            "source_path": "/bulk/subvol-519010-disk-1",
            "target_path": "/rpool/data/subvol-519010-disk-1",
        }
    ]
    playbook_tasks = "    - ansible.builtin.include_tasks: zfs-parser.yml\n"
    if expected_mappings is not None:
        playbook_tasks += (
            "    - ansible.builtin.assert:\n"
            "        that:\n"
            "          - pve_guest_evacuation_lxc_managed_volumes_dataset_mappings == "
            "expected_dataset_mappings\n"
        )
    playbook_path = tmp_path / "playbook.yml"
    playbook_path.write_text(
        "---\n"
        "- hosts: localhost\n"
        "  connection: local\n"
        "  gather_facts: false\n"
        "  vars:\n"
        "    pve_guest_evacuation_lxc_managed_volumes_zfs_filesystems: "
        f"{json.dumps(zfs_filesystems)}\n"
        "    pve_guest_evacuation_lxc_managed_volumes_resolved_mappings: "
        f"{json.dumps(resolved_mappings)}\n"
        "    expected_dataset_mappings: "
        f"{json.dumps(expected_mappings or [])}\n"
        "  tasks:\n"
        f"{playbook_tasks}"
    )
    return subprocess.run(
        [ansible_playbook, "-i", "localhost,", str(playbook_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )


def run_canonical_endpoint_contract(
    tmp_path: Path,
    canonical_fqdn: str,
    inventory_endpoint: str,
    canonical_ipv4s: list[str],
    inventory_ipv4s: list[str],
) -> subprocess.CompletedProcess[str]:
    """Execute the role's exact canonical-endpoint assertion with fixture DNS."""
    ansible_playbook = shutil.which("ansible-playbook")
    if ansible_playbook is None:
        pytest.skip("ansible-playbook is required to execute the endpoint regression")

    contract = (ROLE / "tasks" / "preflight_contract.yml").read_text()
    task_start = contract.index("- name: Derive pve2 IPv4 resolutions")
    endpoint_tasks = tmp_path / "endpoint-contract.yml"
    endpoint_tasks.write_text(contract[task_start:])

    def getent_lines(addresses: list[str]) -> list[str]:
        return [f"{address} STREAM" for address in addresses]

    playbook = tmp_path / "playbook.yml"
    playbook.write_text(
        "---\n"
        "- hosts: localhost\n"
        "  connection: local\n"
        "  gather_facts: false\n"
        "  vars:\n"
        f"    pve_guest_evacuation_lxc_managed_volumes_target_rsync_host: {json.dumps(canonical_fqdn)}\n"
        f"    pve_guest_evacuation_lxc_managed_volumes_target_rsync_canonical_fqdn: {json.dumps(canonical_fqdn)}\n"
        "    pve_guest_evacuation_lxc_managed_volumes_target_node: pve540\n"
        "    pve_guest_evacuation_lxc_managed_volumes_canonical_fqdn_resolution:\n"
        "      rc: 0\n"
        f"      stdout_lines: {json.dumps(getent_lines(canonical_ipv4s))}\n"
        "    pve_guest_evacuation_lxc_managed_volumes_inventory_endpoint_resolution:\n"
        "      rc: 0\n"
        f"      stdout_lines: {json.dumps(getent_lines(inventory_ipv4s))}\n"
        "  tasks:\n"
        "    - ansible.builtin.add_host:\n"
        "        name: pve540\n"
        f"        ansible_host: {json.dumps(inventory_endpoint)}\n"
        "    - ansible.builtin.include_tasks: endpoint-contract.yml\n"
    )
    return subprocess.run(
        [ansible_playbook, "-i", "localhost,", str(playbook)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )


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


def test_rsync_endpoint_keeps_the_literal_inventory_fast_path() -> None:
    contract = (ROLE / "tasks" / "preflight_contract.yml").read_text()

    assert (
        "pve_guest_evacuation_lxc_managed_volumes_target_rsync_host\n"
        "        == hostvars[pve_guest_evacuation_lxc_managed_volumes_target_node].ansible_host"
        in contract
    )
    assert "or (" in contract


def test_unequal_rsync_endpoint_requires_a_verified_canonical_fqdn() -> None:
    defaults = (ROLE / "defaults" / "main.yml").read_text()
    contract = (ROLE / "tasks" / "preflight_contract.yml").read_text()

    assert "pve_guest_evacuation_lxc_managed_volumes_target_rsync_canonical_fqdn: \"\"" in defaults
    assert "Resolve the approved pve540 canonical FQDN from pve2" in contract
    assert "Resolve the pve540 inventory endpoint from pve2" in contract
    assert "- ahostsv4" in contract
    assert "pve_guest_evacuation_lxc_managed_volumes_target_rsync_host\n              == pve_guest_evacuation_lxc_managed_volumes_target_rsync_canonical_fqdn" in contract
    assert "pve_guest_evacuation_lxc_managed_volumes_canonical_fqdn_ipv4s" in contract
    assert "pve_guest_evacuation_lxc_managed_volumes_inventory_endpoint_ipv4s" in contract
    assert "| intersect(pve_guest_evacuation_lxc_managed_volumes_inventory_endpoint_ipv4s)" in contract


def test_unequal_rsync_endpoint_rejects_aliases_and_unverified_resolution() -> None:
    contract = (ROLE / "tasks" / "preflight_contract.yml").read_text()

    assert "is match('^[A-Za-z0-9][A-Za-z0-9-]*(\\.[A-Za-z0-9][A-Za-z0-9-]*)+$')" in contract
    assert "is not match('^([0-9]{1,3}\\.){3}[0-9]{1,3}$')" in contract
    assert "pve_guest_evacuation_lxc_managed_volumes_canonical_fqdn_resolution.rc == 0" in contract
    assert "pve_guest_evacuation_lxc_managed_volumes_inventory_endpoint_resolution.rc == 0" in contract
    assert "pve_guest_evacuation_lxc_managed_volumes_canonical_fqdn_ipv4s | length > 0" in contract
    assert "pve_guest_evacuation_lxc_managed_volumes_inventory_endpoint_ipv4s | length > 0" in contract
    assert "unapproved aliases, IP literals, missing DNS results, and mismatches" in contract


def test_canonical_fqdn_endpoint_contract_accepts_a_matching_literal_inventory_ipv4(tmp_path: Path) -> None:
    result = run_canonical_endpoint_contract(
        tmp_path,
        "pve540.jacobpevans.com",
        "192.0.2.54",
        ["192.0.2.54"],
        ["192.0.2.54"],
    )

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("canonical_fqdn", "inventory_endpoint", "canonical_ipv4s", "inventory_ipv4s"),
    [
        ("pve540", "192.0.2.54", ["192.0.2.54"], ["192.0.2.54"]),
        ("192.0.2.54", "192.0.2.55", ["192.0.2.54"], ["192.0.2.55"]),
        ("pve540.jacobpevans.com", "192.0.2.54", ["192.0.2.55"], ["192.0.2.54"]),
    ],
    ids=["single-label-alias", "ip-literal", "dns-mismatch"],
)
def test_canonical_fqdn_endpoint_contract_rejects_invalid_or_mismatched_inputs(
    tmp_path: Path,
    canonical_fqdn: str,
    inventory_endpoint: str,
    canonical_ipv4s: list[str],
    inventory_ipv4s: list[str],
) -> None:
    result = run_canonical_endpoint_contract(
        tmp_path,
        canonical_fqdn,
        inventory_endpoint,
        canonical_ipv4s,
        inventory_ipv4s,
    )

    assert result.returncode != 0


def test_verified_fqdn_preserves_one_ed25519_key_and_strict_ssh() -> None:
    transfer = (ROLE / "tasks" / "transfer.yml").read_text()

    assert "| list | length == 1" in transfer
    assert "ssh-ed25519" in transfer
    for setting in (
        "StrictHostKeyChecking=yes",
        "UserKnownHostsFile={{ pve_guest_evacuation_lxc_managed_volumes_rsync_known_hosts_file }}",
        "GlobalKnownHostsFile=/dev/null",
        "PasswordAuthentication=no",
        "KbdInteractiveAuthentication=no",
    ):
        assert setting in transfer


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
    assert "getfacl --physical --absolute-names --numeric" in transfer
    assert "getfattr --absolute-names --no-dereference --encoding=hex" in transfer
    assert "-printf '%y\\t%m\\t%U\\t%G\\t%s" in transfer
    assert "(?:[^,]+,)*mp=/[^,]+" in transfer
    assert transfer.count("set -euo pipefail") >= 2
    assert "Require exact source and target manifest equality for every volume" in transfer
    assert "Require one exact ZFS dataset identity for each source and target volume" in transfer


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
    transfer = (ROLE / "tasks" / "transfer.yml").read_text()

    assert "Require two-field ZFS filesystem identity records" in transfer
    assert "pve_guest_evacuation_lxc_managed_volumes_zfs_record_separator: '{{ \"%c\" | format(9) }}'" in transfer
    assert "map('split', pve_guest_evacuation_lxc_managed_volumes_zfs_record_separator)" in transfer
    assert "Parse source ZFS filesystem identity records into name and mountpoint fields" in transfer
    assert "Parse target ZFS filesystem identity records into name and mountpoint fields" in transfer
    assert "selectattr('mountpoint', 'equalto', item.source_path)" in transfer
    assert "selectattr('mountpoint', 'equalto', item.target_path)" in transfer
    assert "select('match', '^.+\\\\t'" not in transfer


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
    assert "evidence_outputs.copy" in evidence
    assert "resume_evidence.rsync['copy']" in evidence
    assert evidence.count("result.stdout_lines | default([], true)") == 4
    assert evidence.count("default({}, true)") == 4
    assert "map(attribute='stdout_lines')" not in evidence


def test_resume_is_bound_to_exact_post_copy_failure_and_never_recopies() -> None:
    defaults = (ROLE / "defaults" / "main.yml").read_text()
    contract = (ROLE / "tasks" / "preflight_contract.yml").read_text()
    transfer = (ROLE / "tasks" / "transfer.yml").read_text()
    evidence = (ROLE / "templates" / "managed-volumes-evidence.json.j2").read_text()

    assert 'pve_guest_evacuation_lxc_managed_volumes_resume_from_run_id: ""' in defaults
    assert 'pve_guest_evacuation_lxc_managed_volumes_resume_evidence_sha256: ""' in defaults
    assert "managed-volumes-{{ pve_guest_evacuation_lxc_managed_volumes_resume_from_run_id }}" in defaults
    assert "resume_evidence_actual_sha256 == pve_guest_evacuation_lxc_managed_volumes_resume_evidence_sha256" in transfer
    assert "checkpoint == 'transfer_failed'" in transfer
    assert "failure.task == 'Build deterministic source byte file metadata ACL xattr manifests'" in transfer
    assert "resume_evidence.volumes == pve_guest_evacuation_lxc_managed_volumes_dataset_mappings" in transfer
    assert "rsync['copy'] | length" in transfer
    assert "rsync['checksum_dry_run'] | flatten | length == 0" in transfer
    assert ".rsync.copy" not in transfer
    assert "Require populated preserved targets for an explicit resume" in transfer
    copy_task = transfer[transfer.index("- name: Copy each stopped-source managed volume"):]
    copy_task = copy_task[:copy_task.index("- name: Require checksum dry run")]
    assert "resume_from_run_id | default('') | length == 0" in copy_task
    assert '"resume": {' in evidence
    assert "resume_evidence_sha256" in contract


def test_checksum_verification_rejects_extra_target_content_and_acl_is_physical() -> None:
    transfer = (ROLE / "tasks" / "transfer.yml").read_text()
    verify = transfer[transfer.index("- name: Require checksum dry run"):]
    verify = verify[:verify.index("- name: Assert checksum dry runs")]
    assert "- --dry-run" in verify
    assert "- --delete" in verify
    assert transfer.count("getfacl --physical --absolute-names --numeric") == 2


def test_missing_resume_evidence_metadata_fails_cleanly() -> None:
    transfer = (ROLE / "tasks" / "transfer.yml").read_text()
    evidence_gate = transfer[transfer.index("- name: Require protected immutable failed-transfer evidence"):]
    evidence_gate = evidence_gate[:evidence_gate.index("- name: Read exact immutable failed-transfer evidence")]

    assert "stat.exists | default(false)" in evidence_gate
    assert "stat.isreg | default(false)" in evidence_gate
    assert "stat.islnk | default(false)" in evidence_gate
    for field in ("pw_name", "gr_name", "mode", "checksum"):
        assert f"stat.{field} | default('')" in evidence_gate
    resume_conditions = [line for line in transfer.splitlines() if line.lstrip().startswith("when:") and "resume_from_run_id" in line]
    assert resume_conditions
    assert all("| default('') | length" in line for line in resume_conditions)


if __name__ == "__main__":
    test_role_is_inert_and_requires_exact_three_record_identity()
    test_rsync_endpoint_keeps_the_literal_inventory_fast_path()
    test_unequal_rsync_endpoint_requires_a_verified_canonical_fqdn()
    test_unequal_rsync_endpoint_rejects_aliases_and_unverified_resolution()
    test_verified_fqdn_preserves_one_ed25519_key_and_strict_ssh()
    test_transfer_requires_stopped_source_empty_target_and_no_snapshots()
    test_transfer_preserves_metadata_and_proves_each_volume()
    test_zfs_dataset_identity_parser_contract_uses_field_parsing()
    test_evidence_is_immutable_and_failure_preserves_the_target()
    test_resume_is_bound_to_exact_post_copy_failure_and_never_recopies()
    test_checksum_verification_rejects_extra_target_content_and_acl_is_physical()
    test_missing_resume_evidence_metadata_fails_cleanly()
