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
   that mount, and resolves it to a real host filesystem path with
   `pvesm path` — the same native resolution
   `roles/pve_guest_evacuation_lxc_managed_volumes` already uses, because a
   managed mount_point's real backing dataset name only exists once Proxmox
   allocates it; it cannot be derived from the desired state alone.
3. For every model in `llm_model_store_seed_models`, resolves its sha256 from
   HuggingFace's own LFS blob metadata at the model's pinned `hf_revision`,
   then fetches the GGUF with `ansible.builtin.get_url` and `checksum:` —
   idempotent (skipped once the destination already matches) and atomic
   (get_url writes to a temp file next to `dest` and moves it into place, so
   a concurrent reader through the guest's own ro bind mount never sees a
   partial file).

## Model catalog — a known, flagged duplicate

`llm_model_store_seed_models` (`defaults/main.yml`) mirrors
dryvist/ansible-proxmox-ai's `llama_cpp_models` declarations. It is a
deliberate, documented duplicate, not a second source of truth by accident:
the two repos are separate Ansible inventories with no automatic variable
sharing, and there is no cross-repo-published registry to read instead
today. `tests/llm_model_store_seed/test_model_catalog_contract.py` pins the
known upstream list and fails if this catalog drops an entry, so drift is
loud rather than silent. See the comment block at the top of
`defaults/main.yml` for the recommended single-source fix
(a shared catalog role in dryvist/homelab-contracts, alongside its existing
`cribl_edge`/`cribl_packs` precedent) — not done in the PR that introduced
this role.

Each entry's `hf_revision` is the one Renovate-tracked var per model
(`git-refs` datasource against the model's own HuggingFace git repo — see
this repo's `renovate.json`). Bump it, and the sha256 + download both follow
automatically at the next converge; nothing else in this role changes.

## Installation

No separate install step: this role ships in this repo's `roles/` and is
already wired into `playbooks/site.yml` against the `proxmox` group, after
`zfs_pools`/`nas_storage` (the backing volume must already exist).

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
| `llm_model_store_seed_models` | see `defaults/main.yml` | Declared `{name, hf_repo, gguf, hf_revision}` catalog |
| `llm_model_store_seed_timeout` | `3600` | Seconds allowed for the HF metadata lookup and the GGUF download |
| `llm_model_store_seed_file_mode` | `"0644"` | Mode of a seeded GGUF file |
