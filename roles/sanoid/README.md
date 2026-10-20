# sanoid

Schedules and prunes ZFS snapshots with [sanoid](https://github.com/jimsalterjrs/sanoid)
— local point-in-time protection (accidental delete / corruption rollback). It
is **layer 1** of the storage-resiliency model; cross-node replication
(syncoid) and guest backups (PBS) are separate roles.

## Installation

This role ships in the `ansible-proxmox` repository and is applied via
`playbooks/site.yml`. No separate installation is required beyond cloning the
repo and installing collection dependencies:

```bash
git clone https://github.com/dryvist/ansible-proxmox.git
cd ansible-proxmox
ansible-galaxy install -r requirements.yml
```

## Scope

- Installs the `sanoid` package, renders `/etc/sanoid/sanoid.conf`, and enables
  `sanoid.timer`.
- Configures only datasets assigned in `sanoid_datasets` or live `syncoid_jobs`
  targets when replica retention is enabled; templates alone take no snapshots.
- Guest disk datasets named `vm-<vmid>-disk-<index>` or
  `subvol-<vmid>-disk-<index>` under `rpool/data` use `rpool_guest`; other
  datasets retain their configured template.
- Package install + timer are skipped under Docker so molecule can converge.

## Variables

| Variable                           | Default                    | Description                                        |
| ---------------------------------- | -------------------------- | -------------------------------------------------- |
| `sanoid_enabled`                   | `true`                     | Master enable for the role                         |
| `sanoid_timer_enabled`             | `true`                     | Enable/start `sanoid.timer`                        |
| `sanoid_templates`                 | critical / media / scratch | Retention templates by criticality tier            |
| `sanoid_rpool_guest_dataset_pattern` | `^rpool/data/(vm\|subvol)-[0-9]+-disk-[0-9]+$` | Guest dataset names receiving the shorter template |
| `sanoid_rpool_guest_template_name` | `rpool_guest`              | Template assigned to matching guest datasets       |
| `sanoid_datasets`                  | `{}`                       | Map of `dataset => { use_template, recursive, … }` |
| `sanoid_replica_retention_enabled` | `false`                    | Add retention stanzas for live syncoid targets     |

Quote `yes`/`no` values — sanoid wants literal `yes`/`no`, and unquoted YAML
coerces them to booleans.

The `rpool_guest` template keeps 6 hourly, 7 daily, and 4 weekly snapshots,
with monthly and yearly retention disabled. The existing `critical` template
remains at 36 hourly, 30 daily, 8 weekly, and 6 monthly snapshots, so bulk
datasets assigned to `critical` are unchanged.

With `sanoid_replica_retention_enabled`, the role derives stanzas only for
`syncoid_jobs` targets (all datasets under a recursive target included) and
retains the newest hourly snapshot, 14 daily and 6 monthly snapshots; sanoid
prunes `autosnap_*` names only. The newest hourly is the newest replicated
instant, so a common snapshot normally survives each run. If replication
stops for longer than the retention windows of source and target overlap, no
common snapshot remains on both sides and incremental replication cannot
resume from a shared snapshot.

## Usage

```yaml
sanoid_datasets:
  "rpool/data/nas": { use_template: critical, recursive: "yes" }
  "nvme1/siem/splunk-hot": { use_template: critical }
  "nvme1/siem/cribl-pq": { use_template: scratch } # transient, no snapshots
```

Where a dataset name embeds a guest VMID, derive it at runtime from the S3 tofu
inventory injected by `playbooks/load_tofu.yml` — `splunk_vm_from_tofu` and
`containers_from_tofu` (see the per-node files in `inventory/host_vars/`) — rather than
hard-coding it, so a VMID renumber flows through with no edit.

```bash
./scripts/run-ansible.sh playbooks/site.yml --tags sanoid
sanoid --monitor-snapshots   # health check after a few cycles
```
