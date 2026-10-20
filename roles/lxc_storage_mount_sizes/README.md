# lxc_storage_mount_sizes

Reconciles declared Proxmox LXC storage-volume mounts from the published
`containers_from_tofu` inventory by growing existing mounts and attaching
missing mounts at their declared `mp_index` only when the slot is free and the
storage has headroom for the full allocation. It retains the placement,
identity, lock, migration, and no-shrink guards, skips bind mounts, refuses
occupied indices, and reads `/pending` after attach to restart only when the
new mount did not hotplug live.

The role runs after the mount-producing LXC roles in `playbooks/site.yml` and
is selected with the `lxc_storage_mount_sizes` tag. An empty
`lxc_storage_mount_sizes_guest_keys` list selects every declared storage mount;
set it to container keys for a scoped run.
