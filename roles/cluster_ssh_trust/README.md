# cluster_ssh_trust

Keeps inter-node **root SSH** working automatically across the Proxmox cluster
by seeding each node's `/root/.ssh/known_hosts` with the **current** host keys
of every cluster peer. Without this, root SSH between nodes (syncoid
replication, `pvecm`, live migration) fails with *Host key verification failed*
after a node rename or reinstall — exactly what happened when `pve` was renamed
to `pve1`.

## Installation

This role ships in the `ansible-proxmox` repository and is applied via
`playbooks/site.yml`. No separate installation is required beyond cloning the
repo and installing collection dependencies:

```bash
git clone https://github.com/dryvist/ansible-proxmox.git
cd ansible-proxmox
ansible-galaxy collection install -r requirements.yml
```

## What it does

- Runs `ssh-keyscan` for each peer in `cluster_ssh_trust_peers` (default: the
  `pve_cluster_members` inventory group, which resolves via the PVE cluster's
  `/etc/hosts`) and merges the keys into `/root/.ssh/known_hosts`, de-duplicated.
- Idempotent: re-runs only report `changed` when a new/rotated key is added.
- Skipped under Docker so molecule can converge.

## Variables

| Variable | Default | Description |
| --- | --- | --- |
| `cluster_ssh_trust_enabled` | `true` | Master enable |
| `cluster_ssh_trust_peers` | `pve_cluster_members` names | Hosts whose keys to trust (names/IPs/FQDNs) |

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
