# pve_node_rename

Idempotently rename a **standalone** (pre-cluster) Proxmox VE node — hostname,
`/etc/hosts`, and the pmxcfs node directory under `/etc/pve` — and strip the
node's stale pre-rename identity addresses.

## When to use this

A node rename is **only safe while standalone**. Renaming a node that is already
part of a cluster corrupts pmxcfs and quorum (see ADR-0001 in `int_homelab`).
This role therefore **hard-refuses to run** when it detects corosync
configuration or a quorate corosync membership.

The homelab use case is the one-time `pve` → `pve1` rename, performed *before*
cluster formation (`pve_cluster` role), as part of moving the node's identity
from the legacy `net` VLAN onto the `compute` VLAN. The role itself is
host-agnostic.

## Installation

This role ships in the `ansible-proxmox` repository. No separate installation is
required beyond cloning the repo and installing collection dependencies:

```bash
git clone https://github.com/dryvist/ansible-proxmox.git
cd ansible-proxmox
ansible-galaxy collection install -r requirements.yml
```

## What it does

| Step | Action | Idempotence |
| --- | --- | --- |
| Preflight | Assert the node is standalone (no corosync) | Read-only gate |
| Hostname | `ansible.builtin.hostname` to the new name | Skipped when already set |
| `/etc/hosts` cleanup | Remove `pve_node_rename_stale_ips` lines | `lineinfile state=absent` |
| `/etc/hosts` rename | Replace old short name with new | Skipped when names equal |
| `/etc/hosts` identity | Ensure mgmt IP → renamed node line | Managed by `regexp` |
| pmxcfs | `mv /etc/pve/nodes/<old> <new>` | Only when src exists, dst absent |
| corosync | Fix single-node `nodename` if file present | Only when file references old name |

All pmxcfs / `/etc/pve` operations are skipped under Docker
(`ansible_virtualization_type == 'docker'`) so the role is molecule-testable in
containers.

## Inputs

No literal IPs are baked in — supply real addresses from inventory / SOPS /
Doppler.

```yaml
pve_node_rename_to: pve1                 # new node name (default)
pve_node_rename_from: "{{ ansible_hostname }}"  # defaults to live hostname
pve_node_rename_ip: "{{ ansible_host }}" # compute-VLAN mgmt IP for /etc/hosts
pve_node_rename_stale_ips: []            # old VLAN IP(s) to strip, e.g. the legacy net-VLAN address
pve_node_rename_fqdn: ""                 # optional FQDN for the /etc/hosts entry
pve_node_rename_force_when_clustered: false  # escape hatch; leave false
```

## Usage

```bash
# Dry run (rename tasks only)
doppler run -- ./scripts/run-ansible.sh playbooks/rename_node.yml --check --diff

# Apply — STANDALONE node only, take a snapshot first
doppler run -- ./scripts/run-ansible.sh playbooks/rename_node.yml
```

After applying, verify the API/UI shows the new node name and the old name is
gone from `pvecm nodes` / the node tree, then proceed to cluster formation.

## Safety

- Refuses to run on a clustered node (corosync detected).
- Every mutating step is guarded so a second run is a no-op.
- Takes no backups itself — snapshot the node before running.
