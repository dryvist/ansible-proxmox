# zfs_pools

Manages ZFS **datasets, quotas, and Proxmox storage registration** for the
per-node pools declared in `tofu-proxmox`'s `node_storage` output.

## Installation

This role ships in the `ansible-proxmox` repository and is applied via
`playbooks/site.yml`. No separate installation is required beyond cloning the
repo and installing collection dependencies:

```bash
git clone https://github.com/dryvist/ansible-proxmox.git
cd ansible-proxmox
ansible-galaxy collection install -r requirements.yml
```

## Scope (and what it deliberately does NOT do)

`tofu-proxmox` declares storage; `ansible-proxmox` realizes it. The
Proxmox API cannot create ZFS pools (`zpool create` is an OS operation), so the
contract is split:

| Layer                                      | Owns                                             |
| ------------------------------------------ | ------------------------------------------------ |
| Host commissioning (auto-install / manual) | `zpool create` from physical devices             |
| **this role**                              | datasets, quotas, `pvesm` storage registration   |
| tofu-proxmox                               | references the datastore by `id` on VM/LXC disks |

**Pool creation is opt-in and off by default.** Creating a pool needs the
host-specific device list (`by-id` paths), which is not in the committed
contract, and getting it wrong destroys data. By default the role asserts a
`register=true` pool already exists and manages datasets within it. To allow
creation, set in untracked `host_vars`:

```yaml
zfs_pools_allow_create: true
zfs_pools_devices:
  tank: ["/dev/disk/by-id/...", "/dev/disk/by-id/...", "/dev/disk/by-id/..."]
```

## Inputs

`playbooks/load_tofu.yml` injects `zfs_pools_from_tofu` onto each
proxmox host: the `node_storage[<node>]` entry for that host, keyed by the
host's `proxmox_node_name` (defaults to the inventory hostname). Set
`proxmox_node_name` in `host_vars` when the inventory name differs from the
tofu node name (e.g. inventory `node-a` → tofu `pve2`).

Shape (`zfs_pools_map`):

```yaml
zfs_pools_map:
  tank:
    type: zfspool
    raid: raidz1 # informational
    protected: true # storage-safety (hold/readonly enforcement: design pending)
    register: true # run `pvesm add zfspool` if not already registered
    content: [images, rootdir]
    datasets:
      backups:
        quota: "1T"
        properties:                 # optional; any zfs property=value
          recordsize: "1M"
          compression: "zstd"
          "com.sun:auto-snapshot": "false"
```

### Per-dataset properties

`datasets.<name>.properties` is an optional map of arbitrary ZFS properties
(`recordsize`, `compression`, `readonly`, `atime`, `com.sun:auto-snapshot`,
user properties, …). Each is read with `zfs get -H -o value` and only set when
it differs, so re-runs report no change. Declare values in **ZFS canonical
form** (`recordsize: "1M"`, `compression: "zstd"`, `readonly: "on"`) and
**quote** them so YAML does not coerce `on`/`off`/`true`/`false` to booleans.
`quota` keeps its own dedicated (byte-compared) handling — do not also put it
under `properties`.

### Per-dataset NFS export

`datasets.<name>.nfs_export` (optional) is the exact ZFS `sharenfs` value, set
verbatim and compared with `zfs get -H -o value sharenfs`. Use it to expose a
dataset over NFS — typically **read-only and LAN-scoped** for query access:

```yaml
datasets:
  databases:
    nfs_export: "ro=@10.0.0.0/8 ro=@192.168.0.0/16"  # space-separated clients
```

Children **inherit** a parent's `sharenfs`, so exporting a namespace parent
(e.g. `bulk/databases`) makes every dataset beneath it queryable read-only
without per-child config; a child can opt out with `sharenfs: "off"` under
`properties`. When any dataset declares `nfs_export`, the role ensures
`nfs-kernel-server` is installed and running. Leave it `null` (the default) for
no export.

### Per-dataset Proxmox storage registration (`pvesm_id`)

`datasets.<name>.pvesm_id` (optional) registers **the dataset itself** as its
own distinct Proxmox `zfspool` storage ID, so a VM/LXC disk can target the
dataset directly via `datastore_id`:

