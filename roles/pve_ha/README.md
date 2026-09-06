# pve_ha

Configure Proxmox VE HA (High Availability) for the tier-0 guests via
`ha-manager` (Proxmox VE 9 "HA rules", not the legacy HA groups). Part of the
autonomous DR/HA program (wave W5): a node failure is handled with **zero manual
action**.

## Installation

Ships with this repo. Reference it from a play (see `playbooks/ha.yml`):

```yaml
- hosts: proxmox
  roles:
    - role: pve_ha
```

## Usage

Runs on a **single** node (`pve_ha_config_host`) because HA state is
cluster-wide (`/etc/pve/ha/*`, replicated by pmxcfs).

```bash
# Preview (asserts-out, no change — inert by default):
doppler run -- ansible-playbook -i inventory playbooks/ha.yml

# LIVE enable (gated — changes cluster HA behaviour for tier-0 guests):
doppler run -- ansible-playbook -i inventory playbooks/ha.yml -e pve_ha_enabled=true
```

When enabled it:

1. Places each managed guest under HA (`ha-manager add ct:VMID` or `vm:VMID
   --state started --max_restart 3`) with `--max_relocate` set from its
   **HA class** — see below. VMIDs resolve from the
   tofu inventory by hostname (containers, `pve_ha_ct_hostnames`) or by tofu
   vms-map key (VMs, `pve_ha_vm_names`), so a renumber flows through with no
   edit.
2. Adds `resource-affinity` **negative** rules so the two halves of each
   redundant pair never share a node.
3. Adds a **strict `node-affinity` rule per home node**
   (`<pve_ha_home_rule_prefix>-<node>`) confining every HA-managed guest with no
   pvesr replica to the single node holding its rootfs/disks.
4. For the **singleton** class (`pve_ha_replication_ct_hostnames` for
   containers, `pve_ha_replication_vm_names` for VMs — both derived), creates
   a `pvesr` job
   shipping each one's storage to its declared `ha_replication_target` — a
   per-guest attribute in the tofu desired state, alongside `node` — so
   ha-manager has a replica to relocate onto.

Guests under HA come from `pve_ha_ct_hostnames` (containers) and
`pve_ha_vm_names` (VMs). Anti-affinity pairs (`pve_ha_anti_affinity_groups`):
the two OpenBao Raft voters, the two Technitium DNS instances, the Traefik
ingress pair, and the Postgres primary/standby pair. A pair whose members do
not all resolve is skipped.

## Three HA classes, all DERIVED

Every guest here sits on **local ZFS**, not shared storage, so ha-manager can
only start a guest on another node if its rootfs already exists there
(`pvesr`). How a guest survives a node loss is its **class**, and the class is
derived from data that already exists — there is no per-guest class list to
keep in sync, so **a guest added later lands in the right class with no edit
to this role**.

**Native application HA is preferred over relocation.** A service that is
already redundant across nodes does not need, and should not get, a
block-level copy of its disk.

| Class | Derived from | `max_relocate` | `pvesr` replica |
| --- | --- | --- | --- |
| `application_ha` | membership of a `pve_ha_anti_affinity_groups` entry | `0` | none |
| `immovable` | a key of `pve_ha_immovable_guests` (the one explicit class) | `0` | none |
| `singleton` | neither of the above — the default | `pve_ha_max_relocate` | **required** |

**`application_ha`** — the service provides its own redundancy across nodes: a
Raft quorum member, a DNS secondary with zone transfer, a keepalived VRRP
ingress pair, a streaming database primary/standby. Being in an anti-affinity
group is already the assertion that a peer exists on another node, so that
membership *is* the classification.

- On a **crash**, HA auto-restarts the guest in place (`max_restart`).
- On a **node loss** the guest stays down, its peer serves, and it returns on
  boot. `max_relocate` is `0`: there is nowhere to go and nothing to gain.
- It gets **no `pvesr` replica**, and that is a correctness point, not a
  saving. A stale block-level copy of a quorum member can rejoin carrying old
  state; the store already survives losing the guest, which is what quorum is
  for. The same argument applies to a DNS secondary with native zone transfer.
- **Anti-affinity** keeps the redundancy real: it stops HA (or a manual
  migrate) from ever collapsing both peers onto one node.
- A **strict home-node pin** keeps HA from trying to relocate it at all. Such
  a relocation lands on a node that cannot start it; HA then exhausts
  `max_restart`/`max_relocate` and parks the guest in `error`, which is a
  LATCH an operator must clear by hand — after the source node has already
  self-fenced to get there.

