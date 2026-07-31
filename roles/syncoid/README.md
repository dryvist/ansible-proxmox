# syncoid

Cross-node ZFS replication with [syncoid](https://github.com/jimsalterjrs/sanoid)
— **layer 2** of the storage-resiliency model (survives losing a whole node or
pool). Pairs with the `sanoid` role: syncoid ships the snapshots sanoid takes.

## Installation

This role ships in the `ansible-proxmox` repository and is applied via
`playbooks/site.yml`. No separate installation is required beyond cloning the
repo and installing collection dependencies:

```bash
git clone https://github.com/dryvist/ansible-proxmox.git
cd ansible-proxmox
ansible-galaxy install -r requirements.yml
```

## Model

**Pull, from the target.** Run this role on the **backup** node (e.g. pve2); it
SSHes to each source (e.g. pve1) and pulls. Pull-from-backup is safer than push
— a compromised source cannot reach the backup. `--no-sync-snap` replicates the
snapshots `sanoid` already took rather than creating new ones.

A failed job (source offline — expected for the intermittent pve3) is logged to
`/var/log/syncoid/` and does **not** abort the remaining jobs — but it is
counted: any failed job makes the wrapper exit non-zero and ping
`syncoid_healthcheck_url/fail` (if set), so a bad run is never silently
exit-0.

## Prerequisite (apply-time)

SSH trust from this node's `syncoid_user` (default `root`) to each source host,
set up out of band. The role schedules replication; it does not distribute keys.

## Variables

| Variable | Default | Description |
| --- | --- | --- |
| `syncoid_enabled` | `true` | Master enable |
| `syncoid_jobs` | `[]` | List of `{ name, source, target, options?, schedule? }` — inert until set |
| `syncoid_default_options` | `--recursive --no-sync-snap --quiet` | Applied when a job omits `options` |
| `syncoid_cron_hour` / `syncoid_cron_minute` | `2` / `17` | Schedule for the `default` group |
| `syncoid_extra_schedules` | `{}` | Extra cadence groups (see below) |
| `syncoid_user` | `root` | User that runs syncoid (needs SSH to sources) |
| `syncoid_healthcheck_url` | `""` | healthchecks.io URL; pinged on success, `/fail` pinged if any job failed |

## Usage

```yaml
syncoid_jobs:
  - name: pve1-nas
    source: "root@pve1:rpool/data/nas"
    target: "tank/replica/pve1/nas"
```

### Schedule groups

One cadence per node stops working once a node pulls datasets with different
RPOs — a few GB of configuration wants hourly, a multi-hundred-GB namespace does
not, and without groups the only way to tighten one is to tighten both. Declare
extra groups and let a job opt in:

```yaml
syncoid_extra_schedules:
  hourly:
    hour: "*"
    minute: "37"

syncoid_jobs:
  - name: app-config
    schedule: hourly          # omit to stay in `default`
    source: "root@pve1:rpool/data/vm-200-disk-2"
    target: "bulk/replica/pve1/vm-200-disk-2"
```

The schedule renders as a whole `/etc/cron.d/syncoid` file rather than as
individual crontab entries, so a group that stops having jobs disappears instead
of leaving a line behind that nothing declares. Each group takes its own lock,
so two groups run concurrently but a group never overlaps itself.

Per-host identity (VMIDs, the source node) is derived at runtime from the S3
tofu inventory injected by `playbooks/load_tofu.yml` — `splunk_vm_from_tofu` and
`containers_from_tofu` (see `inventory/host_vars/pve{2,3}.yml`) — never
hard-coded, so a VMID renumber flows through with no edit.

```bash
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags syncoid
```
