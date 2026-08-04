# Database DR Standard

Postgres and SQLite backup/restore mechanics — the concrete "how" for the
database stores that [`DATA_PROTECTION_STANDARD.md`](DATA_PROTECTION_STANDARD.md)
classifies as **P0**. That document is the governing standard: it sets the
RPO/RTO/recovery-window targets and the telemetry contract. This document is
the workflow that meets them, and it applies to every database in the
homelab, Postgres, SQLite, or any engine added later — new databases conform
to it; they do not invent their own backup scheme.

Every dump is an **app-consistent logical backup** (`pg_dump`, SQLite online
backup), not a block snapshot — portable, and restorable into a freshly
rebuilt guest, matching the ChaosMonkey "rebuild from source, restore data"
model. Everything below runs via Ansible/IaC; there are no hand-run dumps or
restores on a live guest.

## Topology (why the archive lives where it does)

- The **live** database guest runs on the primary compute node (`fast` pool). Its
  own volume is not snapshotted/replicated.
- The **always-on standby node** owns `bulk/databases` (recursive `sanoid` `database`
  template) — the warm-standby home for all DB archives.
- The **offline-DR node** pulls the whole `bulk/databases` namespace during its
  power-on windows (`syncoid`, recursive), giving an independent second copy.

So a dump must reach `bulk/databases/<instance>` on the standby node. It gets there
by a **pull on the standby node** (the `*_standby` pattern), never by writing to the
live guest's own unreplicated volume.

For a database with multiple guest instances spread across nodes (e.g. a
primary and a hot standby that each dump themselves locally), "the standby
node" is not necessarily one fixed host: the pull for a given instance must
land on a node that is not the one that instance runs on, or it is not an
off-node copy at all. Where two such nodes each hold one instance, they pull
for each other (`host_vars/<node>.yml` on each names the other's instance as
its `*_standby_jobs` source) rather than each pulling its own co-located one.

## The workflow (per database)

### 1. Produce a consistent dump on the source (the DB role)

The engine's role runs a scheduled, app-consistent dump locally on the DB guest:

- **Postgres** (`ansible-proxmox-apps` `roles/postgres`): a `pg-backup` systemd timer
  runs `pg_dump --format=custom` per managed database, with retention pruning.
- **SQLite**: a consistent online backup (`.backup`) of the live file.

### 2. Pull the dump into the replicated archive (the `*_standby` role, on the standby node)

A standby role on the always-on node pulls the latest dump over SSH into
`bulk/databases/<instance>/`, where sanoid + syncoid take over:

- **SQLite** — `roles/sqlite_standby` (append-only row archive; existing).
- **Postgres** — `roles/postgres_standby` (rsync the newest `*.dump` into
  `bulk/databases/postgres/`; retain history via sanoid snapshots). Same job shape
  as `sqlite_standby`: `source_host`, `source_path`, `archive_path`, timer,
  `*_healthcheck_url`, `*_run_now`.

Prerequisite (out of band, Ansible-managed): SSH trust from the standby node's root
to the source DB guest (`cluster_ssh_trust` covers node↔node, not node→guest — add
the standby node's key to the guest's `authorized_keys`).

### 3. Ship the latest dump off-site (Tier 2, shared upload)

A shared upload step pushes the newest archive dump to cloud/off-box object storage
(RustFS `s3` and/or AWS S3), credentials from OpenBao/SOPS (`no_log`). One reusable
mechanism invoked by each engine's standby role — not reinvented per database.

### 4. Restore (the DB role, `dr_restore` tag)

Rebuild the guest + cluster via the (idempotent) role, then restore from the latest
archive (Tier-1) or cloud (Tier-2):

- **Postgres**: `pg_restore --clean --if-exists --dbname=<db> <latest>.dump`.
- **SQLite**: copy/`.restore` the archive into place.

Each pull and upload step reports its result per the telemetry contract in
`DATA_PROTECTION_STANDARD.md` — `age_seconds=-1` for never-run, a `job_count=0`
line for a host with nothing to do, and a non-empty `reason=` on any `skip`.

## Adding a new database

1. Add the DB to its engine role's managed list so it gets a scheduled consistent dump.
2. Add a `*_standby` job pulling its dump into `bulk/databases/<instance>/` on the
   standby node (reuse `sqlite_standby`/`postgres_standby`; add a new engine role only
   for a genuinely new engine, following the same shape).
3. Confirm `bulk/databases` recursion already covers `<instance>` (it does — the
   sanoid dataset and the pve→DR syncoid job are recursive); no per-DB sanoid/syncoid
   edit is needed.
4. Wire the Tier-2 upload for the new archive.
5. Add a restore entry + run the restore drill (below).
6. Add the job to `data_protection_expected.csv` per
   `DATA_PROTECTION_STANDARD.md` — a job that never reports is a missing row.

## Restore drill (the DR gate — mandatory)

DR is only "done" once demonstrated:

1. Trigger a backup + the standby pull (`*_run_now: true` or the timer).
2. Confirm the dump exists in `bulk/databases/<instance>/` on the standby node AND in
   the cloud target.
3. Restore the latest dump into a **scratch** database.
4. Compare row counts (and a checksum of key tables) between source and restored —
   the diff must be `0`.
5. Record the drill result. Re-run after any change to the backup or restore path.

## Related

- [`DATA_PROTECTION_STANDARD.md`](DATA_PROTECTION_STANDARD.md) — the governing
  standard: protection classes, RPO/RTO/recovery-window targets, the
  telemetry contract, and the checklist for adding any new data store.
- `roles/sanoid`, `roles/syncoid` — the snapshot + cross-node replication layer.
- `roles/sqlite_standby`, `roles/postgres_standby` — the per-engine pull consumers.
- `docs/DR_RUNBOOK.md` — node/guest rebuild procedures (this doc is the DB-data half).
