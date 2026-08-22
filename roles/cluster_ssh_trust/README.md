# cluster_ssh_trust

Keeps inter-node **root SSH** working automatically across the Proxmox cluster
by seeding each node's `/root/.ssh/known_hosts` with the **current** host keys
of every cluster peer. Without this, root SSH between nodes (syncoid
replication, `pvecm`, live migration) fails with *Host key verification failed*
after a node rename or reinstall — exactly what happened when `pve` was renamed
to `node-a`.

## Installation

This role ships in the `ansible-proxmox` repository and is applied via
`playbooks/site.yml`. No separate installation is required beyond cloning the
repo and installing collection dependencies:

```bash
git clone https://github.com/dryvist/ansible-proxmox.git
cd ansible-proxmox
ansible-galaxy install -r requirements.yml
```

## What it does

- Runs `ssh-keyscan` for each peer in `cluster_ssh_trust_peers` and merges the
  keys into `/root/.ssh/known_hosts`, de-duplicated.
- Peers come from the **`PROXMOX_VE_NODES`** Doppler variable — the single
  source of truth for the cluster node list, shared by terraform and ansible
  (e.g. `node-a,node-b,node-c`). The value is tokenised with `regex_findall`, so plain
  comma-separated, bracketed (`[node-a, node-b]`), or quoted forms all work. When the
  variable is absent (e.g. molecule), it falls back to the `pve_cluster_members`
  inventory group.
- Idempotent: re-runs only report `changed` when a new/rotated key is added.
- Skipped under Docker so molecule can converge.

## Variables

| Variable | Default | Description |
| --- | --- | --- |
| `cluster_ssh_trust_enabled` | `true` | Master enable |
| `cluster_ssh_trust_peers` | from `PROXMOX_VE_NODES` (fallback: `pve_cluster_members`) | Hosts whose keys to trust |

## Usage

```bash
# Applied automatically as part of site.yml; or target it directly:
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags cluster_ssh_trust
```

## Scope / follow-up

This is the **interim** automation. Full per-host, generated-at-instantiation,
encrypted-in-inventory, rotatable SSH **key** management (replacing the single
shared Ansible key) is tracked as a separate design effort. This role only
manages `known_hosts` trust, not the keypairs themselves.
