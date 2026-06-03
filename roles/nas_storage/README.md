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

- `inventory/tofu_inventory.json` must exist and contain `host_services.nas`
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
| `nas_storage_config` | OpenTofu host_services.nas | Source config injected by `inventory/load_tofu.yml` |
| `nas_storage_group_name` | `nas` | Unix/Samba group for shared access |
| `nas_storage_managed_users` | `[]` | Declarative Samba-backed service accounts |
| `nas_storage_shares` | single `nas` share fallback | Declarative Samba shares |
| `nas_storage_password_fingerprint_dir` | `/etc/samba/password-fingerprints` | Root-only password hash cache for idempotence |

## Notes

- ZFS and systemd tasks are skipped in Docker containers (molecule testing)
- Password values are read from environment variables populated by `sops exec-env`
- `smbpasswd` is fully managed by Ansible; no post-run manual steps are required