```yaml
datasets:
  fast-splunk:
    quota: "500G"
    pvesm_id: fast-splunk  # register this dataset as its own zfspool storage
```

**Why a quota is not enough.** A `zfspool`-backed VM disk lands at the pool
**root** by default (a sibling of any child dataset), so a plain `quota` on a
child dataset does *not* confine a disk to it. Registering the dataset itself
(`pvesm add zfspool <pvesm_id> -pool <pool>/<dataset>`) is what makes it a real,
isolated storage target — the disk lives inside the dataset and is capped by its
quota. This is the mechanism behind the `fast-splunk` and `bulk-splunk` tiers,
which give Splunk a volume-level cap so indexed data can no longer fill a pool.

Registration is gated with `pvesm status --storage <pvesm_id>` and only added
when absent, so re-runs report no change. It is registered with `-content
{{ content | default(['images', 'rootdir']) }}` (both VM and LXC disks by
default; override per-dataset with `content`) on the current node
(`proxmox_node_name`, defaulting to the inventory hostname). Leave `pvesm_id`
unset (the default) to skip registration.

Unlike pool creation, this capability is **not** gated by
`zfs_pools_allow_create` — it is non-destructive against an already-existing
pool. Creating a *new* pool for a new tier (e.g. `bulk-splunk` on a fresh pool)
still requires the existing `zfs_pools_allow_create: true` + `zfs_pools_devices`
opt-in in untracked `host_vars`; only the dataset registration itself runs
unconditionally on a present pool.

## Database storage namespace (engine- and tier-agnostic)

A reserved `<pool>/databases/<instance>` namespace standardizes where database
data lives, independent of engine (SQLite, PostgreSQL, MySQL, …) or role
(hot/primary, warm/standby, backup/archive). The parent `databases` dataset on
a pool is a lightweight container; each database is its **own child dataset** so
it carries engine-appropriate tuning, its own quota, snapshot policy, and
(optionally) replication.

**Tier → pool.** Pick the pool by latency need, not engine:

| Role | Pool | Why |
| --- | --- | --- |
| hot / primary | `fast` (NVMe) | low-latency random I/O |
| warm / standby / backup / archive | `bulk` (non-fast) | capacity over latency |

**Engine → `recordsize`.** Match ZFS `recordsize` to the engine's page/IO unit:

| Engine | `recordsize` | Notes |
| --- | --- | --- |
| PostgreSQL | `8K`–`16K` | 8K page; consider a separate WAL dataset, `logbias=throughput` |
| MySQL / MariaDB (InnoDB) | `16K` | 16K page |
| SQLite | `32K`–`64K` | balances query reads vs. append writes |

Always pair with `compression: "zstd"` and `atime: "off"`. The namespace parent
defaults to a neutral `recordsize: "16K"`; per-instance children override.

**Role → snapshots / replication / export.**

- **primary/hot** → `critical` sanoid template (hourly + long retention); export
  off.
- **warm/standby/backup** → `database` sanoid template (daily, long retention),
  `syncoid` DR replication, and `nfs_export` read-only so the standby is
  queryable from another machine.

The parent is snapshotted/replicated **recursively**, so adding a child instance
inherits snapshots, the DR copy, and (on `bulk`) the read-only export with no
extra wiring. Engine-specific *sync* mechanisms (e.g. the `sqlite_standby` role,
`pg_basebackup`, `mysqldump`) are separate consumers of this namespace.

## Usage

```bash
# Dry run — storage tasks only
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags zfs_pools --check
# Apply
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags zfs_pools
```

## Idempotency

- Pools: checked with `zpool list`; only created when explicitly allowed.
- Datasets: checked with `zfs list`; created with `zfs create -p` when absent.
- Quotas: compared in **bytes** (`zfs get -Hp` vs `human_to_bytes(desired)`), so
  `1T` and `1024G` do not cause spurious changes.
- Properties: each `properties` entry compared as a string (`zfs get -H -o
  value`) and only `zfs set` when it differs.
- Registration: `pvesm status --storage <pool>` gates `pvesm add`; the same
  check gates per-dataset `pvesm_id` registration.

All ZFS / `pvesm` tasks are skipped under Docker (`ansible_virtualization_type
== 'docker'`) for molecule testing.
