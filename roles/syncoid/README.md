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
ansible-galaxy collection install -r requirements.yml
```

## Model

**Pull, from the target.** Run this role on the **backup** node (e.g. pve2); it
SSHes to each source (e.g. pve1) and pulls. Pull-from-backup is safer than push
— a compromised source cannot reach the backup. `--no-sync-snap` replicates the
snapshots `sanoid` already took rather than creating new ones.

A failed job (source offline — expected for the intermittent pve3) is logged to
`/var/log/syncoid/` and does **not** abort the remaining jobs.

## Prerequisite (apply-time)

SSH trust from this node's `syncoid_user` (default `root`) to each source host,
set up out of band. The role schedules replication; it does not distribute keys.

## Variables

| Variable | Default | Description |
| --- | --- | --- |
| `syncoid_enabled` | `true` | Master enable |
| `syncoid_jobs` | `[]` | List of `{ name, source, target, options? }` — inert until set |
| `syncoid_default_options` | `--recursive --no-sync-snap --quiet` | Applied when a job omits `options` |
| `syncoid_cron_hour` / `syncoid_cron_minute` | `2` / `17` | Replication schedule |
| `syncoid_user` | `root` | User that runs syncoid (needs SSH to sources) |

## Usage

```yaml
syncoid_jobs:
  - name: pve1-nas
    source: "root@pve1:rpool/data/nas"
    target: "tank/replica/pve1/nas"
```

Per-host identity (VMIDs, the source node) is derived at runtime from the S3
tofu inventory injected by `playbooks/load_tofu.yml` — `splunk_vm_from_tofu` and
`containers_from_tofu` (see `inventory/host_vars/pve{2,3}.yml`) — never
hard-coded, so a VMID renumber flows through with no edit.

```bash
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags syncoid
```
