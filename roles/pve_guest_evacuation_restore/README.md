# pve_guest_evacuation_restore

`pve_guest_evacuation_restore` is the second, standalone issue-816 slice: it
restores exactly one completed `pve_guest_evacuation` archive onto standalone
pve540. It is not loaded by `site.yml` and has no effect until
`pve_guest_evacuation_restore_enabled=true` is supplied to
`playbooks/restore_evacuated_guest.yml`.

## Restore contract

Before it writes to pve540, the role requires explicit VMID, guest type,
source-config digest, archive SHA-256, original archive run id, and a new
restore run id. It derives the archive evidence path from the original run id
and VMID under `/bulk/evacuation-816/evidence`, reads that root-only pve3
record, and requires its final `archive_verified` checkpoint.

The evidence must say the archive came from pve2 and was intended for pve540.
The role validates the archive SHA-256, `zstd -t`, and pve540's extracted
configuration against the evidence. This uses Proxmox's native
`pvesm extractconfig` facility for a VZDump archive without creating a
multi-terabyte temporary decompression file.

The explicit destination storage must already be active on pve540, support
`images` for QEMU or `rootdir` for LXC, and differ from the backup-only staging
storage. The role also independently verifies pve540's staging NFS view from
the selected archive evidence.

## Target safety

The role refuses a VMID that already exists as either a QEMU VM or LXC
container, validates that pve540 has no ZFS snapshots, and invokes only one of
`qmrestore` or `pct restore` with `--storage <explicit-target>`. It never
starts the target, changes pve2, or invokes any snapshot, rollback, destroy,
free, or removal command.

After restoration it requires a stopped guest, a target config digest, the
same backed disk or mount keys captured in the archive evidence, and every
resulting volume to resolve on the explicit target storage. Storage relocation
can change Proxmox disk references, so the exact source digest is used to bind
the archive evidence before restore; disk and configuration structure are then
verified on pve540 after the intentional storage placement.

## Evidence and failure policy

The result is atomically written as a new, root-owned `0600` file below the
root-only pve3 evidence directory. Existing final or temporary evidence files
cause a failure rather than an overwrite. A restore failure records a
`restore_failed` checkpoint when evidence publication has not already begun.

There is no automated rollback. If `qmrestore` or `pct restore` has created a
partial target when another assertion fails, that target is intentionally
preserved for investigation. No target or archive deletion is part of this
role.

## Invocation

Supply every identity value from the previously verified archive evidence;
placeholders below are intentional:

```bash
doppler run -- ./scripts/run-ansible.sh playbooks/restore_evacuated_guest.yml \
  -e pve_guest_evacuation_restore_enabled=true \
  -e pve_guest_evacuation_restore_archive_run_id=<verified-archive-run-id> \
  -e pve_guest_evacuation_restore_run_id=<new-restore-run-id> \
  -e pve_guest_evacuation_restore_expected_vmid=<vmid> \
  -e pve_guest_evacuation_restore_expected_guest_type=<qemu-or-lxc> \
  -e pve_guest_evacuation_restore_expected_config_digest=<source-config-digest> \
  -e pve_guest_evacuation_restore_expected_archive_sha256=<archive-sha256> \
  -e pve_guest_evacuation_restore_target_storage=<active-pve540-storage>
```
