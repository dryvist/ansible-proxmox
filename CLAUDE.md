# Ansible Proxmox

Configure the Proxmox VE host itself (not applications).

## This Repo Owns

- Kernel tuning (vm.swappiness, hugepages)
- ZFS swap configuration
- System ulimits
- Proxmox monitoring (healthchecks)
- Crash diagnostics
- Common system packages
- ZFS dataset realization, quotas, and NFS exports (`zfs_pools`), including the
  generic engine-/tier-agnostic `<pool>/databases` namespace (datasets declared
  in `terraform-proxmox` `node_storage`; convention in `roles/zfs_pools/README.md`)
- Local snapshots + cross-node replication (`sanoid` / `syncoid`)
- SQLite warm-standby archival (`sqlite_standby`) — one consumer of the
  databases namespace

## Pipeline Role

This repo has **no direct pipeline role**. It ensures
the Proxmox host is stable and properly configured so
that VMs/containers (managed by other repos) can run
reliably.

Firewall rules for pipeline ports (1514-1518, 8088, 2055) are managed by `terraform-proxmox/modules/firewall/`.

## Required Environment Variables

| Variable                  | Purpose                                          |
| ------------------------- | ------------------------------------------------ |
| `PROXMOX_VE_HOSTNAME`     | Proxmox VE hostname                              |
| `PROXMOX_VM_SSH_USERNAME` | SSH user for Proxmox host                        |
| `PROXMOX_SSH_PRIVATE_KEY` | SSH private key (used by scripts/run-ansible.sh) |
| `HEALTHCHECK_PING_KEY`    | Healthchecks.io key                              |

`scripts/run-ansible.sh` writes `PROXMOX_SSH_PRIVATE_KEY` to a temp file
and exports `ANSIBLE_PRIVATE_KEY_FILE` pointing to it.

## Commands

```bash
# Via run script (handles SSH key from env)
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml

# Or directly
doppler run -- ansible-playbook \
  -i inventory/hosts.yml playbooks/site.yml

# Dry run
doppler run -- ansible-playbook \
  -i inventory/hosts.yml playbooks/site.yml \
  --check --diff

# Lint
ansible-lint
```

## Dev Environment

This repo uses [Nix flakes](https://wiki.nixos.org/wiki/Flakes) + [direnv](https://direnv.net/) for a reproducible dev environment.

### Activation

```sh
direnv allow    # one-time per worktree — auto-activates on cd
```

### Manual activation

```sh
nix develop
```

### Tools provided

- ansible, ansible-lint, molecule — configuration management
- sops, age — secrets management
- python3 with paramiko, pyyaml, jinja2, jsondiff — Ansible dependencies
- jq, yq, pre-commit — utilities

## Related Repositories

| Repo                 | Relationship                    |
| -------------------- | ------------------------------- |
| terraform-proxmox    | Peer: provisions VMs/containers |
| ansible-proxmox-apps | Peer: configures apps on VMs    |
| ansible-splunk       | Peer: configures Splunk on VM   |
