# pve_frozen_host_bind_copy

An intentionally inert, fail-closed one-way migration role for the six pve2
media containers with host bind mounts. Its approved mapping is fixed in the
role and is discovered again from live `pct config` before transfer.

Set `pve_frozen_host_bind_copy_enabled=true` only after pve2 holds dedicated,
root-owned transport files and you supply a new evidence run identifier. The
destination must exactly match pve540's inventory endpoint; the role rejects
arbitrary remote-shell strings and builds its own strict, non-interactive SSH
transport with the dedicated known-hosts file:

```yaml
pve_frozen_host_bind_copy_target_rsync_host: pve540.example.internal
pve_frozen_host_bind_copy_rsync_identity_file: /root/.ssh/pve540-copy
pve_frozen_host_bind_copy_rsync_known_hosts_file: /root/.ssh/pve540-copy-known-hosts
pve_frozen_host_bind_copy_run_id: 20260802T000000Z
```

The role validates the exact live `pct config` host binds for all six approved
containers, including download-vpn's single TUN mapping; it rejects an extra
bind, raw mount, or device mapping. It requires every container stopped, zero
ZFS snapshots and zero pending pool frees on both nodes, active `bulk/data` and
`bulk/appdata` datasets at their approved mountpoints, existing target paths,
empty target paths, and per-dataset capacity. A nonempty pve540 target fails
without modification so the result's hard-link topology cannot inherit an
unrelated destination link. It uses archive, ACL, xattr, numeric-ID, sparse,
hard-link, and one-filesystem rsync flags without deletion. The strict SSH
preflight, checksum dry run, and deterministic numeric-ID metadata, content,
and hard-link-group manifests must all match.

Each successful pre-copy gate and final verification is recorded in a new,
root-owned pve3 evidence directory. A reused run ID fails rather than replacing
prior evidence. The role never creates a snapshot, dataset, target copy path,
or Proxmox resource.
