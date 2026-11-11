# syncoid

Cross-node ZFS replication with [syncoid](https://github.com/jimsalterjrs/sanoid)
— **layer 2** of the storage-resiliency model (survives losing a whole node or
pool). Pairs with the `sanoid` role: syncoid ships the snapshots sanoid takes.

## Installation

This role ships in the `ansible-proxmox` repository and is applied via
`playbooks/site.yml`. No separate installation is required beyond cloning the
repo and installing collection dependencies:

```bash
git clone https://github.com/dryvist/ansible-proxmox.git
cd ansible-proxmox
ansible-galaxy install -r requirements.yml
```

## Model

**Pull, from the target.** Run this role on the **backup** node (e.g. node-b); it
SSHes to each source (e.g. node-a) and pulls. Pull-from-backup is safer than push
— a compromised source cannot reach the backup. `--no-sync-snap` replicates the
snapshots `sanoid` already took rather than creating new ones.

A failed job (source offline — expected for the intermittent node-c) is logged to
`/var/log/syncoid/` and does **not** abort the remaining jobs — but it is
counted: any failed job makes the wrapper exit non-zero and ping
`syncoid_healthcheck_url/fail` (if set), so a bad run is never silently
exit-0.

Each run also writes syslog lines with the tag `syncoid-replicate`, so the log
pipeline can check every replica:

- one line per job: `job=<name> group=<group> result=ok|failed rc=<rc> duration_s=<s>`;
- one line per run: `run group=<group> result=ok|failed|no_jobs|skipped`, with the
  job count and the failed job names.

Failed and `no_jobs` lines use priority `daemon.err`, a skipped run (the group's
lock is still held) uses `daemon.warning`, and successful lines use
`daemon.info`.

## Prerequisite (apply-time)

SSH trust from this node's `syncoid_user` (default `root`) to each source host,
set up out of band. The role schedules replication; it does not distribute keys.

## Variables

| Variable                                    | Default                              | Description                                                            |
| ------------------------------------------- | ------------------------------------ | ---------------------------------------------------------------------- |
| `syncoid_enabled`                           | `true`                               | Master enable                                                          |
| `syncoid_jobs`                              | `[]`                                 | List of `{ name, source, target, options?, schedule? }`; empty = inert |
| `syncoid_retired_replica_datasets`          | `[]`                                 | Literal `bulk/replica/…` paths destroyed once their pull job is gone   |
| `syncoid_default_options`                   | `--recursive --no-sync-snap --quiet` | Applied when a job omits `options`                                     |
| `syncoid_cron_hour` / `syncoid_cron_minute` | `2` / `17`                           | Schedule for the `default` group                                       |
| `syncoid_extra_schedules`                   | `{}`                                 | Extra cadence groups (see below)                                       |
| `syncoid_user`                              | `root`                               | User that runs syncoid (needs SSH to sources)                          |
| `syncoid_healthcheck_url`                   | `""`                                 | healthchecks.io URL; pings on success, `/fail` if any job failed       |
| `syncoid_restore_check_enabled`             | `false`                              | Weekly restore check (see below)                                       |
| `syncoid_restore_check_dataset`             | `example/dataset`                    | Replica dataset to check; runtime inventory supplies the real value   |
| `syncoid_restore_check_bucket`              | `example-bucket`                     | Bucket directory the check must find non-empty inside the clone        |

## Restore check

Freshness proves a copy was pulled; it does not prove the copy **reads back**.
When `syncoid_restore_check_enabled` is true and a
`syncoid_restore_check_dataset` is declared, the role installs a weekly systemd
timer (`syncoid-restore-check.timer` — nominal time off the `:00/:15/:30/:45`
grid and away from the minutes sanoid and the syncoid cron lines own,
`RandomizedDelaySec` + `FixedRandomDelay=true`, `Persistent=true`) that runs
`/usr/local/bin/syncoid-restore-check.sh` on the node that holds the replica.
The script:

1. finds the newest snapshot of the replica dataset;
2. `zfs clone`s it **read-only** (`readonly=on`, `canmount=noauto`) to a
   throwaway dataset and mounts it at a temporary mountpoint under `/run`;
3. confirms the object store's bucket directory (`syncoid_restore_check_bucket`)
   exists and is non-empty inside the clone;
4. **always** destroys the clone — the destroy runs from the script's `EXIT`
   trap, so every failure path tears down what it cloned;
5. logs one syslog line (tag `syncoid-restore-check`) with the result, the
   snapshot name and the snapshot's age, so the log pipeline sees the weekly
   result (`daemon.info` on success, `daemon.err` with a `reason=` on failure).

A known-object check (`deployment.json`) is deliberately NOT asserted by path:
how the object store lays objects out on disk is not resolvable from this
repository (the store guest is deployed by `ansible-proxmox-apps`), so the
check verifies only that the bucket directory exists and is non-empty. When
the store's on-disk layout is published upstream, tighten the check to the
named object.

Runtime inventory supplies the real dataset and bucket values through the
variables above. The role defaults and tracked inventory example contain only
placeholders. Disabling the check removes the timer and units: the declared
state includes the absence.

## Usage

```yaml
syncoid_jobs:
  - name: node-a-nas
    source: "root@node-a:rpool/data/nas"
    target: "tank/replica/node-a/nas"
```

### Schedule groups

One cadence per node stops working once a node pulls datasets with different
RPOs — a few GB of configuration wants hourly, a multi-hundred-GB namespace does
not, and without groups the only way to tighten one is to tighten both. Declare
extra groups and let a job opt in:

```yaml
syncoid_extra_schedules:
  hourly:
    hour: "*"
    minute: "37"

syncoid_jobs:
  - name: app-config
    schedule: hourly # omit to stay in `default`
    source: "root@node-a:rpool/data/vm-200-disk-2"
    target: "bulk/replica/node-a/vm-200-disk-2"
```

The schedule renders as a whole `/etc/cron.d/syncoid` file rather than as
individual crontab entries, so a group that stops having jobs disappears instead
of leaving a line behind that nothing declares. Each group takes its own lock,
so two groups run concurrently but a group never overlaps itself.

Per-host identity (VMIDs, the source node) is derived at runtime from the S3
tofu inventory injected by `playbooks/load_tofu.yml` — `splunk_vm_from_tofu` and
`containers_from_tofu` (see the replicating node's file under
`inventory/host_vars/`) — never
hard-coded, so a VMID renumber flows through with no edit.

### Retired replica datasets

Removing a job from `syncoid_jobs` stops the pull, not the storage: the replica
it left behind keeps consuming quota on the target pool. List the exact paths
under `syncoid_retired_replica_datasets` to destroy them once. Every entry must
be a literal `bulk/replica/...` path — a wildcard, a snapshot marker (`@`),
`..`, or whitespace fails the converge before anything runs — and a path that
still has child filesystems or volumes (a namespace such as
`bulk/replica/<node>` or its `.../rpool/data`) fails the converge too: declare
the leaves. Only a literal "dataset does not exist" reads as absent and is
skipped, so the converge after a successful destroy is a clean no-op; any
other `zfs list` error fails the task. `zfs destroy -r` removes the dataset
and its own snapshots; it never touches a parent.

```bash
./scripts/run-ansible.sh playbooks/site.yml --tags syncoid
```

## Why `syncoid_healthcheck_url` is load-bearing

It is not optional decoration. With it empty, a job that failed on one dataset
was visible only as a non-zero exit code inside a cron run nobody reads — the
replica kept sitting at the right path with an increasingly old snapshot, which
looks identical to a healthy dataset on a quiet source.

Wiring it makes a failed replication page. It also makes a run that never
happens page, because healthchecks.io expects a ping every cycle and alerts on
its absence — so a wrapper that dies before starting, or a cron line that was
never installed, is caught by the same mechanism.

Both matter more than they look: replication failures are silent by
construction. Nothing downstream reads the replica until someone needs it.
