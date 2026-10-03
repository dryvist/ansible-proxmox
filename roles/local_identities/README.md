# local_identities

Create the named accounts that replace shared-`root` administration:

- The human operator has passwordless sudo and key-based SSH.
- **`admin`** — break-glass only. Created and sudo-capable, reachable
  **only** via the OpenBao SSH CA (no static key), so it is not a second
  standing door the way a static key would be.

## Installation

Ships in the `ansible-proxmox` repository; applied via `playbooks/site.yml`:

```bash
ansible-playbook playbooks/site.yml --limit pve-r540,localhost --tags local_identities
```

## Why this exists

The estate administers every Proxmox host as `root` today. That is not
removed here — this role is **additive**: it creates `jevans` and `admin` as
better paths, but root access (both the OpenBao CA `ansible` principal and
the static break-glass key managed by `root_authorized_keys`) stays intact.
Retiring direct root login is a deliberate, separate, later step once every
consumer — humans, Ansible, Terrakube — is confirmed working over the new
accounts.

`iac` (Terrakube) is deliberately **not** covered here: Terrakube reaches
Proxmox over its API (the BPG provider), not SSH, so there is no host
principal for it to hold.

## Usage

Run against every Proxmox node. Idempotent — safe to re-run.

## Variables

See `defaults/main.yml`. Key ones: `local_identities_jevans_ssh_public_key`
(reads `VM_SSH_PUBLIC_KEY`), and the `*_enabled` per-account toggles.

## Molecule

`molecule/local_identities/` — runs the full role (account creation, sudo,
key authorization) inside the test container; no Docker-skip guard is
needed since `useradd`/`visudo` work fine there.
