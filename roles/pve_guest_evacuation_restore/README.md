# pve_guest_evacuation_restore

`pve_guest_evacuation_restore` is the second, standalone evacuation slice: it
restores exactly one completed `pve_guest_evacuation` archive onto the
standalone target node. It is not loaded by `site.yml` and has no effect until
`pve_guest_evacuation_restore_enabled=true` is supplied to
`playbooks/restore_evacuated_guest.yml`.

The source, target and staging hosts have no defaults. The caller names all
three (`pve_guest_evacuation_restore_source_node`,
`pve_guest_evacuation_restore_target_node`,
`pve_guest_evacuation_restore_staging_host`) and an unset value fails closed.

## Restore contract

Before it writes to the target, the role requires explicit VMID, guest type,
source-config digest, archive SHA-256, original archive run id, and a new
restore run id. It derives the archive evidence path from the original run id
and VMID under the caller-supplied
`pve_guest_evacuation_restore_evidence_dir` (no default), reads that root-only
staging record, and requires its final `archive_verified` checkpoint.

The evidence must say the archive came from the declared source node and was
intended for the declared target. The role validates the archive SHA-256,
`zstd -t`, and the target's extracted configuration against the evidence. This
uses Proxmox's native `pvesm extractconfig` facility for a VZDump archive
without creating a multi-terabyte temporary decompression file.

The explicit destination storage must already be active on the target, support
`images` for QEMU or `rootdir` for LXC, and differ from the backup-only staging
storage. The role also independently verifies the target's staging NFS view
from the selected archive evidence.

## Target safety

The role refuses a VMID that already exists as either a QEMU VM or LXC
container, validates that the target has no ZFS snapshots, and invokes only one
of `qmrestore` or `pct restore` with `--storage <explicit-target>`. It never
starts the target, changes the source node, or invokes any snapshot, rollback,
destroy, free, or removal command.

After restoration it requires a stopped guest, a target config digest, the
same backed disk or mount keys captured in the archive evidence, and every
resulting volume to resolve on the explicit target storage. Storage relocation
can change Proxmox disk references, so the exact source digest is used to bind
the archive evidence before restore; disk and configuration structure are then
verified on the target after the intentional storage placement.

For an LXC with managed `mpN` volumes, VZDump restoration deliberately remains
refused by default because Proxmox can create empty target skeletons. The only
supported opt-in is `pve_guest_evacuation_restore_lxc_mountpoint_strategy=
manifested_copy`; it writes a `restore_pending_managed_mount_copy` evidence
record while leaving the stopped target intact. Follow it with
`playbooks/transfer_evacuated_lxc_managed_volumes.yml`, which requires an empty
target volume, a stopped source, a checksum rsync transfer, and exact
per-volume manifests before it writes final immutable evidence.

## Evidence and failure policy

The result is atomically written as a new, root-owned `0600` file below the
root-only staging evidence directory. Existing final or temporary evidence
files cause a failure rather than an overwrite. A restore failure records a
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
  -e pve_guest_evacuation_restore_source_node=<source-inventory-key> \
  -e pve_guest_evacuation_restore_target_node=<target-inventory-key> \
  -e pve_guest_evacuation_restore_staging_host=<staging-inventory-key> \
  -e pve_guest_evacuation_restore_archive_run_id=<verified-archive-run-id> \
  -e pve_guest_evacuation_restore_run_id=<new-restore-run-id> \
  -e pve_guest_evacuation_restore_expected_vmid=<vmid> \
  -e pve_guest_evacuation_restore_expected_guest_type=<qemu-or-lxc> \
  -e pve_guest_evacuation_restore_expected_config_digest=<source-config-digest> \
  -e pve_guest_evacuation_restore_expected_archive_sha256=<archive-sha256> \
  -e pve_guest_evacuation_restore_target_storage=<active-target-storage>
```
