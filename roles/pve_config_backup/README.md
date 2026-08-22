# pve_config_backup

Daily tar of the local `/etc/pve` (pmxcfs) mount into the generic
`<pool>/databases` archive namespace (see the [`zfs_pools`](../zfs_pools/README.md)
role) — the same shape already proven by
[`sqlite_standby`](../sqlite_standby/README.md) and
[`postgres_standby`](../postgres_standby/README.md), applied to a new source.

## Why no cross-host pull

`/etc/pve` is `pmxcfs`, already replicated to every cluster member. Running
this role locally on any one member — by convention, the node that already
owns the `<pool>/databases` dataset — captures `cluster.conf`, `storage.cfg`,
firewall rules, HA rules, `replication.cfg` and ACLs for the **whole
cluster**, not just that node. A single-node loss does not lose this data;
the real exposure this role protects against is total-cluster loss, which is
what makes an independent, off-pmxcfs copy worth having at all.

## Installation

Ships in `ansible-proxmox`, applied via `playbooks/site.yml`. No separate
install. Inert (`pve_config_backup_enabled: false`) unless set per-host.

## How it works

Daily (`systemd` timer): `tar czf` the source directory into a timestamped
archive under the archive directory, then prune to the `N` most recent. The
archive directory sits inside the existing `<pool>/databases` dataset, so it
is already snapshotted (`sanoid`) and, once wired, cross-node replicated
(`syncoid`) by the storage layer the same as every other archive in that
namespace — this role only fills it.

## Variables

| Variable | Default | Description |
| --- | --- | --- |
| `pve_config_backup_enabled` | `false` | Master enable — set per-host |
| `pve_config_backup_source_dir` | `/etc/pve` | Directory tarred |
| `pve_config_backup_archive_dir` | `/bulk/databases/pve-etc` | Archive destination |
| `pve_config_backup_on_calendar` | `*-*-* 04:15:00` | `systemd` `OnCalendar` (daily) |
| `pve_config_backup_persistent` | `true` | Run a missed schedule on next boot |
| `pve_config_backup_retain_count` | `14` | Archives kept before pruning oldest |
| `pve_config_backup_healthcheck_url` | `""` | Optional healthchecks.io URL |

## Usage

```bash
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags pve_config_backup
```

## Restore

Extract the newest archive under the archive directory
(`tar xzf pve-etc-<timestamp>.tar.gz`) into a scratch location and diff
against a live `/etc/pve` read — never `pct`/`qm` config edits directly from
the tar. A real restore into a rebuilt cluster's `pmxcfs` is an operator
action outside this role's scope.

## What it captures, and why running it on one member is enough

The archive is a daily tar of the local pmxcfs mount (`/etc/pve`): cluster
configuration, storage definitions, firewall, HA and replication config, and
ACLs. It lands in the generic `<pool>/databases` archive namespace — the same
shape as `sqlite_standby` and `postgres_standby`, with a different source.

pmxcfs replicates cluster-wide, so the copy on any one member is the whole
cluster's configuration. Enabling this on a second node would duplicate the
same content rather than covering anything new, which is why it is inert unless
a host explicitly sets `pve_config_backup_enabled: true` — in practice the node
that already owns the `<pool>/databases` dataset.
