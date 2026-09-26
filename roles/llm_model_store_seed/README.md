# llm_model_store_seed

Populates the llm fabric's shared model-store mount(s)
(`var.llm_models_mount_path` in tofu-proxmox, `/var/lib/llm` by default) with
every declared GGUF, so a serving guest's converge-time
`roles/llama_cpp/tasks/main.yml` model-presence assert (dryvist/ansible-proxmox-ai)
finds the file rather than failing a converge on a manually-populated store.

## Why this runs here, not on the serving guest

The fabric's own convention is that a serving guest never downloads models —
it mounts the store read-only (tofu derives `read_only: true` for every
`llm_fast_container_ids` member's models mount; see
`modules/proxmox-stack/main.tf` in tofu-proxmox). Something has to write the
files from the other side of that mount, on the PVE host that actually owns
the backing volume, which is what this role does.

## What It Does

1. Reads the published OpenTofu inventory (`containers_from_tofu`, injected
   by `playbooks/load_tofu.yml`) and finds every container on **this** node
   that declares a `models_mount_path` — never a hand-written host or vmid
   list. A node with none does nothing.
2. For each match, reads the container's live LXC configuration
   (`pvesh get .../lxc/<vmid>/config`) to find the exact `mpN` entry backing
   that mount. If none exists yet — `mount_point` is in
   `modules/proxmox-container/main.tf`'s `ignore_changes` in tofu-proxmox
   (root@pam-only, so terraform never applies a `mount_points` addition to an
   already-created container) — attaches it natively from the inventory's
   `models_mount_storage`/`models_mount_size`/`models_mount_read_only`
   (`pct set --mpN <storage>:<size>,mp=<path>[,ro=1]`) at the next free `mpN`
   index, then restarts the container (reboot if running, start if stopped —
   `mpN` is a boot-time config key, not hotpluggable) so the guest itself
   sees the new mount. Same idiom `roles/media_lxc_features` already uses for
   its own root@pam-only mount changes.
3. Resolves the (now-live, either way) mount to a real host filesystem path
   with `pvesm path` — the same native resolution
   `roles/pve_guest_evacuation_lxc_managed_volumes` already uses, because a
   managed mount_point's real backing dataset name only exists once Proxmox
   allocates it; it cannot be derived from the desired state alone.
4. For every model in `llm_model_catalog_models`, resolves its sha256 from
   HuggingFace's own LFS blob metadata at the model's pinned `hf_revision`,
   then fetches the GGUF with `ansible.builtin.get_url` and `checksum:` —
   idempotent (skipped once the destination already matches) and atomic
   (get_url writes to a temp file next to `dest` and moves it into place, so
   a concurrent reader through the guest's own ro bind mount never sees a
   partial file).

## Model catalog

The model list is `llm_model_catalog_models`, from
`dryvist.homelab.llm_model_catalog` (dryvist/homelab-contracts) — the single
catalog shared with dryvist/ansible-proxmox-ai's `llama_cpp` role, which
serves the same GGUFs this role downloads. `playbooks/site.yml` includes that
role immediately before this one so the catalog is already in scope; this
role declares no model list of its own.

Each entry's `hf_revision` is the one Renovate-tracked var per model
(`git-refs` datasource against the model's own HuggingFace git repo — see
`dryvist/homelab-contracts`' `renovate.json`). Bumping it there and pulling
the resulting collection release is all that's needed for the sha256 and
download to follow at the next converge.

## Installation

Ships in this repo's `roles/` and is already wired into `playbooks/site.yml`
against the `proxmox` group, after `zfs_pools`/`nas_storage` (the backing
volume must already exist) and after `dryvist.homelab.llm_model_catalog`
(the model list). The catalog role comes from the `dryvist.homelab`
collection — see `requirements.yml`.

```bash
ansible-galaxy role list | grep llm_model_store_seed  # confirm it's present locally
```

## Usage

Runs with the rest of `site.yml`, or target just this role by tag:

```bash
doppler run -- ansible-playbook -i inventory/hosts.yml playbooks/site.yml \
  --limit proxmox,localhost --tags llm_model_store_seed
```

### Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `llm_model_catalog_models` | see `llm_model_catalog`'s defaults | Declared `{name, hf_repo, gguf, hf_revision}` catalog (not this role's own) |
| `llm_model_store_seed_timeout` | `3600` | Seconds allowed for the HF metadata lookup and the GGUF download |
| `llm_model_store_seed_file_mode` | `"0644"` | Mode of a seeded GGUF file |
