# lxc_gpu_features

Binds GPU device nodes (AMD `/dev/dri`/`/dev/kfd`, NVIDIA `/dev/nvidia*`) into
GPU LXC containers over native `root@pam` SSH, idempotently. Companion to
`media_lxc_features`.

## Installation

This role ships with the `ansible-proxmox` repository — no external install. It
is wired into `playbooks/site.yml` (after `media_lxc_features`) and runs against
the `proxmox` host group. Service → VMID resolution is injected by
`playbooks/load_tofu.yml` from `tofu_inventory.json`, so the role must
run after that play (already imported first by `site.yml`). Tools come from the
repo's Nix dev shell (`direnv allow`); no `pip`/`galaxy` step is required.

## Why this role exists (the contract split)

The BPG Proxmox provider's API token **cannot** set arbitrary device
passthrough — Proxmox restricts `lxc.cgroup2.devices.allow` / `lxc.mount.entry`
to `root@pam` _ticket_ auth, so the token gets HTTP 403. So `tofu-proxmox`
creates the GPU LXC as a plain **shell**, and this role applies the device
lines. Identical split to `media_lxc_features` (which passes `/dev/net/tun` to
the download-vpn LXC).

## Ordering

1. `tofu-proxmox` — creates the GPU LXC as a privileged shell.
2. **this role** — binds the device nodes a service asks for in
   `lxc_gpu_features_map` (`/dev/dri` + `/dev/kfd` for an AMD compute service,
   `/dev/nvidia*` for a legacy NVIDIA service). Engine-identified NVIDIA guests
   are derived from the published Tofu inventory, reboots on change.
3. `ansible-proxmox-apps` (role `llama_cpp`) — installs llama.cpp + llama-swap
   and the matching GPU userspace (ROCm or CUDA/Vulkan), adds the service user
   to the needed groups, stages the GGUF models.

## What it writes

Manages these raw lines in `/etc/pve/lxc/<vmid>.conf`, one per `lineinfile` — Proxmox
relocates raw `lxc.*` keys to EOF, so marker-guarded blocks can't manage them idempotently:

```text
lxc.cgroup2.devices.allow: c 226:* rwm
lxc.mount.entry: /dev/dri dev/dri none bind,optional,create=dir
lxc.cgroup2.devices.allow: c 235:* rwm
lxc.mount.entry: /dev/kfd dev/kfd none bind,optional,create=file
```

## Feature sources

| Var                                       | Default             | Purpose                                           |
| ----------------------------------------- | ------------------- | ------------------------------------------------- |
| `lxc_gpu_features_map`                    | legacy service map  | Service → device groups                          |
| `lxc_gpu_features_nvidia_guest_features`   | NVIDIA device set   | Shared device set for engine-identified guests   |
| `lxc_gpu_features_service_vmids`           | from Tofu inventory | Service → current vmid                            |
| `lxc_gpu_features_engine_vmids_from_tofu`  | from Tofu inventory | Engine identity → current vmid                     |
| `lxc_gpu_features_legacy_engine_vmids_from_tofu` | from Tofu inventory | Legacy guest to stop after the replacement pair is declared |
| `lxc_gpu_features_engine_handoff_pre_stop` | `false` | Explicitly stop GPU guests before a selector-changing Tofu apply |
| `lxc_gpu_features_engine_handoff_vmids_from_tofu` | from Tofu inventory | Legacy and engine GPU guest candidates for that pre-stop |
| `lxc_gpu_features_dri_major`               | `226`               | `/dev/dri` char major                              |
| `lxc_gpu_features_kfd_major`               | `235`               | `/dev/kfd` char major                              |

VMIDs are resolved at run time from the published inventory, so renumbering a
guest needs no service-to-VMID edit here. Engine guests use their immutable
engine identity, not a second hard-coded service name.

## Idempotency & guards

Each raw line is managed with `lineinfile` (idempotent by exact match,
position-agnostic), and the handler reboots **only** changed containers, so a
converged host does nothing. Acts only on vmids actually present (`pct list`);
the handler reads each changed guest's status and reboots only guests that are
running. When Tofu publishes the replacement pair, the role logs and gracefully
stops the same-node legacy GPU guest before changing passthrough. For an engine
switch, set `lxc_gpu_features_engine_handoff_pre_stop=true` for a pre-apply
host-role run; it gracefully stops every legacy/engine GPU guest candidate
present on the limited host, so drift cannot leave another candidate owning
the device. This operation is opt-in, works only on present VMIDs, and never
force-stops or destroys a guest. All `pct` tasks are skipped under Docker
virtualization (molecule), and the role is a no-op when inventory resolves no
GPU services.

## Usage

```bash
# Dry run
./scripts/run-ansible.sh playbooks/site.yml --limit <node> --tags lxc_gpu_features --check --diff

# Apply (after tofu creates the LXC shell, before apps converge)
./scripts/run-ansible.sh playbooks/site.yml --limit <node> --tags lxc_gpu_features
```

Verify the devices landed inside the container (substitute the vmid the tofu
inventory resolved for the service):

```bash
pct exec <vmid> -- ls -l /dev/dri /dev/kfd       # an AMD compute service
pct exec <vmid> -- ls -l /dev/nvidia*            # an NVIDIA service
```
