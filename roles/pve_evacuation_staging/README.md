# pve_evacuation_staging

`pve_evacuation_staging` provisions the temporary, backup-only NFS staging
surface for issue 816. It is deliberately separate from `site.yml` and is
inert until `pve_evacuation_staging_enabled=true` is supplied to
`playbooks/pve2_evacuation_staging.yml`.

## What it provisions

1. On pve3, an owned `bulk/evacuation-816` ZFS dataset mounted at
   `/bulk/evacuation-816`. Its backup surface is owned by Debian's
   `nobody:nogroup` anonymous NFS identity and mode `0700`, so root-squashed
   pve2 and pve540 writes work without granting access to other local users.
   `/bulk/evacuation-816/manifests` is a separate anonymous-identity-owned
   surface for snapshot-free comparison manifests. `/bulk/evacuation-816/evidence`
   is created separately as root-owned, root-only pve3-local archive evidence.
2. A quota, reservation, and retained-pool-headroom guard based on the reviewed
   migration budget. The role fails before creation when the full configured
   quota would infringe the retained headroom.
3. Debian's supported `nfs-kernel-server`, enabled through `nfs-server`.
4. One ZFS-managed NFS export with synchronous writes and root squash. Its
   allow-list is exactly the pve2 and pve540 management endpoints supplied by
   `PVE2_VE_HOSTNAME` and `PVE5_VE_HOSTNAME`.
5. An `evacuation-816` NFS storage view with `content=backup` on pve2, then an
   independent view with the same endpoint, export, and storage ID on standalone
   pve540. The pve2 view is scoped to pve2; pve540 is never added to the pve2
   cluster configuration.

The role creates neither snapshots nor replication state, does not change a
ZFS pool, and does not operate on guests.

## Enable only with a reviewed capacity budget

The role has no default quota, reservation, or headroom because those are live
capacity decisions. Supply all three values explicitly after confirming the
staging budget and pve3 pool capacity:

```bash
doppler run -- ./scripts/run-ansible.sh playbooks/pve2_evacuation_staging.yml \
  -e pve_evacuation_staging_enabled=true \
  -e pve_evacuation_staging_quota=<reviewed-zfs-size> \
  -e pve_evacuation_staging_reservation=<reviewed-zfs-size> \
  -e pve_evacuation_staging_pool_headroom=<reviewed-zfs-size>
```

`reservation` must not exceed `quota`. The guard accounts for an existing
owned staging dataset's used space and reservation, then requires enough free
space for its remaining quota while retaining the configured headroom.

## Verification contract

The server verifies the running NFS export through `exportfs -v` and checks
that the anonymous identity used by root squash has write access to the backup
surface without creating a probe file. Each client independently scans pve3's
export, reads its own `/storage/<id>` API view, and requires exactly `nfs`,
the shared endpoint, `/bulk/evacuation-816`, `backup` content, and its own
node restriction. It also requires its `pvesm status` view to be active.

The first reviewed archive run remains the real end-to-end client write proof;
this role deliberately does not create then delete a synthetic NFS artifact.

An existing dataset needs the `org.dryvist:purpose=pve2-evacuation-816` marker;
an existing storage ID needs the exact expected configuration. These checks
preserve evidence and stop rather than adopting or rewriting another resource.

## Cleanup contract

After migration validation, backup-retention sign-off, and removal of all
references to `evacuation-816`, cleanup is a separately approved operation:

1. Confirm the backup chain and restoration evidence are retained elsewhere.
2. Remove the pve2 storage view from its cluster configuration and remove the
   standalone pve540 view independently.
3. Retire the pve3 export and only then remove the dedicated dataset after its
   preserved contents are no longer required.

This role intentionally contains no destructive cleanup task. The staging
dataset and associated evidence remain available until that later approval.
