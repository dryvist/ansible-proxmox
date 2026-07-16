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

### Internal Services

- **OpenBao**: native secret paths, including RustFS inventory credentials

### Infrastructure

- Physical Proxmox VE cluster (not provisioned by OpenTofu)

### Upstream inventory (read-only consumer)

The `tofu-proxmox` Terrakube workspace provisions the hosts and publishes the inventory this repo
consumes (`playbooks/load_tofu.yml`). This repo **never reads `deployment.json`**;
the published inventory is the source of truth, fetched fresh with no
authoritative local copy. The upstream desired-state's ACID single-writer
contract is documented once at
[Deployment state contract](https://docs.jacobpevans.com/infrastructure/deployment-state-contract).

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
> (`playbooks/load_tofu.yml`) runs on `hosts: localhost` and populates the
> dynamic inventory via `add_host`. Running with `--limit <group>` but **not**
> `localhost` silently skips the loader, so no hosts are added and every play
> reports "no hosts matched". Use `--limit <group>,localhost`, or invoke via
> `scripts/run-ansible.sh`, which appends `localhost` automatically.

### Execution Performance & Optimization

Ansible runs against the Proxmox hosts can be slow due to connection latency and fact-gathering serialization. To increase speed:

1. **Parallel Execution (`--forks` or `ANSIBLE_FORKS`)**: Increase the
   concurrency from the default 5 hosts at once. Using `25` forks (e.g.
   `doppler run -- ansible-playbook ... --forks 25`) runs significantly
   faster across large fleets.
2. **Targeted Runs (`--limit`)**: Restrict play scope to the target hosts and localhost (e.g., `--limit pve-nodes,localhost`).
3. **Scoping via Tags (`--tags`)**: Use `--tags <tag-name>` to run only a subset of roles.
4. **Disable Fact Gathering**: Set `gather_facts: false` on ad-hoc plays where facts are not required to bypass the setup step.

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

- \*_tofu-proxmox_: VM/container provisioning
- **ansible-proxmox-apps**: Application deployment on VMs
- \*_ansible-splunk_: Splunk configuration
