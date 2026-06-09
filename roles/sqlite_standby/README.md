# sqlite_standby

Daily, **insert-only** SQLite **warm standby**. For each configured job this role
pulls a consistent online backup of a source SQLite database and appends only
**new** rows into a local archive database — it **never deletes**, so the live
source can enforce a short retention (prune old rows) while the archive keeps
the full history and stays directly queryable.

It is one **consumer** of the engine-agnostic `<pool>/databases` storage
namespace (see the [`zfs_pools`](../zfs_pools/README.md) role). The storage layer
owns tiering, snapshots, read-only NFS export, and cross-node replication; this
role only fills an archive that lives there.

## Installation

Ships in `ansible-proxmox`, applied via `playbooks/site.yml`. No separate install.

## How it works

Per job, daily (`systemd` timer):

1. **Consistent copy** — `sqlite3 '<src>' ".backup '<tmp>'"` on the source over
   SSH (safe for a live WAL database), pulled back with binary `rsync`.
2. **Seed (first run)** — the consistent copy *becomes* the archive verbatim, so
   the full schema and **primary keys** are preserved (required for dedupe).
3. **Insert-only append (subsequent runs)** — per configured table:

   ```sql
   INSERT OR IGNORE INTO main.[t]
   SELECT * FROM src.[t] WHERE [key] > (SELECT MAX([key]) FROM main.[t]);
   ```

   Only rows past the archive's current high-water mark are added; `OR IGNORE`
   keeps the first-seen row on a primary-key collision. Nothing is ever deleted.

The archive is kept in `journal_mode=DELETE` so a **read-only NFS consumer** sees
a self-consistent file. For a guaranteed point-in-time view while a sync may be
running, query the latest ZFS snapshot under `<dataset>/.zfs/snapshot/`.

A failed job is logged to `/var/log/sqlite-standby/` and does **not** abort the
others; a failure pings `<healthcheck>/fail`.

## Prerequisites (apply-time, out of band)

- SSH trust from this host's `root` to each `source_host`. `cluster_ssh_trust`
  covers PVE node↔node; a database guest is **not** a PVE node, so add that
  trust separately.
- `sqlite3` present on each source host, with transient free space (~the DB
  size) for the online backup.
- The target dataset (e.g. `bulk/databases`) created by `zfs_pools` from the
  `terraform-proxmox` declaration.

## Variables

| Variable | Default | Description |
| --- | --- | --- |
| `sqlite_standby_enabled` | `true` | Master enable |
| `sqlite_standby_jobs` | `[]` | Jobs (see below) — inert until set |
| `sqlite_standby_on_calendar` | `*-*-* 03:30:00` | `systemd` `OnCalendar` (daily) |
| `sqlite_standby_persistent` | `true` | Run a missed schedule on next boot |
| `sqlite_standby_healthcheck_url` | `""` | healthchecks.io URL (`/fail` on error) |
| `sqlite_standby_run_now` | `false` | Opt-in: run immediately during the play |
| `sqlite_standby_staging_dir` | `/var/lib/sqlite-standby` | Pulled-copy staging |

### Job shape

```yaml
sqlite_standby_jobs:
  - name: "events-archive"
    source_host: "root@10.0.x.y"
    source_path: "/var/lib/app/live.db"
    archive_path: "/bulk/databases/events/archive.db"
    tables:
      - { name: "events", key: "id" }      # key MUST be monotonic per table
      - { name: "samples", key: "ts" }
```

## Best-effort caveats

- **Each table needs a monotonic key** (`INTEGER PRIMARY KEY`, autoincrement id,
  or a never-decreasing timestamp). Tables without one cannot be appended safely
  and should be omitted (or reseeded).
- **Insert-only**: an UPDATE to an existing row keeps the first-seen version;
  intermediate edits are not retained. (To retain full change history, model it
  as append-only rows on the source.)
- **Daily lag** by design — a queryable daily archive, not a near-real-time
  replica.
- **Full copy each run** — the current implementation transfers a full
  consistent copy per run and needs transient free space on the source; a
  delta-only optimization is a tracked follow-up.

## Usage

```bash
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags sqlite_standby
# Seed/refresh now (e.g. first run) without waiting for the timer:
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags sqlite_standby -e sqlite_standby_run_now=true
```
