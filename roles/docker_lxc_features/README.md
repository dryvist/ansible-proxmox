# docker_lxc_features

Applies the root-only LXC features needed by AI-orchestration Docker guests:
`nesting=1,keyctl=1,fuse=1`.

The BPG Proxmox Terraform provider can create the shell, but Proxmox only lets
`root@pam` set `keyctl` and `fuse`, so this role finishes the container on the
host with `pct set`.

## Selection

The role resolves candidate containers from `containers_from_tofu`:

- any container tagged `docker` plus either `ai-orchestration` or
  `agentgateway` is selected
- `n8n` and `langgraph` remain explicit fallbacks until those tags are present

That keeps the role VMID-agnostic and lets a renumber flow through from tofu
inventory without editing the role.

## Ordering

Run after `playbooks/load_tofu.yml` has populated `containers_from_tofu`, and
before the app converge that needs Docker overlayfs inside the LXC.

## Idempotency

The role reads `pct config` first, compares the live `features:` tokens to the
desired set, and only issues `pct set` when `keyctl` or `fuse` are missing.
Changed containers are restarted with a stop/start handler only when config
actually changed.

## Usage

```bash
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --limit pve1,localhost --tags docker_lxc_features
```
