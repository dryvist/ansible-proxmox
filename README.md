# Proxmox Ansible

[![Ansible Lint][lint-badge]][lint-url]
[![Molecule Test][molecule-badge]][molecule-url]

**Automate your Proxmox server setup in minutes instead of hours.**

## What This Does

This project uses [Ansible][ansible]—an industry-standard automation
tool—to configure [Proxmox VE][proxmox] servers automatically. Instead
of manually logging into each server and typing commands, you run one
command and all your servers are configured identically.

### The Problem It Solves

Setting up a Proxmox server properly takes time:

- Installing monitoring tools
- Configuring swap space for memory management
- Tuning kernel parameters for performance
- Setting system limits so applications don't crash

Doing this manually on one server takes 30-60 minutes. On multiple
servers? Hours of repetitive work, with the risk of human error making
each server slightly different.

### The Solution

Run a single command, and every server gets the same professional
configuration:

```bash
./scripts/run-ansible.sh playbooks/site.yml
```

**Time saved**: 30-60 minutes per server
**Consistency**: Every server configured identically
**Repeatability**: Add a new server? One command. Rebuild? One command.

## What Gets Configured

| Component              | What It Does                                        |
| ---------------------- | --------------------------------------------------- |
| **Common Packages**    | Installs utilities: htop, iotop, lm-sensors         |
| **ZFS Swap**           | Creates optimized swap on ZFS                       |
| **Kernel Tuning**      | Optimizes memory and disk settings                  |
| **System Limits**      | Increases file and process limits                   |
| **Crash Diagnostics**  | System crash diagnostics configuration              |
| **LXC Features**       | LXC container feature flags (fuse, nesting)         |
| **Proxmox Monitoring** | Sets up historical monitoring (sysstat, atop)       |
| **NAS Storage**        | Declarative ZFS + Samba NAS for Home Assistant      |

### Why Each Matters

- **Common Packages**: See what your server is doing at a glance
- **ZFS Swap**: Prevents out-of-memory crashes when VMs use too much RAM
- **Kernel Tuning**: Better performance for NVMe drives and VMs
- **System Limits**: Prevents "too many open files" errors under load

## Installation

Requires [Ansible][ansible-install] (Mac, Linux, WSL), SSH access to Proxmox server(s), and Proxmox VE 8.x.

```bash
git clone https://github.com/JacobPEvans/ansible-proxmox.git
cd ansible-proxmox
ansible-galaxy collection install -r requirements.yml
cp inventory/hosts.yml.example inventory/hosts.yml
# Edit inventory/hosts.yml with your server details
```

Sync the Terraform inventory and create the SOPS secrets file:

```bash
aws-vault exec tf-proxmox -- doppler run -- \
  terragrunt output -json ansible_inventory > inventory/terraform_inventory.json
cp secrets.sops.yml.example secrets.sops.yml
sops secrets.sops.yml
```

Set `NAS_HOMEASSISTANT_SMB_PASSWORD` in the secrets file before saving.

## Usage

Test the configuration (doesn't change anything):

```bash
sops exec-env secrets.sops.yml 'doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --check --diff'
```

Apply the configuration:

```bash
sops exec-env secrets.sops.yml 'doppler run -- ./scripts/run-ansible.sh playbooks/site.yml'
```

### Commissioning a new rack server (PVE 9.x)

Use `playbooks/commission_rack_server.yml` after a new rack server (Dell
PowerEdge, HPE ProLiant, Supermicro, etc.) has PVE 9.x installed via its
BMC's vKVM and has joined the cluster (`pvecm add`):

```bash
ansible-playbook -i inventory playbooks/commission_rack_server.yml -l node-a
```

The play deliberately does NOT import `load_terraform.yml` — that loader is
NAS-focused and would block commissioning. Run `playbooks/site.yml` after
commissioning if you need NAS provisioning.

Rack-server group defaults live in `inventory/group_vars/rack_servers.yml`;
per-host settings (real IPs, BMC addresses, expected hardware) live in
`inventory/host_vars/<node>.yml` (untracked). See
`inventory/host_vars/rack-server.yml.example` for the schema.

Wiring `terraform-proxmox`'s `rack_servers` output into Ansible host_vars
is a forward-looking enhancement — the existing `load_terraform.yml` only
injects the NAS `host_services` contract today.

## Customization

All settings have sensible defaults. Override them in
`inventory/group_vars/proxmox.yml`:

```yaml
# Swap size (default: 96GB - reduce for smaller systems)
zfs_swap_size: "32G"

# Kernel tuning (lower swappiness = prefer RAM over swap)
kernel_tuning_swappiness: 10

# System limits (increase for high-load applications)
ulimits_nofile: 65536
```

## Development Environment

This project uses [Nix flakes](https://wiki.nixos.org/wiki/Flakes) + [direnv](https://direnv.net/) for a reproducible dev environment.

Requires [Nix](https://nixos.org/download/) with flakes enabled and
[direnv](https://direnv.net/docs/installation.html) with [nix-direnv](https://github.com/nix-community/nix-direnv).

```sh
cd ~/git/ansible-proxmox/main    # or any worktree
direnv allow                     # one-time per worktree
```

Tools provided: `ansible`, `ansible-lint`, `molecule`, `sops`, `age`,
`python3` (with paramiko, jsondiff, pyyaml, jinja2), `jq`, `yq`, `pre-commit`.

## Testing

This project includes automated tests using [Molecule][molecule] plus a
Terraform inventory loading check:

```bash
# Run the default scenario
ANSIBLE_ALLOW_BROKEN_CONDITIONALS=1 molecule test

# Run the NAS-focused scenario
ANSIBLE_ALLOW_BROKEN_CONDITIONALS=1 molecule test -s nas_storage

# Verify Terraform inventory loading locally
cp tests/inventory_load/terraform_inventory.json inventory/terraform_inventory.json
TERRAFORM_INVENTORY_PATH=$PWD/inventory/terraform_inventory.json \
PROXMOX_VE_HOSTNAME=localhost PROXMOX_VM_SSH_USERNAME=root \
  ansible-playbook tests/inventory_load/verify_inventory.yml -i inventory/hosts.yml -c local
```

## For Developers

### Pre-commit Hooks

```bash
# pre-commit is provided by the Nix dev environment
pre-commit install
```

### Linting

```bash
ansible-lint
yamllint .
```

## Cost-Benefit Summary

| Metric              | Manual Setup       | With Ansible       |
| ------------------- | ------------------ | ------------------ |
| Time per server     | 30-60 min          | 2-5 min            |
| Consistency         | Variable           | 100% identical     |
| Documentation       | In your head       | In the code        |
| Disaster recovery   | Start from scratch | Re-run playbook    |
| Onboarding new team | Shadow someone     | Read the code      |

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

---

Generated by AI (Claude Opus 4.5 with Claude Code v2.1.4)

[lint-badge]: https://github.com/JacobPEvans/ansible-proxmox/actions/workflows/ansible-lint.yml/badge.svg
[lint-url]: https://github.com/JacobPEvans/ansible-proxmox/actions/workflows/ansible-lint.yml
[molecule-badge]: https://github.com/JacobPEvans/ansible-proxmox/actions/workflows/molecule.yml/badge.svg
[molecule-url]: https://github.com/JacobPEvans/ansible-proxmox/actions/workflows/molecule.yml
[ansible]: https://www.ansible.com/
[proxmox]: https://www.proxmox.com/
[ansible-install]: https://docs.ansible.com/ansible/latest/installation_guide/
[molecule]: https://docs.ansible.com/projects/molecule/
