# Proxmox Monitoring Role

Configures system monitoring tools for Proxmox VE crash investigation and
health monitoring.

## Installation

This role ships in the `ansible-proxmox` repository and is applied via
`playbooks/site.yml`. No separate installation is required beyond cloning the
repo and installing collection dependencies:

```bash
git clone https://github.com/dryvist/ansible-proxmox.git
cd ansible-proxmox
ansible-galaxy collection install -r requirements.yml
```

## Components

### sysstat (sar)

System performance data collection every 10 minutes.

- **Data location**: `/var/log/sysstat/`
- **View CPU**: `sar -u -f /var/log/sysstat/saDD`
- **View memory**: `sar -r -f /var/log/sysstat/saDD`

### atop

Detailed per-process resource accounting with historical data.

- **Data location**: `/var/log/atop/`
- **View historical**: `atop -r /var/log/atop/atop_YYYYMMDD`

### crash-monitor

Custom script logging memory, swap, top processes, and VM/CT counts every
minute.

- **Data location**: `/var/log/crash-monitor/`
- **Format**: Daily log files (YYYY-MM-DD.log)
- **Retention**: 90 days (configurable)

### healthchecks.io

External uptime monitoring ping (optional).

### zfs-capacity

Pushes an [ntfy](https://ntfy.sh) alert when a ZFS **pool** crosses a usage
band (default 50/75/85/90%) or a **quota'd dataset** crosses a dataset band
(default 85/90%, computed as `used/quota`). Quota-less datasets share their
pool's free space, so the pool bands already cover them — per-dataset bands
would only duplicate the pool alert. State is tracked per pool/dataset under
`/var/lib/zfs-capacity-monitor/`, so a notification fires only on a band
**change** (rising or recovering) — not every run. Priority scales with the
band (50 → default, 75/85 → high, 90 → urgent). Disabled until
`proxmox_monitoring_ntfy_url` is set.

### pvesr-telemetry

Emits `pvesr status` for every ZFS replication job as key=value lines to
syslog every 5 minutes. `pve_syslog_forwarder` already ships host syslog to
Cribl and on into Splunk, so no extra collection is needed.

**It does not alert.** It states facts only; Hermes evaluates them out of
Splunk. Alerting here would duplicate that and bypass the pipeline of record —
which is also why this is not modelled on the ntfy-based `zfs-capacity` check
above.

```text
host=pve2 job_id=602000-0 enabled=Yes target=local/pve3 state="OK" \
  fail_count=0 last_sync=2026-07-26_19:20:13 last_sync_epoch=1785093613 \
  age_seconds=286 duration_seconds=40.017384
```

A node with no jobs emits `job_count=0` explicitly, so "configured with zero
jobs" stays distinguishable from "never reported".

`age_seconds` and `last_sync_epoch` are `-1` when a job has **never completed a
sync** — the case worth catching, and one that would otherwise parse as `0` and
read as "just synced".

Suggested Hermes conditions:

| Condition | Meaning |
| --- | --- |
| `fail_count > 0` | job erroring |
| `age_seconds = -1` | **never synced** — the failure mode below |
| `age_seconds > 3 × schedule` | falling behind |
| host stops reporting | telemetry or node down |

**Why this exists.** A `pvesr` job that has never run still appears in
`pvesr list` looking healthy. On 2026-07-26 the `postgres-apps` job had been
failing silently — it targeted a node with no `bulk` pool, so it could never
have succeeded — while the guest showed as HA-protected with nothing to fail
over to. Job existence is not job health, and HA over a replica that does not
exist is worse than no HA, because it reads green.

## Variables

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `proxmox_monitoring_enable_sysstat` | `true` | Enable sysstat |
| `proxmox_monitoring_enable_atop` | `true` | Enable atop |
| `proxmox_monitoring_enable_crash_monitor` | `true` | Enable script |
| `proxmox_monitoring_enable_healthchecks` | `true` | Enable ping |
| `proxmox_monitoring_healthchecks_ping_url` | `""` | Ping URL (secret) |
| `proxmox_monitoring_crash_monitor_interval` | `1` | Crash monitor cron interval (minutes) |
| `proxmox_monitoring_healthchecks_interval` | `1` | Healthchecks.io ping interval (minutes) |
| `proxmox_monitoring_log_retention_days` | `90` | Days to retain |
| `proxmox_monitoring_enable_zfs_capacity` | `true` | Enable ZFS capacity alerts |
| `proxmox_monitoring_ntfy_url` | `""` | ntfy topic URL (secret); empty disables |
| `proxmox_monitoring_zfs_capacity_interval` | `15` | Capacity check cron interval (minutes) |
| `proxmox_monitoring_zfs_capacity_thresholds` | `[50, 75, 85, 90]` | Pool usage bands (%) that trigger alerts |
| `proxmox_monitoring_zfs_dataset_capacity_thresholds` | `[85, 90]` | Quota'd-dataset usage bands (%; `used/quota`) |

## Usage

```yaml
- hosts: proxmox
  roles:
    - role: proxmox_monitoring
      vars:
        proxmox_monitoring_healthchecks_ping_url: "{{ vault_url }}"
```

## Post-Crash Investigation

After a crash/reboot, check these in order:

```bash
# 1. Check crash-monitor logs (1-minute granularity)
# Note: Replace YYYY-MM-DD with the date of the crash.
less /var/log/crash-monitor/YYYY-MM-DD.log

# 2. Check previous boot journal (if available)
journalctl -b -1 | tail -100

# 3. Check for hardware errors
ras-mc-ctl --errors

# 4. Check atop historical data
# Note: Replace YYYYMMDD with the date of the crash.
atop -r /var/log/atop/atop_YYYYMMDD

# 5. Check sar data
# Note: Replace DD with the day of the month for the crash.
sar -r -f /var/log/sysstat/saDD
```
