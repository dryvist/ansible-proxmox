# nas_storage

Serves already-existing ZFS datasets over Samba, from the per-node
`node_storage` contract: declarative shares, a Unix/Samba group, and managed
Samba users.

## What it does NOT do

It does **not** create datasets, set quotas, or manage mountpoints. `zfs_pools`
owns those, from the same `node_storage` declaration these shares are derived
from — so a share can only ever name a dataset that already exists. Two roles
both creating datasets is how the previous global contract produced an
identical `rpool/data/nas` on every node.

## What it does

1. Creates the Unix group and each declared share's directory
2. Installs Samba plus client/admin tooling
3. Manages declarative Samba-backed service accounts
4. Renders one config per declared share and validates with `testparm`
5. Stores a root-only password fingerprint so password rotation is idempotent

## Where shares are declared

Each share lives on the dataset it serves, and the node-level Samba *service*
settings sit beside the pools:

```hcl
node_storage = {
  <node> = {
    smb = {                       # service settings for this node
      group_name      = "nas"
      workgroup       = "WORKGROUP"
      macos_optimized = true
      managed_users   = [{ name = "...", password_secret_env = "..." }]
    }
    pools = {
      <pool> = {
        datasets = {
          <dataset> = {
            mountpoint = "/<pool>/<dataset>"
            smb = { share_name = "...", comment = "...", time_machine = false }
          }
        }
      }
    }
  }
}
```

The map key is the node selector — there is nothing further to select, and no
way to point a share at a dataset that does not exist. `playbooks/load_tofu.yml`
flattens this into `nas_storage_from_tofu`, filling each share's `name` from
`share_name` and its `path` from the dataset's `mountpoint` (falling back to
`/<pool>/<dataset>`).

A node that declares no `smb` block on any dataset receives nothing, and
`playbooks/site.yml` skips this role there. That is the normal case for most
nodes, not an error.

## Inputs

- The resolved OpenTofu inventory must contain `node_storage`
- Each managed user's `password_secret_env` must be readable from OpenBao

## Usage

```bash
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags nas_storage
```

## Role Variables

| Variable | Default | Description |
| --- | --- | --- |
| `nas_storage_config` | `node_storage.<node>` NAS projection | Injected by `playbooks/load_tofu.yml` |
| `nas_storage_group_name` | `nas` | Unix/Samba group for shared access |
| `nas_storage_smb_workgroup` | `WORKGROUP` | Samba workgroup |
| `nas_storage_managed_users` | `[]` | Declarative Samba-backed service accounts |
| `nas_storage_shares` | `[]` | Declarative Samba shares (no single-share fallback) |
| `nas_storage_macos_optimized` | `true` | Global vfs_fruit tuning for macOS Finder/Time Machine |
| `nas_storage_password_fingerprint_dir` | `/etc/samba/password-fingerprints` | Root-only password hash cache for idempotence |

## Apple clients (macOS, Time Machine, Infuse)

When `nas_storage_macos_optimized` is true (default), the global Samba config
enables `vfs_fruit` (`catia fruit streams_xattr` + `fruit:*` options) so macOS
Finder behaves correctly and shares can serve Time Machine. It is harmless for
non-Apple clients.

Per-share Apple options, set in the dataset's `smb` block:

| Share field | Effect |
| --- | --- |
| `time_machine: true` | Adds `fruit:time machine = yes` — the share becomes a Time Machine target |
| `time_machine_max_size: "600G"` | **Required** when `time_machine` is true. Time Machine grows until the volume is full, so an uncapped target eventually consumes the whole pool and takes every other dataset on it down with it. The tofu schema rejects the uncapped case |
| `read_only: true` | A read-only media share — e.g. for **Infuse** on Apple TV / iPhone to play directly over SMB alongside Plex |

Spotlight *search* over SMB additionally requires a server-side indexer
(Tracker/Elasticsearch) and is out of scope; Finder browsing and metadata work
with `vfs_fruit` alone.

## Notes

- Every optional share attribute is null-safe. Terraform serialises an
  undeclared `optional(...)` as an explicit `null`, and Jinja's `is defined` is
  **true** for null — so the templates test truthiness. Testing definedness
  renders `comment = None` into `smb.conf`, which is a silently wrong share
  rather than a missing one. `molecule/nas_storage` pins this with an
  all-nulls share fixture.
- systemd tasks are skipped in Docker containers (molecule testing)
- `smbpasswd` is fully managed by Ansible; no post-run manual steps are required
