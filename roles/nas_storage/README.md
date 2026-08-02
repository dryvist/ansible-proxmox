# nas_storage

Provisions the Proxmox host NAS end to end from the OpenTofu `host_services.nas`
contract: ZFS dataset, directory permissions, declarative Samba shares, and managed
Samba users.

## What it does

1. Creates or repairs the NAS ZFS dataset, mountpoint, and quota
2. Creates `/mnt/nas`, managed subdirectories, and any declared share paths
3. Installs Samba plus client/admin tooling
4. Manages a Unix group plus declarative Samba-backed service accounts
5. Renders one share config per declared share and validates config with `testparm`
6. Stores a root-only password fingerprint so Samba password rotation is idempotent

## Installation

This role is included in the `ansible-proxmox` repository and applied via `playbooks/site.yml`.
No separate installation is required.

## Inputs

- The resolved OpenTofu inventory must contain `host_services.nas`
- `NAS_HOMEASSISTANT_SMB_PASSWORD` must be exported for the managed Home Assistant user

## Usage

```bash
sops exec-env secrets.sops.yml 'doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags nas_storage --check'
sops exec-env secrets.sops.yml 'doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags nas_storage'
```

Validate the live NAS after deploy:

```bash
sops exec-env secrets.sops.yml 'doppler run -- ./scripts/run-ansible.sh playbooks/validate-nas.yml'
```

## Role Variables

| Variable | Default | Description |
| --- | --- | --- |
| `nas_storage_config` | OpenTofu host_services.nas | Source config injected by `playbooks/load_tofu.yml` |
| `nas_storage_group_name` | `nas` | Unix/Samba group for shared access |
| `nas_storage_managed_users` | `[]` | Declarative Samba-backed service accounts |
| `nas_storage_shares` | single `nas` share fallback | Declarative Samba shares |
| `nas_storage_macos_optimized` | `true` | Global vfs_fruit tuning for macOS Finder/Time Machine |
| `nas_storage_password_fingerprint_dir` | `/etc/samba/password-fingerprints` | Root-only password hash cache for idempotence |

## Apple clients (macOS, Time Machine, Infuse)

When `nas_storage_macos_optimized` is true (default), the global Samba config
enables `vfs_fruit` (`catia fruit streams_xattr` + `fruit:*` options) so macOS
Finder behaves correctly and shares can serve Time Machine. It is harmless for
non-Apple clients.

Per-share Apple options (set on a share in the `host_services.nas.shares`
contract):

| Share field | Effect |
| --- | --- |
| `time_machine: true` | Adds `fruit:time machine = yes` — the share becomes a Time Machine target |
| `time_machine_max_size: "1T"` | Optional per-share Time Machine quota |
| `read_only: true` | A read-only media share — e.g. for **Infuse** on Apple TV / iPhone to play directly over SMB alongside Plex |

Spotlight *search* over SMB additionally requires a server-side indexer
(Tracker/Elasticsearch) and is out of scope; Finder browsing and metadata work
with `vfs_fruit` alone.

## Notes

- ZFS and systemd tasks are skipped in Docker containers (molecule testing)
- Password values are read from environment variables populated by `sops exec-env`
- `smbpasswd` is fully managed by Ansible; no post-run manual steps are required
