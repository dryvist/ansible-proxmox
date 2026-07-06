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

1. Places each tier-0 LXC under HA (`ha-manager add ct:VMID --state started
   --max_restart 3 --max_relocate 1`). VMIDs resolve from the tofu inventory by
   hostname, so a renumber flows through with no edit.
2. Adds `resource-affinity` **negative** rules so the two halves of each
   redundant pair never share a node.

Guests (default `pve_ha_ct_hostnames`): `openbao-01`, `openbao-02`,
`technitium-dns`, `technitium-dns-2`, `traefik`. Anti-affinity pairs
(`pve_ha_anti_affinity_groups`): the two OpenBao Raft voters, the two Technitium
DNS instances, and the Traefik ingress pair (the last auto-activates once
`traefik-2` exists). A pair whose members do not all resolve is skipped.

## Why anti-affinity is the real payload (and relocation is not)

These tier-0 guests sit on **local ZFS**, not shared storage, and each already
has a redundant PEER on another node (OpenBao Raft quorum, the second Technitium
instance, the keepalived VRRP VIP). So:

- On a **crash**, HA auto-restarts the guest in place (`max_restart`).
- On a **node loss**, the surviving PEER carries the service; the failed guest
  returns when its node heals. HA cannot start it on another node without the
  rootfs being there (PVE storage replication / `pvesr`), which is a tracked
  follow-up — deliberately **not** required for the node-loss story. Hence
  `max_relocate` is intentionally low.
- **Anti-affinity** is what keeps the redundancy real: it stops HA (or a manual
  migrate) from ever collapsing both peers onto one node.

With 4 quorate nodes, HA fencing is safe — losing one node keeps quorum, so no
surviving node self-fences.

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
