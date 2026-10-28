# pve_backup_jobs

Reconciles the cluster's vzdump backup jobs from a declared desired state. Each
job selects guests by pool or selects all guests on one node. Every job writes
to one Proxmox Backup Server (PBS) storage.

## Installation

Ships with this repo. Reference it from a play:

```yaml
- hosts: proxmox
  roles:
    - role: pve_backup_jobs
```

## Selection

PVE supports selecting either all guests or one resource pool. The API treats
`all` and `pool` as mutually exclusive. `all: true` together with `node` selects
every guest on that node, regardless of its pool. **All guests per node is the
fleet standard**, so inventory does not need to move guests out of their
existing category pools.
The `schedule` value uses PVE calendar syntax; an `HH:MM` value is a daily
event, and the Proxmox nodes run in UTC.

Pool selection remains available for a job that intentionally covers only one
pool on one node. Validation refuses a job that sets both `pool` and `all`, and
a job that sets neither. A literal `vmid` list is refused: if an id is reused
for a different guest, the job would silently protect that new guest instead.

```yaml
# Fleet standard: every guest on one node.
- id: guests-pve-r540
  all: true
  node: pve-r540
  storage: guests
  schedule: "06:00"

# Scoped alternative: one pool on one node.
- id: platform-pve-r540
  pool: platform
  node: pve-r540
  storage: guests
  schedule: "06:00"
```

## What this role does not do

It does not verify itself. The assertion that catches a job protecting the wrong
guest lives in `pve_health_telemetry`, which compares the archives on disk
against the published inventory and stamps the health line accordingly — a job
cannot be trusted to audit its own aim. Its contract is pinned by
`tests/pve_backup_identity/test_identity_assert.py`.

It does not assert restorability either. Archive size and presence are not
evidence that an archive restores; only a periodic restore into a scratch pool,
with a check that the expected data is inside, is. That is out of scope here.

`exclude_names` can omit selected guests using their keys in the published
`tofu_data` inventory. The role resolves those names to current VMIDs and fails
validation when a name is missing or has no valid VMID; literal guest-id lists
remain refused.

It does not create the PBS prune job. Retention is PBS-side (see below), and
that job lives on the PBS server.

## Backup target

The role ensures one PBS storage. Its id is `guests`
(`pve_backup_jobs_storage_id`). `pbs` is the storage type, which names the
protocol, so the id leaves it out. Every PVE node can use the storage.

| Variable | Source |
| --- | --- |
| `pve_backup_jobs_pbs_server` | Inventory. An FQDN, never an address, so the server can move. |
| `pve_backup_jobs_pbs_secret_path` | OpenBao KV v2 path. Default `platform/pbs/pve-nodes`, under the mount `pve_backup_jobs_bao_kv_mount` (default `secret`). |

The OpenBao path holds four fields:

- `PBS_TOKEN_ID`: the full auth id, such as `user@realm!tokenname`.
- `PBS_TOKEN_SECRET`: the token secret.
- `PBS_FINGERPRINT`: the server certificate fingerprint. PBS serves a self-signed
  certificate, so the fingerprint is pinned.
- `PBS_DATASTORE`: the datastore name.

The role reads the path on the controller with
`community.hashi_vault.vault_kv2_get`. It uses `BAO_ADDR` (or `VAULT_ADDR`) and
`BAO_TOKEN`, the same as `pve_api_tokens`. The read runs only on the config host,
under `no_log`. A missing field fails the run.

## Retention

PBS owns retention. vzdump writes every job with `prune-backups keep-all=1`, so
it never prunes. A prune job on the PBS datastore removes old snapshots for all
writers at once. vzdump pruning would apply per job and see only the snapshots
that one job wrote.

The PBS prune job is not part of this repo. Create it on the PBS server before
you enable any job. Without it, snapshots accumulate.

## Node restriction

Every job must name exactly one node (`node`, PVE format `pve-node`). An
all-node job backs up every guest on that node; a pool job backs up guests in
that pool on that node. A job that names two nodes matches nothing.

Validation refuses a job that names no node, a list, or
`pve_backup_jobs_pbs_node`. Jobs cannot target the backup node because that
would store its guests' backups on the same host.

## Usage

Inert by default: nothing is created, changed or removed until
`pve_backup_jobs_manage` is true **and** `pve_backup_jobs_jobs` is non-empty.
Declared jobs default to `enabled: false`, so a first full run — a serious IO
event — stays a deliberate act rather than a side effect of a converge.

Backup jobs live in the cluster filesystem, so all work runs on the single
`pve_backup_jobs_config_host`. Pool ids, node names and the PBS server are
environment values. They belong in `host_vars` or `group_vars`, never in this
role.

PVE rejects a pool-scoped job whose pool does not exist. The first converge
with that job declared fails until the pool exists. All-node jobs do not depend
on a resource pool.

`pve_backup_jobs_prune_unmanaged` (default `true`) removes every vzdump job the
declaration does not contain. That includes enabled and disabled jobs, and jobs
made in the web UI. The inventory sets it to `false`, because the live job set
has not been checked against the declaration. Set it to `true` only after you
confirm that no undeclared job runs. With the desired list empty the whole
reconcile is skipped, so it cannot sweep a cluster by accident.

The backup target must not share a failure domain with the guests it protects.
That is why the backup node is excluded above.

See `defaults/main.yml` for the full variable set.
