# pve_guest_evacuation

This standalone role implements only the archive phase of a one-guest pve2
evacuation. It is inert by default and is not imported by `site.yml`.

With explicit enablement it verifies one guest belongs to pve2, rejects HA,
Proxmox replication, external devices and extra LXC mounts, requires zero ZFS
snapshots on pve2 and pve540, validates pve3-hosted shared NFS staging, stops
the guest gracefully with a force-stop fallback, and produces one `vzdump
--mode stop --compress zstd` archive. It records before/after archive volids,
size, SHA-256, `zstd -t`, extracted configuration, and archive verification in an
atomically-published pve3 evidence file.

VZDump uses the configurable local workspace
`pve_guest_evacuation_tmpdir` (default `/var/tmp`). Archive output still goes
to pve3, while the local workspace remains compatible with unprivileged LXC
UID mappings and the staging export's required `root_squash` policy.
Compression uses Proxmox's native `--zstd 0` auto mode by default, allowing
half of the source host's CPU cores to compress each subsequent archive.

`probe` and `cutover` deliberately fail closed. The role never restores,
migrates, deletes a source guest, changes cluster membership, or changes any
storage configuration.

Required run-time values are `pve_guest_evacuation_enabled=true`, one numeric
`pve_guest_evacuation_guest_vmid`, a run id, the pre-existing shared NFS
storage id, endpoint, export path, and a writable pve3 evidence directory.
