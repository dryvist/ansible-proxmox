"""Evidence immutability and resume contract: bound to the exact failed run."""

from conftest import ROLE, flatten_included_tasks


def test_role_is_inert_and_requires_exact_three_record_identity() -> None:
    defaults = (ROLE / "defaults" / "main.yml").read_text()
    contract = (ROLE / "tasks" / "preflight_contract.yml").read_text()
    transfer = flatten_included_tasks(ROLE / "tasks" / "transfer.yml")

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


def test_evidence_is_immutable_and_failure_preserves_the_target() -> None:
    main = (ROLE / "tasks" / "main.yml").read_text()
    writer = (ROLE / "tasks" / "write_evidence.yml").read_text()
    evidence = (ROLE / "templates" / "managed-volumes-evidence.json.j2").read_text()
    transfer = flatten_included_tasks(ROLE / "tasks" / "transfer.yml")

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
    transfer = flatten_included_tasks(ROLE / "tasks" / "transfer.yml")
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


def test_missing_resume_evidence_metadata_fails_cleanly() -> None:
    transfer = flatten_included_tasks(ROLE / "tasks" / "transfer.yml")
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
    test_evidence_is_immutable_and_failure_preserves_the_target()
    test_resume_is_bound_to_exact_post_copy_failure_and_never_recopies()
    test_missing_resume_evidence_metadata_fails_cleanly()
