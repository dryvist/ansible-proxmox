# Ansible Proxmox - AI Agent Documentation

Ansible automation for Proxmox VE host configuration.

## Purpose

Configure the Proxmox VE hypervisor itself:

- Kernel parameters and tuning
- Swap configuration (including ZFS-backed swap)
- Host monitoring and metrics
- Process and file descriptor limits
- Crash diagnostics and troubleshooting data collection

This is for **host-level** configuration only. Application VMs are
configured by `ansible-proxmox-apps` and `ansible-splunk`.

## Dependencies

### External Services

- **Doppler**: SSH credentials and API tokens

### Infrastructure

- Physical Proxmox VE cluster (not provisioned by OpenTofu)

## Key Files

| Path                 | Purpose                     |
| -------------------- | --------------------------- |
| `playbooks/site.yml` | Main orchestration playbook |
| `roles/`             | Configuration roles         |
| `inventory/`         | Proxmox host inventory      |

## Agent Tasks

### Running Playbooks

```bash
doppler run -- ansible-playbook playbooks/site.yml
```

> **`--limit` must include `localhost`.** The inventory loader
> (`inventory/load_tofu.yml`) runs on `hosts: localhost` and populates the
> dynamic inventory via `add_host`. Running with `--limit <group>` but **not**
> `localhost` silently skips the loader, so no hosts are added and every play
> reports "no hosts matched". Use `--limit <group>,localhost`, or invoke via
> `scripts/run-ansible.sh`, which appends `localhost` automatically.

### Common Operations

- **Kernel tuning**: Updates sysctl parameters
- **Swap management**: Configures swappiness and ZFS swap devices
- **Monitoring setup**: Installs sysstat, atop, and crash-monitor

Note: All playbooks use `doppler run` to inject secrets (SSH credentials, API tokens) from your Doppler config.

## Development Environment

This repo uses [direnv](https://direnv.net/) with a Nix flake to automatically
activate the development shell. When you `cd` into the repo, direnv loads the
Nix development shell, providing ansible, ansible-lint, and other tools on PATH.

**Prerequisites:**

- [direnv](https://direnv.net/) installed
- [nix-direnv](https://github.com/nix-community/nix-direnv) installed (required for `use flake` support)

After cloning, run `direnv allow` to enable automatic shell activation.

## Related Repositories

- \*_terraform-proxmox_: VM/container provisioning
- **ansible-proxmox-apps**: Application deployment on VMs
- \*_ansible-splunk_: Splunk configuration
