# oci_app_upgrade

Replaces the image of OCI-image LXCs (tag `oci-app`) while keeping each CT's
CT-owned mpN volumes. Serial, one node at a time. Playbook:
`playbooks/oci_app_upgrade.yml`.

## Input

`oci_app_upgrades` has no default. Pass it as extra vars (for example
`-e @request.yml`). Each entry:

| Key | Meaning |
| --- | --- |
| `vmid` | The CT. It must exist exactly once cluster-wide as an LXC. |
| `image` | The OCI image reference, for the record. |
| `template` | The storage volid of the new OCI template, for example `local:vztmpl/<name>.tar.zst`. |
| `current_template` | The volid the CT runs now. A rescue rebuilds the CT from it. |
| `health_url` | The application health URL. It must return 200 within the window. |

An entry whose `template` equals `current_template` is reported and skipped.
The role does not pull templates; both must already be on their storages.

## Dry run

`oci_app_upgrade_dry_run` defaults to `true`. A dry run reads state only and
prints the planned actions per CT. Check mode behaves the same way. Applying
needs `-e oci_app_upgrade_dry_run=false` explicitly.

## Procedure per CT

1. Preflight, read-only. The CT is present on this node, unlocked, has no
   `unusedN` volume and no snapshot other than `current`. Every `mpN` is a
   storage volume flagged `backup=1`. The holder VMID is free cluster-wide. The
   PBS storage and both templates exist.
2. `vzdump` to the PBS storage in snapshot mode. This is the last-resort
   archive. The rescue never restores from it.
3. Remove the CT from HA (`ha-manager remove ct:<vmid>`). Delete its
   replication jobs (`pvesr delete <vmid>-<n>`).
4. `pct shutdown` with `--forceStop 0`. Record the `pct config` and its digest.
5. Create a stopped holder CT at `oci_app_upgrade_holder_vmid_base` plus the
   request index. Lift protection if set. Move every `mpN` to the holder with
   `pct move-volume`.
6. `pct destroy <vmid> --purge`. The CT owns no volume at this point.
7. `pct create` from the target template with the recorded keys in
   `oci_app_upgrade_create_keys` and every `netN`. Move each `mpN` back to the
   same slot. Destroy the holder once it owns no `mpN` or `unusedN` volume.
   Restore protection.
8. Start if the CT was running. Re-apply HA and replication from desired state
   with the `pve_ha` tasks (`tier0_resources`, `replication_jobs`,
   `replication_apply`).
9. Wait for `health_url` to return 200, 60 attempts ten seconds apart.

Every step reads the live state first and checks it. Each `move-volume` is
followed by an assertion that the moved volume keeps its mount options.

## Rescue

Any failure after step 2 posts to the ntfy `keystone` topic first, then recovers
from live state:

- If the CT was never destroyed, its volumes move back to it. The holder is
  removed once empty. Protection is restored, the CT is started if it was
  running, and HA and replication are re-applied.
- If the CT is missing or its destroy had started, it is rebuilt from
  `current_template` with the recorded configuration. The volumes move back and
  HA and replication are re-applied.

The run then stops at that CT. No volume is deleted by the rescue.

If the recovery itself fails, a second ntfy notice says so, and the run stops
for manual action. HA and replication may still be removed at that point.

## Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `oci_app_upgrade_dry_run` | `true` | Report only. |
| `oci_app_upgrade_holder_vmid_base` | `990000` | Holder VMID base. Refused if in use. |
| `oci_app_upgrade_backup_storage` | `guests` | PBS storage id for the archive. |
| `oci_app_upgrade_shutdown_timeout` | `120` | Seconds for a clean `pct shutdown`. |
| `oci_app_upgrade_health_retries` | `60` | Health attempts. |
| `oci_app_upgrade_health_delay` | `10` | Seconds between attempts. |
| `oci_app_upgrade_ntfy_url` | `ntfy.<PROXMOX_SUBDOMAIN>/keystone` | Failure notice target. |
| `oci_app_upgrade_create_keys` | see defaults | Recorded keys carried into `pct create`. |

## Assumptions

The procedure depends on `pct` and `pvesh` behaviour that the repository's
tests cannot exercise offline. These are listed in the change description and
need a live check before the first apply.
