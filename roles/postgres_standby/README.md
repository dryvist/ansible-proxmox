# postgres_standby

Daily pull of **Postgres logical dumps** into the replicated database archive
namespace, plus the optional **Tier-2 cloud upload** — the Postgres consumer of
[`docs/DATABASE_DR_STANDARD.md`](../../docs/DATABASE_DR_STANDARD.md).

The source guest's `postgres` role (in `ansible-proxmox-apps`) already produces
app-consistent `pg_dump --format=custom` artifacts on a timer. This role, on the
always-on standby node, mirrors that backup directory into
`<pool>/databases/<instance>/`, where the storage layer (see
[`zfs_pools`](../zfs_pools/README.md), `sanoid`, `syncoid`) owns snapshots and
cross-node DR replication. It then uploads the newest dump per database to each
configured S3-compatible target (on-prem RustFS and/or AWS S3).

## Installation

Ships in `ansible-proxmox`, applied via `playbooks/site.yml`. No separate install.

## How it works

Per job, daily (`systemd` timer, after the source's own backup window):

1. **Mirror** — `rsync -a --delete` of `*.dump` from the source guest's backup
   directory into the archive dataset. The mirror tracks the **source's**
   retention window; pre-prune history is preserved by sanoid snapshots of the
   archive dataset (read a point-in-time view from `<dataset>/.zfs/snapshot/`).
2. **Tier-2 upload** — the newest dump per database (`<db>-<utc-stamp>.dump`)
   is `aws s3 cp`'d to every configured target. Credentials live in a
   root-only `EnvironmentFile` rendered with `no_log` — never in the script.

A failed job or upload is logged to `/var/log/postgres-standby/` and does
**not** abort the others; any failure pings `<healthcheck>/fail`.

## Prerequisites (apply-time, out of band)

- The public half of this host's pull key authorised on each `source_host` —
  see [SSH trust](#ssh-trust) below.
- The target dataset (e.g. `bulk/databases`) created by `zfs_pools` from the
  `tofu-proxmox` declaration; `bulk/databases` recursion covers the
  per-instance child automatically.
- For Tier-2: the bucket exists and the supplied keys can write it.

## SSH trust

The pull is an unattended 04:00 timer, so it needs a credential already on
disk. This role generates a **dedicated ed25519 keypair** (default
`/root/.ssh/id_postgres_standby`, generate-if-absent, never rotated in place)
and the sync script uses it with `IdentitiesOnly=yes` so nothing else is
offered.

A certificate from the SSH CA is not usable here: certificates are minted at
use time, and a timer has no way to mint one. A dedicated key scoped to a
single read-only directory is the narrower credential for this job.

The guest side (`postgres` role, `ansible-proxmox-apps`) authorises the public
half under a forced command, so the key cannot open a shell or write:

```text
restrict,command="rrsync -ro /var/lib/postgresql/backups" ssh-ed25519 AAAA... postgres-standby-pull
```

`rrsync` ships with the `rsync` package. Prefer it over pinning an exact
`rsync --server --sender` argv, which breaks silently when flags change.

The converge prints the public key to copy; take it from there rather than
transcribing it.

## Variables

| Variable | Default | Description |
| --- | --- | --- |
| `postgres_standby_enabled` | `true` | Master enable |
| `postgres_standby_jobs` | `[]` | Jobs (see below) — inert until set |
| `postgres_standby_s3_targets` | `[]` | Tier-2 targets (see below) |
| `postgres_standby_on_calendar` | `*-*-* 04:00:00` | `systemd` `OnCalendar` (daily) |
| `postgres_standby_persistent` | `true` | Run a missed schedule on next boot |
| `postgres_standby_healthcheck_url` | `""` | healthchecks.io URL (`/fail` on error) |
| `postgres_standby_run_now` | `false` | Opt-in: run immediately during the play |
| `postgres_standby_ssh_key` | `/root/.ssh/id_postgres_standby` | Dedicated pull identity (see [SSH trust](#ssh-trust)) |

### Job shape

```yaml
postgres_standby_jobs:
  - name: "postgres"
    source_host: "root@<db-guest-fqdn>"
    source_dir: "/"                          # see below
    archive_dir: "/bulk/databases/postgres"
```

`source_dir` is **anchored at the guest's `rrsync` root**, not at the guest's
filesystem root. `rrsync` prefixes any absolute path with its own restricted
directory, so `/var/lib/postgresql/backups` would resolve to
`<root>/var/lib/postgresql/backups` and match nothing. `/` means "the whole of
what this key is allowed to see".

### Tier-2 target shape

```yaml
postgres_standby_s3_targets:
  - name: "RUSTFS"                 # env-var prefix in the credentials file
    bucket: "db-dr"
    prefix: "postgres"
    endpoint_url: "https://..."    # omit for AWS S3
    access_key: "..."              # wire env/SOPS-sourced, never a literal
    secret_key: "..."
```

## Restore

Owned by the source engine's role: the apps `postgres` role's `dr_restore` path
(`pg_restore --clean --if-exists`) consumes the newest dump from this archive or
a Tier-2 copy. The mandatory restore drill is defined in the DR standard.

## Usage

```bash
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags postgres_standby
# Seed/refresh now (e.g. first run) without waiting for the timer:
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags postgres_standby -e postgres_standby_run_now=true
```
