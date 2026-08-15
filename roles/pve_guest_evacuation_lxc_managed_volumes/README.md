# pve_guest_evacuation_lxc_managed_volumes

`pve_guest_evacuation_lxc_managed_volumes` is the final data-capture stage for
an evacuated LXC whose `mpN` entries are Proxmox-managed volumes. It exists
because a VZDump LXC restore can recreate those entries as empty target
skeletons rather than restore their payloads.

The role is inert by default. It is run only on the declared source node after
`pve_guest_evacuation_restore` has written a
`restore_pending_managed_mount_copy` record with
`pve_guest_evacuation_restore_lxc_mountpoint_strategy=manifested_copy`.

The source, target and staging hosts have no defaults. The caller names all
three (`pve_guest_evacuation_lxc_managed_volumes_source_node`,
`pve_guest_evacuation_lxc_managed_volumes_target_node`,
`pve_guest_evacuation_lxc_managed_volumes_staging_host`) and an unset value
fails closed.

## Safety contract

Before transferring one byte, it binds the archive evidence, pending restore
evidence, current source configuration, and current target configuration to the
same VMID and source digest. Both containers must be stopped. Each `mpN` must
have the same mount semantics, resolve through `pvesm path` to an existing
directory, and resolve to exactly one mounted ZFS dataset on each host. The
new target volume must be completely empty; the role never creates, deletes,
merges, overwrites, starts, snapshots, or rolls back anything.

The stopped-source transfer uses strict host-key-pinned SSH and rsync with
numeric ids, ACLs, xattrs, sparse files, hard links, and checksums. A checksum
dry run must be empty afterwards. For each volume it then compares deterministic
byte count, regular-file count, metadata, content, hard-link, numeric ACL, and
hex xattr manifests. The final evidence includes exact source/target volume
IDs, resolved paths, and ZFS dataset identities.

Evidence is a new root-only file on the staging host. Existing final or
temporary paths fail closed. A failed transfer writes one immutable failure
record and preserves the stopped target for investigation.

## Invocation

Supply identity values from the verified archive record and the pending restore
record. The root-owned source-host SSH identity and known-hosts paths are
deliberately explicit. The rsync host normally matches the target's inventory
endpoint literally. If it cannot, provide the sole approved alternate spelling
as a canonical FQDN; it is accepted only when both names resolve on the source
to a shared IPv4 address. Unapproved aliases remain rejected.

```bash
doppler run -- ./scripts/run-ansible.sh playbooks/transfer_evacuated_lxc_managed_volumes.yml \
  -e pve_guest_evacuation_lxc_managed_volumes_enabled=true \
  -e pve_guest_evacuation_lxc_managed_volumes_source_node=<source-inventory-key> \
  -e pve_guest_evacuation_lxc_managed_volumes_target_node=<target-inventory-key> \
  -e pve_guest_evacuation_lxc_managed_volumes_staging_host=<staging-inventory-key> \
  -e pve_guest_evacuation_lxc_managed_volumes_archive_run_id=<archive-run-id> \
  -e pve_guest_evacuation_lxc_managed_volumes_restore_run_id=<restore-run-id> \
  -e pve_guest_evacuation_lxc_managed_volumes_run_id=<new-volume-run-id> \
  -e pve_guest_evacuation_lxc_managed_volumes_expected_vmid=<vmid> \
  -e pve_guest_evacuation_lxc_managed_volumes_expected_config_digest=<source-config-digest> \
  -e pve_guest_evacuation_lxc_managed_volumes_expected_archive_sha256=<archive-sha256> \
  -e pve_guest_evacuation_lxc_managed_volumes_target_storage=<target-storage> \
  -e pve_guest_evacuation_lxc_managed_volumes_target_rsync_host=<target-inventory-host> \
  -e pve_guest_evacuation_lxc_managed_volumes_target_rsync_canonical_fqdn=<target-canonical-fqdn> \
  -e pve_guest_evacuation_lxc_managed_volumes_rsync_identity_file=<root-only-identity> \
  -e pve_guest_evacuation_lxc_managed_volumes_rsync_known_hosts_file=<root-only-known-hosts>
```