**`immovable`** — cannot relocate for a structural reason, declared in
`pve_ha_immovable_guests` as `name: reason`. `plex` is the only one: its
container config carries bind mounts (host directory paths, not zvols), and
`pvesr` replicates zvols only, so it can be neither replicated nor
live-migrated — now or later. It keeps the crash auto-restart it does benefit
from, with `max_relocate` `0` so ha-manager never attempts a move that could
only fail. Being immovable exempts it from the singleton replica requirement.

"Not replicated yet" is **not** immovable. That is a singleton missing its
replica, and the converge is supposed to fail on it. Two guards keep the
exemption honest (`roles/pve_ha/tasks/classification.yml`): an immovable guest
may not also be an anti-affinity group member, and an immovable entry naming a
guest under no HA management is refused rather than sitting inert.

**`singleton`** — no application-level redundancy, so relocation is the only
HA available, and a relocation needs a replica. This is the **default class**,
which is what makes the model safe: a guest nobody classified is held to the
strictest requirement rather than silently assumed to have a peer.
`pve_ha_replication_ct_hostnames` / `pve_ha_replication_vm_names` are derived
as exactly this class.

**A singleton without a replica fails the converge, by name** — before any
guest reaches ha-manager (`roles/pve_ha/tasks/tier0_resources.yml`). That
check is the point of the whole classification: discovering a missing
relocation path during an outage is how this estate lost a guest in the first
place.

- `pvesr` ships each guest's storage to its declared `ha_replication_target`
  on a schedule (`pve_ha_replication_schedule`, default `*/5`), so a
  current-enough replica exists to relocate onto. The target is a per-guest
  attribute in the tofu desired state — this role only reads it, it has no
  opinion on node placement. A guest listed in
  `pve_ha_replication_ct_hostnames`/`pve_ha_replication_vm_names` whose
  inventory entry publishes no `ha_replication_target` fails the converge
  loud (`pve_ha_fail_on_unresolved`), naming the guest and the missing
  attribute.
- The pair's node list is checked against the inventory before the rule is
  written: a `ha_replication_target` naming a node that is not commissioned, or
  that does not carry the guest's datastore, fails the converge. A strict rule
  naming a node that cannot start the guest is the exact shape of the outage
  this role exists to prevent.
- On a **node loss**, ha-manager relocates the guest to the target and starts
  it from the replica. `max_relocate=1` is enough: one hop to the target.
- A **strict `node-affinity` rule per distinct `[node, target]` pair** pins
  each guest to its own pair, so ha-manager can never relocate one onto a
  node without a replica and then start-fail/flap. `strict` = run only on
  the listed nodes. Whichever pair currently matches the LIVE nodes of the
  rule named `pve_ha_replication_affinity_rule` keeps that name — resolved
  from the cluster, not a hardcoded pair — so the live rule is enforced in
  place rather than renamed and re-created.
- The replica is a **relocation enabler, not the durability layer**: the app
  guests' real data-loss window is covered separately (`postgres-apps` by
  streaming replication + WAL archiving; `nautobot`/`vikunja` are near-stateless
  — their state lives in `postgres-apps`).

With 4 quorate nodes, HA fencing is safe — losing one node keeps quorum, so no
surviving node self-fences.

Because a `pvesr` job is node-local (`pvesr create-local-job` runs on the guest's
source node), the replication tasks run on **every** node and each creates jobs
only for the guests homed on it; the cluster-wide HA config still runs once on
`pve_ha_config_host`.

Before any `pvesr` job is created, the role hard-fails the converge if a job's
target node lacks a storage id used by the guest's volumes. `pvesr` replicates
to the SAME storage id on the target, so a mismatch would otherwise fail
silently on first sync — Ansible reports success, but no replica ever exists.
For a container this is read from `pvesh get /storage` (not a hand-rolled
parse of `/etc/pve/storage.cfg`) against its volumes from
`pvesh get /nodes/<node>/lxc/<vmid>/config`. For a VM it uses the storage ids
already published in the tofu inventory's `disks` list — a VM can have
several disks, unlike a container's single rootfs. A storage entry with no
`nodes` restriction is treated as available on every node.

### Which nodes a rule may name

