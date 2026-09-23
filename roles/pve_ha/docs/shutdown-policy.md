# Cluster shutdown policy

The role also owns `shutdown_policy`, which decides what happens to
HA-managed guests when a node goes down. It is the `ha.shutdown_policy` key
of `/cluster/options`, set through `pvesh` rather than by editing
`/etc/pve/datacenter.cfg` directly — a bare top-level `shutdown_policy` key
there is outside the config schema and makes every `ha-manager`/`pvesh` call
on the node fail to parse the file.

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

`tasks/datacenter_cfg.yml` reads `/cluster/options` via `pvesh get` and only
calls `pvesh set /cluster/options -ha shutdown_policy=<value>` when the
current value differs, so a converge with nothing to do makes no API call.
Any leftover top-level `shutdown_policy` key in `datacenter.cfg` from a prior
release — cluster-wide and carrying keys this role does not own (`keyboard`,
`migration`, bandwidth limits, ...) — is removed.
`tests/pve_ha_datacenter_cfg/verify_shutdown_policy.yml` runs that task file
against a mock `pvesh` and asserts the legacy key is removed, the policy is
set when it differs, another key already in `ha` survives, and a second pass
against an already-correct policy calls `pvesh set` no further.
