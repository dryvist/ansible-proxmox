# pve_backup_jobs

Reconciles the cluster's vzdump backup jobs from a declared desired state, with
guests selected **by pool**.

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

## Usage

Inert by default: nothing is created, changed or removed until
`pve_backup_jobs_manage` is true **and** `pve_backup_jobs_jobs` is non-empty.
Declared jobs default to `enabled: false`, so a first full run — a serious IO
event — stays a deliberate act rather than a side effect of a converge.

Backup jobs live in the cluster filesystem, so all work runs on the single
`pve_backup_jobs_config_host`. Pool ids, storage ids and node names are
environment values and belong in `host_vars`/`group_vars`, never in this role.

`pve_backup_jobs_prune_unmanaged` (on by default) removes vzdump jobs the
declaration does not contain. With the desired list empty the whole reconcile is
skipped, so it cannot sweep a cluster by accident.

The target storage must not be backed by a pool that holds the guests it
protects, or one failure takes both. `is_mountpoint` is set on the storage so an
unmounted pool marks it offline rather than letting vzdump write into the empty
directory underneath the mountpoint.

See `defaults/main.yml` for the full variable set.