Every strict rule this role writes is checked against the published inventory's
own `nodes` and `node_storage` maps
(`roles/pve_ha/tasks/storage_eligibility.yml`). A node may appear in a guest's
rule only when it is commissioned **and** its usable datastores include that
guest's `datastore` — the two stores every PVE node ships with, plus each
declared pool REGISTERED with `pvesm`. An unregistered pool is a real ZFS pool
PVE does not expose as storage, so no guest disk can live on it.

A guest whose own home node fails that test, or whose inventory entry publishes
no `datastore` at all, stops the converge rather than receiving a rule built on
a guess.

## Cluster shutdown policy

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

## Safety

**Inert by default.** Nothing happens unless `pve_ha_enabled=true`. Enabling is a
deliberate, gated step. All CLI work is skipped under Docker so the role is
molecule-testable.

## Failover drill (non-destructive)

`scripts/ha-failover-drill.sh <test-sid> <other-node-name>` proves both
auto-restart and relocation against a **disposable** test container (never a
tier-0 guest — it hard-refuses). It adds the test guest to HA, stops it and
confirms HA restarts it, migrates it to another node and back, then removes it.
No real service is touched.

## Key variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `pve_ha_enabled` | `false` | Master switch (inert until true). |
| `pve_ha_config_host` | `pve` | Single node the ha-manager commands run on. |
| `pve_ha_ct_hostnames` | tier-0 list | LXC guests to HA-manage (by hostname). |
| `pve_ha_vm_names` | `[iac-platform]` | VMs to HA-manage (by tofu vms-map key), resolved/enrolled/pinned the same way as a container. |
| `pve_ha_extra_sids` | `[]` | Verbatim SIDs for a guest the tofu maps miss. Never a tofu-known VM — those go in `pve_ha_vm_names`, which is also pinned. |
| `pve_ha_anti_affinity_groups` | pairs | Redundant pairs to keep apart. |
| `pve_ha_max_restart` / `pve_ha_max_relocate` | `3` / `1` | Restart bound for every guest; relocate bound for the singleton class only. |
| `pve_ha_pinned_max_relocate` | `0` | Relocate bound for `application_ha` and `immovable` guests — nowhere to go. |
| `pve_ha_replication_ct_hostnames` | *derived* | The singleton containers — HA-managed, in no anti-affinity group, not immovable. Not hand-maintained. |
| `pve_ha_replication_vm_names` | *derived* | The singleton VMs, derived the same way. |
| `pve_ha_immovable_guests` | `{plex: ...}` | Guests that cannot relocate for a structural reason, as `name: reason`. The only class that is declared. |
| `pve_ha_class_application` | *derived* | Anti-affinity group members — the guests whose own service is redundant across nodes. |
| `pve_ha_replication_schedule` | `*/5` | `pvesr` schedule (systemd-calendar subset). |
| `pve_ha_replication_rate` | `""` | `pvesr` rate limit in MB/s; empty = unlimited. |
| `pve_ha_replication_jobnum` | `0` | Job-number suffix in the `<vmid>-<jobnum>` job id. |
| `pve_ha_replication_affinity_rule` | `apps-replication-nodes` | Name kept for the strict node-affinity rule over the pair currently carrying it live. |
| `pve_ha_home_rule_prefix` | `pve-ha-home` | Prefix of the per-home-node strict pins applied to every replica-less HA guest. |
| `pve_ha_shutdown_policy` | `freeze` | Cluster-wide `shutdown_policy` in `datacenter.cfg`. `migrate` only once every HA guest has a replica. |
| `pve_ha_datacenter_cfg_path` | `/etc/pve/datacenter.cfg` | Path to the cluster-wide config; a variable so the offline test can target a temp copy. |
| `pve_ha_manage_all` | `false` | Also enroll the rest of the estate in HA. Widens enrollment only — the home pin applies either way. |

## Why `ha.yml` is imported by `site.yml` rather than left standalone

It previously existed only as a standalone playbook driven by a hand-typed
`-e pve_ha_enabled=true`, and `site.yml` never included it. So a routine
converge configured no HA at all, and HA silently did nothing on every node
loss — the failure only became visible at the moment it was needed, which is
the worst possible time to discover a control was never armed.

Importing it here makes the flag the only switch: the role stays inert unless
`pve_ha_enabled` is true in inventory group_vars, but the decision is now
declarative and reviewable instead of depending on whoever ran the playbook
remembering an extra argument.

`ha.yml` re-imports `load_tofu.yml`; `import_playbook` is safe to repeat.
