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

1. Places each managed LXC under HA (`ha-manager add ct:VMID --state started
   --max_restart 3 --max_relocate 1`). VMIDs resolve from the tofu inventory by
   hostname, so a renumber flows through with no edit.
2. Adds `resource-affinity` **negative** rules so the two halves of each
   redundant pair never share a node.
3. Adds a **strict `node-affinity` rule per home node**
   (`<pve_ha_home_rule_prefix>-<node>`) confining every HA-managed guest with no
   pvesr replica to the single node holding its rootfs.
4. For the **singleton app guests** (`pve_ha_replication_ct_hostnames`), creates
   a `pvesr` job shipping each one's rootfs to the always-on partner node, so
   ha-manager has a replica to relocate onto.

Guests (default `pve_ha_ct_hostnames`): `openbao-01`, `openbao-02`,
`technitium-dns`, `technitium-dns-2`, `traefik`, plus the singleton app guests
`postgres-apps`, `nautobot`, `vikunja`. Anti-affinity pairs
(`pve_ha_anti_affinity_groups`): the two OpenBao Raft voters, the two Technitium
DNS instances, and the Traefik ingress pair (the last auto-activates once
`traefik-2` exists). A pair whose members do not all resolve is skipped.

## Two guest classes: peer-redundant vs singleton

Every guest here sits on **local ZFS**, not shared storage, so ha-manager can
only start a guest on another node if its rootfs already exists there (`pvesr`).
The guests split on how they survive a node loss:

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
`pve_ha_replication_ct_hostnames`) — one instance, no peer, so **relocation is
the only node-loss story**:

- `pvesr` ships each guest's rootfs to the always-on PARTNER node on a schedule
  (`pve_ha_replication_schedule`, default `*/15`), so a current-enough replica
  exists to relocate onto.
- On a **node loss**, ha-manager relocates the guest to the partner and starts
  it from the replica. `max_relocate=1` is enough: one hop to the partner.
- A **strict `node-affinity` rule** (`pve_ha_replication_affinity_rule`) pins
  these guests to `pve_ha_replication_pair`, so ha-manager can never relocate one
  onto a node without a replica and then
  start-fail/flap. `strict` = run only on the listed nodes.
- The replica is a **relocation enabler, not the durability layer**: the app
  guests' real data-loss window is covered separately (`postgres-apps` by
  streaming replication + WAL archiving; `nautobot`/`vikunja` are near-stateless
  — their state lives in `postgres-apps`).

Membership in `pve_ha_replication_ct_hostnames` is the per-guest "relocation is
viable" knob. A guest in `pve_ha_ct_hostnames` but not in the replication list
is treated as peer-redundant and gets no `pvesr` job.

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
This is read from `pvesh get /storage` (not a hand-rolled parse of
`/etc/pve/storage.cfg`), against each guest's volumes from
`pvesh get /nodes/<node>/lxc/<vmid>/config`. A storage entry with no `nodes`
restriction is treated as available on every node.

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
| `pve_ha_extra_sids` | `[]` | Verbatim extra SIDs (e.g. `vm:NNN`). |
| `pve_ha_anti_affinity_groups` | pairs | Redundant pairs to keep apart. |
| `pve_ha_max_restart` / `pve_ha_max_relocate` | `3` / `1` | Per-guest bounds. |
| `pve_ha_replication_ct_hostnames` | app list | Singleton guests that get a `pvesr` replica (relocation-enabled). |
| `pve_ha_replication_pair` | `[node-a, node-b]` | Always-on nodes; `pvesr` target is the member that is not the guest's home node. |
| `pve_ha_replication_schedule` | `*/15` | `pvesr` schedule (systemd-calendar subset). |
| `pve_ha_replication_rate` | `""` | `pvesr` rate limit in MB/s; empty = unlimited. |
| `pve_ha_replication_jobnum` | `0` | Job-number suffix in the `<vmid>-<jobnum>` job id. |
| `pve_ha_replication_affinity_rule` | `apps-replication-nodes` | Name of the strict node-affinity rule pinning replication guests to the pair. |
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
