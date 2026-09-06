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

Every guest lands in exactly one of three classes — `application_ha`,
`immovable`, `singleton` — derived from data that already exists, so a
guest added later needs no edit to this role. Native application HA is
preferred over relocation. Full derivation rules, per-class behaviour on
crash/node-loss, the singleton replication contract, and which nodes a
strict rule may name: [docs/ha-classes.md](docs/ha-classes.md).

## Cluster shutdown policy

The role also owns `shutdown_policy` in the cluster-wide `/etc/pve/datacenter.cfg`
(default `freeze`, not `migrate`) — why unset is not neutral, why `migrate` is
only safe once every HA guest has a replica, and how the single key is merged
in place: [docs/shutdown-policy.md](docs/shutdown-policy.md).

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
