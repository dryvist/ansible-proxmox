# zfs_replication

Opt-in, **reachability-gated** ZFS replication to an **intermittently-online
standby node**, plus an optional `vzdump` guest-backup leg. Groundwork for the
homelab resiliency program's warm/hot-standby host (see
[`docs/DR_RUNBOOK.md`](../../docs/DR_RUNBOOK.md)).

## Installation

This role ships in the `ansible-proxmox` repository and is applied via
`playbooks/site.yml`. No separate installation is required beyond cloning the
repo and installing collection dependencies:

```bash
git clone https://github.com/dryvist/ansible-proxmox.git
cd ansible-proxmox
ansible-galaxy install -r requirements.yml
```

> Note: this role is **not yet referenced** in `playbooks/site.yml` — wiring it
> in is a deliberate follow-up (see below).

## Relationship to the `sanoid` / `syncoid` roles (read first)

This repo already ships `sanoid` (snapshot retention, layer 1) and `syncoid`
(cron-driven PULL replication, layer 2). This role is **additive groundwork, not
a drop-in replacement**, and is **not yet wired into `playbooks/site.yml`**. It
adds two things the existing roles do not:

1. A **systemd-timer** schedule with an **explicit pre-flight reachability gate**
   — a replication run against a powered-off standby is decided to be a clean
   SKIP *before* `syncoid` is invoked, rather than relying on `syncoid` itself
   failing-and-logging once the SSH connection times out.
2. An optional **`vzdump`** backup leg.

A maintainer should decide whether to **adopt this role** or **fold its additive
pieces into the existing `syncoid` role**. Until that decision is made and the
role is wired into `site.yml`, it is inert by default and changes nothing.

## Model

**PUSH from the source toward an intermittent standby** (e.g. `proxmox-3`). The
standby is up or down at any time, independent of any failover. Whenever it is
reachable, the configured datasets are replicated so the standby's copies are
near-current the moment it boots. When it is down, every job is a clean skip —
never a failure. `syncoid` (from the `sanoid` apt package) is used because it
tolerates an offline target far more gracefully than Proxmox-native `pvesr`,
which requires the target to be up.

> The existing `syncoid` role uses a PULL model (run on the target, pull from
> sources). This role uses PUSH (run on the source, gated on the target being
> reachable) because the *source* is the always-on node here and the *target* is
> the intermittent one — so the gate has to be evaluated by the always-on side.
> This divergence is one of the things a maintainer should reconcile.

## Inert by default

`zfs_replication_jobs` is `[]` and `zfs_replication_target_host` is empty, so the
role is a no-op until configured in `inventory/host_vars`. The systemd timer is
only enabled when both a target host and at least one job are set; remove them
and the role disables the timer again.

## Variables

| Variable | Default | Description |
| --- | --- | --- |
| `zfs_replication_enabled` | `true` | Master enable for the role |
| `zfs_replication_target_host` | `""` | Standby host to replicate toward. Set in host_vars; never hard-code a real node name |
| `zfs_replication_jobs` | `[]` | List of replication jobs — **inert until set** |
| `zfs_replication_reachability_probe` | `true` | Probe the target before replicating; skip cleanly if down |
| `zfs_replication_probe_method` | `ssh` | `ssh` (TCP connect) or `ping` (ICMP) |
| `zfs_replication_probe_port` / `zfs_replication_probe_timeout` | `22` / `10` | Probe port and per-probe timeout (s) |
| `zfs_replication_default_options` | `--recursive --no-sync-snap --quiet` | syncoid options when a job omits its own |
| `zfs_replication_timer_enabled` | `true` | Enable/start the systemd timer |
| `zfs_replication_on_calendar` | `*:0/15` | Replication cadence (every 15 min) |
| `zfs_replication_randomized_delay_sec` | `120` | Timer jitter so sources don't all hit the standby at once |
| `zfs_replication_timer_persistent` | `false` | Do NOT catch up a missed trigger on boot |
| `zfs_replication_vzdump_enabled` | `false` | Enable the optional vzdump backup leg |
| `zfs_replication_vzdump_storage` | `<backup-storage-id>` | Proxmox storage id vzdump writes to |
| `zfs_replication_vzdump_guests` | `[]` | vmids to back up — inert until set |
| `zfs_replication_vzdump_on_calendar` | `*-*-* 01:30:00` | vzdump cadence |

Each job in `zfs_replication_jobs`:

| Key | Required | Description |
| --- | --- | --- |
| `name` | yes | Human label, used in logs |
| `source_dataset` | yes | Local source dataset (e.g. `bulk/data`) |
| `target_dataset` | yes | Destination on the standby (e.g. `bulk/replica/proxmox-2/data`) |
| `recursive` | no (`true`) | Replicate children |
| `sync_snaps` | no (`false`) | Let syncoid make its own snapshots instead of shipping sanoid's |
| `options` | no | Explicit syncoid option string; overrides `recursive`/`sync_snaps` |

## Prerequisites (apply-time)

- Root SSH trust from this (source) node to the standby — set up out of band
  (the `cluster_ssh_trust` role / PVE cluster keys).
- The destination parent datasets (`bulk/replica/<node>`) exist on the standby —
  declared in tofu-proxmox `node_storage` and created by the `zfs_pools`
  role; `syncoid` creates the per-dataset leaves.
- A sanoid snapshot exists on each source (for `--no-sync-snap`).

## Usage

```yaml
# inventory/host_vars/<always-on source node>.yml
zfs_replication_target_host: "<target-node>"   # e.g. proxmox-3
zfs_replication_jobs:
  - name: media-data
    source_dataset: "bulk/data"
    target_dataset: "bulk/replica/proxmox-2/data"
    recursive: true
```

```bash
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags zfs_replication
```

Package install, the systemd daemon-reload, and timer enablement are skipped
under Docker so molecule can converge the contract in-container.
