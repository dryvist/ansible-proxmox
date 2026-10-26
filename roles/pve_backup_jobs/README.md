# pve_backup_jobs

Reconciles the cluster's vzdump backup jobs from a declared desired state. Guests
are selected **by pool**. Every job writes to one Proxmox Backup Server (PBS)
storage.

## Installation

Ships with this repo. Reference it from a play:

```yaml
- hosts: proxmox
  roles:
    - role: pve_backup_jobs
```

## Why pool selection

`vzdump` offers three selection modes: every guest, a pool, or a literal list of
guest ids. A literal list records which numbers were true on the day someone
typed them, not what the job was for. When a guest id is later reused for a
different guest, the list keeps selecting the number — so the job runs on the
same schedule, writes to the same storage, prunes normally and exits clean,
while protecting something else entirely. Nothing the job emits contradicts it.

Every guest already carries a declared pool in the published inventory, so a
pool-scoped job states the intent directly: a guest enters or leaves coverage by
its declared identity, and a newly provisioned guest is covered with no edit
here. There is no tag-based selection available to use instead.

## What this role does not do

It does not verify itself. The assertion that catches a job protecting the wrong
guest lives in `pve_health_telemetry`, which compares the archives on disk
against the published inventory and stamps the health line accordingly — a job
cannot be trusted to audit its own aim. Its contract is pinned by
`tests/pve_backup_identity/test_identity_assert.py`.

It does not assert restorability either. Archive size and presence are not
evidence that an archive restores; only a periodic restore into a scratch pool,
with a check that the expected data is inside, is. That is out of scope here.

It does not create the PBS prune job. Retention is PBS-side (see below), and
that job lives on the PBS server.

## Scope: far less needs image backup than it looks

An image backup is the fallback for state with no better home. Excluded
deliberately:

| Excluded | Because |
| --- | --- |
| Bulk media | Re-acquirable, and multiple TB of it |
| Model / agent working sets | Reconstructed by their roles from source |
| Log and telemetry data | Explicitly outside the DR scope |
| Databases | A native dump beats a crash-consistent image of a live engine |

What remains is service state that is neither re-acquirable nor covered by a
native mechanism.

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

vzdump matches one node name per job (`node`, PVE format `pve-node`). A job runs
on that node and backs up its guests only. A job that names two nodes matches
nothing. So a pool that spans several nodes needs one job per node.

Every job must set `node` to a single node that is not
`pve_backup_jobs_pbs_node`. The validation refuses a job that names no node, a
list, or the backup node. A job with no node would also back up the guests on
the backup node, onto the same host that stores them. Those guests stay uncovered
until a second target exists.

## Usage

Inert by default: nothing is created, changed or removed until
`pve_backup_jobs_manage` is true **and** `pve_backup_jobs_jobs` is non-empty.
Declared jobs default to `enabled: false`, so a first full run — a serious IO
event — stays a deliberate act rather than a side effect of a converge.

Backup jobs live in the cluster filesystem, so all work runs on the single
`pve_backup_jobs_config_host`. Pool ids, node names and the PBS server are
environment values. They belong in `host_vars` or `group_vars`, never in this
role.

PVE rejects a job whose pool does not exist. The first converge with jobs
declared fails at that job until the pool exists.

`pve_backup_jobs_prune_unmanaged` (default `true`) removes every vzdump job the
declaration does not contain. That includes enabled and disabled jobs, and jobs
made in the web UI. The inventory sets it to `false`, because the live job set
has not been checked against the declaration. Set it to `true` only after you
confirm that no undeclared job runs. With the desired list empty the whole
reconcile is skipped, so it cannot sweep a cluster by accident.

The backup target must not share a failure domain with the guests it protects.
That is why the backup node is excluded above.

See `defaults/main.yml` for the full variable set.
