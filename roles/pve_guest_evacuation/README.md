# pve_guest_evacuation

This standalone role implements only the archive phase of a one-guest node
evacuation. It is inert by default and is not imported by `site.yml`.

With explicit enablement it verifies one guest belongs to the declared source
node, rejects HA, Proxmox replication, external devices and extra LXC mounts,
requires zero ZFS snapshots on the source and target nodes, validates the
shared NFS staging exported by the declared staging host, stops the guest
gracefully with a force-stop fallback, and produces one `vzdump --mode stop
--compress zstd` archive. It records before/after archive volids, size,
SHA-256, `zstd -t`, extracted configuration, and archive verification in an
atomically-published evidence file on the staging host.

VZDump uses the configurable local workspace
`pve_guest_evacuation_tmpdir` (default `/var/tmp`). Archive output still goes
to the staging host, while the local workspace remains compatible with
unprivileged LXC UID mappings and the staging export's required `root_squash`
policy. Compression uses Proxmox's native `--zstd 0` auto mode by default,
allowing half of the source host's CPU cores to compress each subsequent
archive.

`probe` and `cutover` deliberately fail closed. The role never restores,
migrates, deletes a source guest, changes cluster membership, or changes any
storage configuration.

Required run-time values are `pve_guest_evacuation_enabled=true`, the three
node variables `pve_guest_evacuation_source_node`,
`pve_guest_evacuation_target_node` and `pve_guest_evacuation_staging_host`
(none of which have a default), one numeric
`pve_guest_evacuation_guest_vmid`, a run id, the pre-existing shared NFS
storage id, endpoint, export path, and a writable evidence directory on the
staging host.
