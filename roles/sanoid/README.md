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
ansible-galaxy collection install -r requirements.yml
```

## Scope

- Installs the `sanoid` package, renders `/etc/sanoid/sanoid.conf`, and enables
  `sanoid.timer`.
- Snapshots only the datasets you assign in `sanoid_datasets`; templates alone
  take nothing. The role is inert until datasets are assigned.
- Package install + timer are skipped under Docker so molecule can converge.

## Variables

| Variable | Default | Description |
| --- | --- | --- |
| `sanoid_enabled` | `true` | Master enable for the role |
| `sanoid_timer_enabled` | `true` | Enable/start `sanoid.timer` |
| `sanoid_templates` | critical / media / scratch | Retention templates by criticality tier |
| `sanoid_datasets` | `{}` | Map of `dataset => { use_template, recursive, … }` |

Quote `yes`/`no` values — sanoid wants literal `yes`/`no`, and unquoted YAML
coerces them to booleans.

## Usage

```yaml
sanoid_datasets:
  "rpool/data/nas": { use_template: critical, recursive: "yes" }
  "nvme1/siem/splunk-hot": { use_template: critical }
  "nvme1/siem/cribl-pq": { use_template: scratch }   # transient, no snapshots
```

```bash
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags sanoid
sanoid --monitor-snapshots   # health check after a few cycles
```
