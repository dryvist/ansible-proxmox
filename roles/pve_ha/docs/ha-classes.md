# Three HA classes, all DERIVED

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

## Which nodes a rule may name

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
