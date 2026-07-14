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

Provided via Doppler (`doppler run -- …`). Grouped by purpose; not every
variable is needed for every playbook.

| Variable | Purpose |
| --- | --- |
| `PVE1_VE_HOSTNAME`, `PVE2_VE_HOSTNAME`, `PVE3_VE_HOSTNAME` | Per-node Proxmox hostnames resolved in `inventory/hosts.yml` |
| `PROXMOX_NODE_PREFIX` | Node-name prefix (without the trailing number) used to derive per-node identifiers |
| `PROXMOX_VM_SSH_USERNAME` | SSH user for the Proxmox hosts |
| `PROXMOX_SSH_KEY_PATH` *or* `PROXMOX_SSH_PRIVATE_KEY` | SSH auth: a key **file path**, or **contents** (loaded via `scripts/run-ansible.sh`) |
| `HEALTHCHECK_PING_KEY` | Healthchecks.io ping key (`proxmox_monitoring`, `sqlite_standby`) |
| `TOFU_INVENTORY_S3_URI` | S3 URI override for RustFS inventory; creds from OpenBao `secret/platform/object-storage` via `inventory_resolve` |
| `TOFU_INVENTORY_PATH`, `TOFU_INVENTORY_ALLOW_STALE` | Optional inventory overrides (pin a local file / permit a stale cache) |
| `IDRAC_USERNAME`, `IDRAC_PASSWORD`, `PVE3_BMC_HOSTNAME` | IPMI power control for the offline-DR node (`idrac_power`, `node_scheduled_wake`) |
| `PROXMOX_VE_HOSTNAME`, `PROXMOX_VE_NODES`, `PROXMOX_VE_USERNAME`, `PROXMOX_VE_TOKEN_ID`, `PROXMOX_VE_TOKEN_SECRET`, `PROXMOX_VE_INSECURE` | Proxmox token |
| `APT_PROXY_URL`, `NAS_HOMEASSISTANT_SMB_PASSWORD` | Optional: apt caching proxy; NAS Samba service account |

`scripts/run-ansible.sh` loads `PROXMOX_SSH_PRIVATE_KEY` into an in-memory
ssh-agent (the key never touches disk) and unsets it so Ansible authenticates via
the agent. If `PROXMOX_SSH_KEY_PATH` points to a real file, that file is used
directly instead.

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
