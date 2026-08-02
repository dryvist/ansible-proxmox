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

| Component              | What It Does                                   |
| ---------------------- | ---------------------------------------------- |
| **Common Packages**    | Installs utilities: htop, iotop, lm-sensors    |
| **ZFS Swap**           | Creates optimized swap on ZFS                  |
| **Kernel Tuning**      | Optimizes memory and disk settings             |
| **System Limits**      | Increases file and process limits              |
| **Crash Diagnostics**  | System crash diagnostics configuration         |
| **LXC Features**       | LXC container feature flags (fuse, nesting)    |
| **Proxmox Monitoring** | Sets up historical monitoring (sysstat, atop)  |
| **NAS Storage**        | Declarative ZFS + Samba NAS for Home Assistant |

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
ansible-galaxy install -r requirements.yml
cp inventory/hosts.yml.example inventory/hosts.yml
# Edit inventory/hosts.yml with your server details
```

### Inventory resolution

This project consumes a host inventory produced by an upstream
infrastructure-provisioning step. The contract is a single JSON document
containing OpenTofu outputs (such as `host_services`, `node_storage`, and
`containers`); `playbooks/load_tofu.yml` resolves it at run time, in priority
order (first that resolves wins):

1. `TOFU_INVENTORY_PATH` — an explicit local file (pin / override, e.g. tests).
2. **RustFS published artifact** — the inventory JSON published by the
   tofu-proxmox Terrakube workspace. The shared resolver fetches it over the
   homelab network with credentials read directly from OpenBao
   `secret/platform/object-storage`; only `BAO_ADDR` and `BAO_TOKEN` are needed.
   Override the object with `TOFU_INVENTORY_S3_URI` when required.

There is no third source — see the
[role README](https://github.com/dryvist/homelab-contracts/tree/main/ansible/roles/inventory_resolve),
which is canonical for the order.

The artifact is expected to already exist in RustFS; provisioning and
publishing it is outside this repo's scope.

Create the SOPS secrets file:

```bash
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

The play deliberately does NOT import `load_tofu.yml` — that loader is
NAS-focused and would block commissioning. Run `playbooks/site.yml` after
commissioning if you need NAS provisioning.

Rack-server group defaults live in `inventory/group_vars/rack_servers.yml`;
per-host settings (real IPs, BMC addresses, expected hardware) live in
`inventory/host_vars/<node>.yml` (untracked). See
`inventory/host_vars/rack-server.yml.example` for the schema.

### Upgrading a node to the latest point release (PVE 9.x)

`playbooks/upgrade.yml` brings a node to the current point release on its
channel (`apt full-upgrade`), then reboots for the new kernel and verifies
`pveversion`. It first imports `playbooks/snapshot.yml`, which snapshots the
ZFS root (boot environment) dataset as a restore point — instant and near-zero
space. An OS upgrade does not touch guest disks (separate datasets), so the
root snapshot, not a guest backup, is the right rollback artifact. It then
applies the `pve_repositories` role, which keeps the node on the
no-subscription channel (deb822 `.sources`, enterprise repo disabled) without
touching the Debian base repos. If `pve_repositories_apt_proxies` is non-empty
(real URLs injected via the `APT_PROXY_URL` env var, e.g. apt-cacher-ng
instances — several accepted, separated by commas and/or whitespace), apt
`http://` fetches are routed through the first one that answers, or straight to
upstream when none does. The selection is apt's own
`Acquire::http::Proxy-Auto-Detect` hook, because apt accepts exactly one
`Acquire::http::Proxy` value and a pair cannot be expressed as config. Run it
with console access available; the node reboots.

```bash
# Test (snapshot and reboot are skipped in check mode):
./scripts/run-ansible.sh playbooks/upgrade.yml -l pve --check --diff

# Apply:
./scripts/run-ansible.sh playbooks/upgrade.yml -l pve
```

`playbooks/snapshot.yml` is also runnable on its own. If a node's root layout
differs from the `rpool/ROOT/pve-1` default, override `pve_snapshot_dataset`.
The upgrade assumes the node already has working apt repos for its channel
(`apt update` fails loudly otherwise). To upgrade now and reboot later, pass
`-e pve_upgrade_reboot=false`. Roll back a bad upgrade from a rescue boot with
`zfs rollback <snapshot>`.

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
OpenTofu inventory loading check:

```bash
# Run the default scenario
ANSIBLE_ALLOW_BROKEN_CONDITIONALS=1 molecule test

# Run the NAS-focused scenario
ANSIBLE_ALLOW_BROKEN_CONDITIONALS=1 molecule test -s nas_storage

# Verify OpenTofu inventory loading locally
TOFU_INVENTORY_PATH=$PWD/tests/inventory_load/tofu_inventory.json \
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

| Metric              | Manual Setup       | With Ansible    |
| ------------------- | ------------------ | --------------- |
| Time per server     | 30-60 min          | 2-5 min         |
| Consistency         | Variable           | 100% identical  |
| Documentation       | In your head       | In the code     |
| Disaster recovery   | Start from scratch | Re-run playbook |
| Onboarding new team | Shadow someone     | Read the code   |

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

[lint-badge]: https://github.com/JacobPEvans/ansible-proxmox/actions/workflows/ansible-lint.yml/badge.svg
[lint-url]: https://github.com/JacobPEvans/ansible-proxmox/actions/workflows/ansible-lint.yml
[molecule-badge]: https://github.com/JacobPEvans/ansible-proxmox/actions/workflows/molecule.yml/badge.svg
[molecule-url]: https://github.com/JacobPEvans/ansible-proxmox/actions/workflows/molecule.yml
[ansible]: https://www.ansible.com/
[proxmox]: https://www.proxmox.com/
[ansible-install]: https://docs.ansible.com/ansible/latest/installation_guide/
[molecule]: https://docs.ansible.com/projects/molecule/

---

> Part of a [larger ecosystem of ~40 repos](https://docs.jacobpevans.com) — see how it all fits together.
