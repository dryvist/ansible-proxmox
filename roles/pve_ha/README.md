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
   --state started --max_restart 3 --max_relocate 1`). VMIDs resolve from the
   tofu inventory by hostname (containers, `pve_ha_ct_hostnames`) or by tofu
   vms-map key (VMs, `pve_ha_vm_names`), so a renumber flows through with no
   edit.
2. Adds `resource-affinity` **negative** rules so the two halves of each
   redundant pair never share a node.
3. Adds a **strict `node-affinity` rule per home node**
   (`<pve_ha_home_rule_prefix>-<node>`) confining every HA-managed guest with no
   pvesr replica to the single node holding its rootfs/disks.
4. For the **singleton app guests** (`pve_ha_replication_ct_hostnames` for
   containers, `pve_ha_replication_vm_names` for VMs), creates a `pvesr` job
   shipping each one's storage to its declared `ha_replication_target` — a
   per-guest attribute in the tofu desired state, alongside `node` — so
   ha-manager has a replica to relocate onto.

Guests (default `pve_ha_ct_hostnames`): `openbao-01`, `openbao-02`,
`technitium-dns`, `technitium-dns-2`, `traefik`, plus the singleton app guests
`postgres-apps`, `nautobot`, `vikunja`, and the singleton VM `pve_ha_vm_names`:
`iac-platform`. Anti-affinity pairs (`pve_ha_anti_affinity_groups`): the two
OpenBao Raft voters, the two Technitium DNS instances, the Traefik ingress pair
(auto-activates once `traefik-2` exists), and the Postgres primary/standby
pair. A pair whose members do not all resolve is skipped.

## Three guest classes, each one DECLARED

Every guest here sits on **local ZFS**, not shared storage, so ha-manager can
only start a guest on another node if its rootfs already exists there (`pvesr`).
The guests split on how they survive a node loss. Which class a guest is in is
**declared**, never inferred: an HA-managed guest that matches none of the three
lists below fails the converge (`roles/pve_ha/tasks/classification.yml`).

That guard exists because "has a live peer" used to be read as an ABSENCE — in
`pve_ha_ct_hostnames` but not in `pve_ha_replication_ct_hostnames` — so a
singleton simply forgotten from the replication list was silently treated as
though a peer covered its outage, and got an in-place restart with no
relocation target. An absence is not a declaration.

**Peer-redundant** (`openbao-*`, `technitium-dns*`, `traefik`) — each has a
redundant PEER on another node (OpenBao Raft quorum, the second Technitium
instance, the keepalived VRRP VIP):

- On a **crash**, HA auto-restarts the guest in place (`max_restart`).
- On a **node loss**, the surviving PEER carries the service; the failed guest
  returns when its node heals. No replicated storage needed.
- **Anti-affinity** keeps the redundancy real: it stops HA (or a manual migrate)
  from ever collapsing both peers onto one node.
- A **strict home-node pin** keeps HA from trying to relocate one at all. These
  guests have no replica, so a relocation lands on a node that cannot start
  them; HA then exhausts `max_restart`/`max_relocate` and parks the guest in
  `error`, which is a LATCH an operator must clear by hand — after the source
  node has already self-fenced to get there. Anti-affinity does not cover this:
  it keeps a pair apart, it never says where either half may run.

**Singleton app guests** (`postgres-apps`, `nautobot`, `vikunja` —
`pve_ha_replication_ct_hostnames` — plus the VM `iac-platform` —
`pve_ha_replication_vm_names`) — one instance, no peer, so **relocation is
the only node-loss story**:

- `pvesr` ships each guest's storage to its declared `ha_replication_target`
  on a schedule (`pve_ha_replication_schedule`, default `*/15`), so a
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

Membership in `pve_ha_replication_ct_hostnames`/`pve_ha_replication_vm_names`
is the per-guest "relocation is viable" knob. A guest in `pve_ha_ct_hostnames`/
`pve_ha_vm_names` but not in the matching replication list is treated as
peer-redundant and gets no `pvesr` job.

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

**Pinned singletons** (`zammad`, `plex` — `pve_ha_singleton_ct_hostnames`,
`pve_ha_singleton_vm_names`) — no peer and no replica, **by decision**. Their
node-loss story is an in-place restart on their home node, enforced by that
node's strict pin; they never relocate. Listing one here is what makes that a
decision an operator wrote down rather than an omission. Giving one a real
relocation story means declaring an `ha_replication_target` on its entry in the
desired state and moving it to `pve_ha_replication_ct_hostnames`.

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
| `pve_ha_extra_sids` | `[]` | Verbatim extra SIDs for a guest the tofu maps don't cover. Never a tofu-known VM — those go in `pve_ha_vm_names`, which gets a node-affinity rule; an extra SID gets none. |
| `pve_ha_anti_affinity_groups` | pairs | Redundant pairs to keep apart. |
| `pve_ha_max_restart` / `pve_ha_max_relocate` | `3` / `1` | Per-guest bounds. |
| `pve_ha_replication_ct_hostnames` | app list | Singleton containers that get a `pvesr` replica (relocation-enabled). |
| `pve_ha_replication_vm_names` | `[iac-platform]` | Singleton VMs that get a `pvesr` replica, parallel to `pve_ha_replication_ct_hostnames`. |
| `pve_ha_replication_schedule` | `*/15` | `pvesr` schedule (systemd-calendar subset). |
| `pve_ha_replication_rate` | `""` | `pvesr` rate limit in MB/s; empty = unlimited. |
| `pve_ha_replication_jobnum` | `0` | Job-number suffix in the `<vmid>-<jobnum>` job id. |
| `pve_ha_replication_affinity_rule` | `apps-replication-nodes` | Name kept for the strict node-affinity rule over whichever `[node, ha_replication_target]` pair currently carries it live; every other distinct pair gets its own derived rule name. |
| `pve_ha_home_rule_prefix` | `pve-ha-home` | Prefix of the per-home-node strict pins applied to every replica-less HA guest. |
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
