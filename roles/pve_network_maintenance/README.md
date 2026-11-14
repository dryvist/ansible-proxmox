# pve_network_maintenance

Opens and closes a network maintenance window on a Proxmox VE cluster. The
window is declared, not discovered: a **pre** phase disarms HA and pauses the
enabled vzdump backup jobs, and a **post** phase re-arms HA and re-enables
exactly the jobs that were paused. The maintenance itself runs between the two
invocations.

It drives only the native PVE 9.2 HA controls (`ha-manager` and `pvesh`); it
implements no fencing or watchdog logic of its own. The disarm feature is the
vendor's: see the section **"Disarming HA for Cluster Maintenance"** in the
Proxmox VE HA manager documentation.

## Usage

Two invocations of `playbooks/network_maintenance.yml`, with the maintenance
in between:

```bash
# Open the window: disarm HA (freeze), pause backups, wait for tasks to drain.
./scripts/run-ansible.sh playbooks/network_maintenance.yml \
  -e pve_network_maintenance_phase=pre

# ... perform the network maintenance ...

# Close the window: wait for quorum, re-arm HA, resume backups.
./scripts/run-ansible.sh playbooks/network_maintenance.yml \
  -e pve_network_maintenance_phase=post
```

HA and backup job state are cluster-wide, so every command runs on the single
`pve_network_maintenance_config_host`. Its default selects the cluster primary
from `pve_cluster_primary_host` or `proxmox_node_names.primary`, falling back
to the first host in the `proxmox` group, without requiring the `pve_ha` role
to be loaded. The role is a no-op on every other node. `--check` performs the
reads and previews the writes; the waits are skipped and the existing window
state is unchanged.

## Pre phase

1. Asserts the cluster is quorate and every node is online
   (`pvesh get /cluster/status`), and no HA resource is in an `error`, `fence`
   or `recover` state (`pvesh get /cluster/ha/status/current`) — the vendor
   disarm is deferred while services are being fenced, recovered or migrated,
   so such a resource would leave the window undetermined.
2. Records every **enabled** vzdump job (`pvesh get /cluster/backup`) in a
   state file on the config host,
   `/var/lib/pve-network-maintenance/state.json` (mode `0600`, root), then
   disables each one (`pvesh set /cluster/backup/<id> --enabled 0`). Waits,
   bounded (`pve_network_maintenance_drain_timeout`, default 30 minutes),
   until no vzdump task is running and no replication job reports an active
   `pid` on any node. If either wait times out, the paused jobs are re-enabled
   and the run fails with the window still closed.
3. Runs `ha-manager crm-command disarm-ha freeze`, which releases all CRM and
   LRM watchdogs cluster-wide. Waits, bounded (default 10 minutes), until
   `ha-manager status` reports the fencing state `disarmed` and every LRM
   entry shows its watchdog released.
4. Reports: `network maintenance window open: HA disarmed (freeze), backups
   paused`.

A job that was already disabled before the window is never recorded and never
re-enabled. Re-running pre while the window is open merges any newly enabled
jobs into the existing state file and skips the disarm command.

## Post phase

1. Waits, bounded (`pve_network_maintenance_quorum_timeout`, default 20
   minutes), for a quorate cluster with every node online.
2. Runs `ha-manager crm-command arm-ha` and waits until `ha-manager status`
   reports the fencing state `armed` again.
3. Re-enables exactly the jobs recorded in the state file — only those still
   present and still disabled — then removes the file. Jobs deleted during
   the window are reported and left alone.
4. Waits, bounded, until every replication job
   (`pvesh get /nodes/<node>/replication`) reports fail count 0.

## Key variables

- `pve_network_maintenance_phase`

  Required: `pre` or `post`. Any other value fails the run.

- `pve_network_maintenance_config_host`

  Default: the cluster primary from `pve_cluster_primary_host` or
  `proxmox_node_names.primary`, falling back to the first host in the
  `proxmox` group. The single node the cluster-wide commands run on.

- `pve_network_maintenance_state_dir` / `pve_network_maintenance_state_file`

  Default: `/var/lib/pve-network-maintenance/state.json`. The pause record.

- `pve_network_maintenance_drain_timeout` / `_delay`

  Default: 1800 / 15 seconds. Bound on the backup and replication task
  drain wait.

- `pve_network_maintenance_disarm_timeout` / `_delay`

  Default: 600 / 10 seconds. Bound on the disarm and re-arm waits.

- `pve_network_maintenance_quorum_timeout` / `_delay`

  Default: 1200 / 15 seconds. Bound on the post-phase quorum wait.

- `pve_network_maintenance_replication_timeout` / `_delay`

  Default: 600 / 15 seconds. Bound on the post-phase fail-count wait.

- `pve_network_maintenance_drain_task_types`

  Default: `[vzdump, vzreplication]`. Task types that must finish before the
  window opens.

- `pve_network_maintenance_blocked_ha_states`

  Default: `[error, fence, recover]`. HA service states that block opening
  the window.

- `pve_network_maintenance_fencing_disarmed_pattern` /
  `pve_network_maintenance_fencing_armed_pattern` /
  `pve_network_maintenance_lrm_line_pattern` /
  `pve_network_maintenance_lrm_idle_pattern`

  ha-manager status matchers. The fencing entry carries the CRM watchdog
  state (`armed | standby | disarming | disarmed`); each LRM entry carries
  that node's watchdog state, which flips to a released/idle value as the LRM
  acknowledges the disarm. Role defaults so field-verified wording can be
  corrected without code changes.

## Warning

While HA is disarmed it recovers nothing: no automatic restart, no
relocation, no fencing. Keep the window short, and close it (the post phase)
as soon as the maintenance finishes.

## Tests

`tests/pve_network_maintenance/verify_*.yml` run the role's own task files
against fixture API output and a stubbed `pvesh` / `ha-manager`, with no
cluster:

```bash
ansible-playbook tests/pve_network_maintenance/verify_pre_window.yml -i localhost, -c local
ansible-playbook tests/pve_network_maintenance/verify_pre_window_drain.yml -i localhost, -c local
ansible-playbook tests/pve_network_maintenance/verify_post_window.yml -i localhost, -c local
ansible-playbook tests/pve_network_maintenance/verify_status_matchers.yml -i localhost, -c local
```
