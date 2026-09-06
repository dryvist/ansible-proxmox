# Cluster shutdown policy

The role also owns `shutdown_policy` in the cluster-wide
`/etc/pve/datacenter.cfg`, which decides what happens to HA-managed guests when
a node goes down.

**Unset is not neutral.** With the key absent, Proxmox falls back to
`conditional`, whose behaviour **splits on how the node was taken down**:

| Node taken down with | `conditional` does |
| --- | --- |
| `reboot` | **Freezes** HA guests — they stay on the node and resume when it returns. |
| `poweroff` | **Migrates** HA guests off to the surviving nodes. |

So today's behaviour silently depends on which command an operator typed,
which nothing else in this repo can read or reason about.

`pve_ha_shutdown_policy` defaults to **`freeze`**, not `migrate`. Every guest
here sits on local zfspool storage, so ha-manager can only relocate one that
already has a pvesr replica on the target node. Under `migrate` a planned
shutdown asks it to relocate *every* HA guest, and each one without a replica
fails to start on the far side and **latches in `error`** — a latch, not a
retry, cleared only by a manual `ha-manager set <sid> --state started`.
`freeze` leaves guests where they are and brings them back with the node:
predictable, and it cannot strand a guest whose storage exists nowhere else.

`migrate` becomes correct once **every** HA-managed guest has a working
relocation path. That is a precondition, not a default — the value is a role
variable so a cluster can move to `migrate` once its replication coverage is
complete. `failover` and `conditional` are the other accepted values; an empty
string leaves the key unmanaged.

Only that one key is written. `datacenter.cfg` is cluster-wide and carries keys
this role does not own (`keyboard`, `migration`, bandwidth limits, ...), so
`tasks/datacenter_cfg.yml` merges the single line in place rather than
templating the file — a template would drop every unmanaged key on the first
converge. `tests/pve_ha_datacenter_cfg/verify_shutdown_policy.yml` runs that
task file against a temporary copy and asserts the unmanaged keys survive and
an existing policy is rewritten rather than duplicated.
