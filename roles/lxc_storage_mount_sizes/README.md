# lxc_storage_mount_sizes

Grows declared Proxmox LXC storage-volume mount points from the published
`containers_from_tofu` inventory. The role compares live cluster placement,
`pct config`, and the storage's available bytes before it calls `pct resize`.
It skips binds and refuses identity mismatches, locks, migrations, shrink
requests, missing headroom, and incomplete live state. It never shrinks a mount.

The role runs after the mount-producing LXC roles in `playbooks/site.yml` and
is selected with the `lxc_storage_mount_sizes` tag. An empty
`lxc_storage_mount_sizes_guest_keys` list selects every declared storage mount;
set it to container keys for a scoped run.
