# media_lxc_features

Applies the **root-only LXC features** for the media stack that the BPG Proxmox
Terraform provider's **API token cannot set**: host bind-mounts (`mp`), the
`keyctl` feature, and `/dev/net/tun` device passthrough. Proxmox restricts all
three to `root@pam` **ticket** authentication, so a BPG API token receives HTTP
403. This role does them natively as `root` over SSH, idempotently.

## Installation

This role ships in the `ansible-proxmox` repository and is applied via
`playbooks/site.yml`. No separate installation is required beyond cloning the
repo and installing collection dependencies:

```bash
git clone https://github.com/dryvist/ansible-proxmox.git
cd ansible-proxmox
ansible-galaxy collection install -r requirements.yml
```

## Why this role exists (the contract split)

`terraform-proxmox` creates the media LXCs as **plain shells**. The root-only
bits are deliberately removed from Terraform because the API token cannot apply
them. This role realizes them after creation.

| Layer | Owns |
| --- | --- |
| terraform-proxmox | Create the media LXCs (CPU, RAM, disk, network, `nesting`) |
| **this role** | Bind-mounts (`mp`), `keyctl` (merged), `/dev/net/tun` passthrough |
| ansible-proxmox-apps | Converge the services inside each LXC |

`nesting=1` stays **Terraform-managed**. This role never drops it: `keyctl=1` is
**merged** into the live `features` string (existing tokens preserved), not
written wholesale.

## Ordering

```text
terraform-proxmox (shells)  ->  media_lxc_features  ->  ansible-proxmox-apps
```

Run this role **after** the LXCs exist and **before** the apps converge. In
`playbooks/site.yml` it runs after `lxc_features` and after `zfs_pools` (the
bind-mount sources are ZFS datasets under `/rpool/data`).

## Feature map (keyed by service, not VMID)

Non-secret, committed in `defaults/main.yml` as `media_lxc_features_map`, keyed
by **service name**. Each service's bind-mounts / keyctl / tun follow the
service, never a hardcoded VMID:

| service | bind-mounts (host -> container) | keyctl | /dev/net/tun |
| --- | --- | --- | --- |
| plex | `/rpool/data/media`->`/mnt/media` | no | no |
| jellyseerr | (none) | yes | no |
| sonarr | `/rpool/data/downloads`->`/mnt/downloads`, `/rpool/data/media`->`/mnt/media` | no | no |
| radarr | `/rpool/data/downloads`->`/mnt/downloads`, `/rpool/data/media`->`/mnt/media` | no | no |
| download-vpn | `/rpool/data/downloads`->`/mnt/downloads`, `/rpool/data/media`->`/mnt/media` | yes | yes |

All bind-mounts are **read-write** (no `ro=1`), matching the live deployment.
`/dev/net/tun` is char device **10:200** (verified on pve1).

### VMID resolution (renumber-proof)

The role never names a raw VMID. `playbooks/load_terraform.yml` projects the
terraform inventory's `containers` (keyed by service hostname, each with a
`vmid`) into `media_lxc_features_service_vmids_from_terraform` —
`{ service: vmid }` — and injects it onto each proxmox host. The role joins its
service-keyed feature map against that resolution at run time to build the
effective `{ vmid: features }` it acts on. A VMID renumber therefore flows in
through `terraform_inventory.json` and needs **zero** changes here: each service
keeps its features and follows its new VMID automatically. Services absent from
the inventory resolve to nothing and are skipped.

## Idempotency

Every change is gated on a config diff read from `pct config` / the live
`.conf` file *before* acting:

- **Bind-mounts**: the desired `mpN: <src>,mp=<dst>[,ro=1]` string is compared
  against the current value of that `mpN` slot; `pct set --mpN` runs only on a
  miss or mismatch.
- **keyctl**: current `features` tokens are parsed, any `keyctl=*` dropped,
  `keyctl=1` appended, sorted; `pct set --features` runs only when the token set
  differs. Terraform-set `nesting=1` is preserved.
- **/dev/net/tun**: a marker-guarded `blockinfile` writes the two raw LXC lines
  to `/etc/pve/lxc/<vmid>.conf`; reports changed only on an actual edit.

A container is **restarted only if its config changed** (handler `pct reboot`,
notified by the mutating tasks). A fully converged host performs **zero**
restarts.

## Guards

- Only vmids resolved from `media_lxc_features_map` (service -> vmid via the
  terraform inventory) that are **actually present** on the host (per
  `pct list`) are touched — absent vmids (not yet created by Terraform), and
  services with no inventory vmid, are skipped silently.
- All tasks are skipped under Docker (`ansible_virtualization_type == 'docker'`)
  for molecule testing.

## Usage

```bash
# Dry run
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags media_lxc_features --check
# Apply (after terraform creates the LXCs, before apps converge)
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags media_lxc_features
```
