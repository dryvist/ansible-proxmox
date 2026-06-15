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
bits are deliberately removed from OpenTofu because the API token cannot apply
them. This role realizes them after creation.

| Layer | Owns |
| --- | --- |
| terraform-proxmox | Create the media LXCs (CPU, RAM, disk, network, `nesting`) + declare the `bulk/data` and `bulk/appdata` datasets (`node_storage`) |
| **this role** | Bind-mounts (`mp`), `keyctl` (merged), `/dev/net/tun` passthrough, shared `media` group + `/bulk/data` directory skeleton, per-app config-mount ownership |
| ansible-proxmox-apps | Converge the services inside each LXC |

`nesting=1` stays **OpenTofu-managed**. This role never drops it: `keyctl=1` is
**merged** into the live `features` string (existing tokens preserved), not
written wholesale.

## Ordering

```text
terraform-proxmox (shells)  ->  media_lxc_features  ->  ansible-proxmox-apps
```

Run this role **after** the LXCs exist and **before** the apps converge. In
`playbooks/site.yml` it runs after `lxc_features` and after `zfs_pools` (the
bind-mount source is the `bulk/data` ZFS dataset, mounted at `/bulk/data`).

## Feature map (keyed by service, not VMID)

Non-secret, committed in `defaults/main.yml` as `media_lxc_features_map`, keyed
by **service name**. Each service's bind-mounts / keyctl / tun follow the
service, never a hardcoded VMID:

| service | bind-mounts (host -> container) | keyctl | /dev/net/tun |
| --- | --- | --- | --- |
| plex | `/bulk/data`->`/data`, `/bulk/appdata/plex`->`/var/lib/plexmediaserver` | no | no |
| seerr | (none) | yes | no |
| sonarr | `/bulk/data`->`/data` | no | no |
| radarr | `/bulk/data`->`/data` | no | no |
| download-vpn | `/bulk/data`->`/data` | yes | yes |

Every mounted service gets the unified `bulk/data` dataset -> `/data`. One
dataset (replacing the old separate `downloads` + `media` datasets/mounts) is
what lets qBittorrent and the *arrs **hardlink** between `/data/torrents/*` and
`/data/media/*` — hardlinks cannot cross dataset boundaries. All bind-mounts are
**read-write** (no `ro=1`), the role's existing convention (plex is read-mostly
by usage, not by mount flag). `/dev/net/tun` is char device **10:200** (verified
on pve1). Plex additionally gets a **persistent config mount** — see below.

A mount may carry `owner_user: <name>`. That marks an app-**private** config
dataset that must be owned by the app *user* (not the shared `media` group), and
the role chowns the host path to that user's mapped host uid/gid.

## Shared data root (host side)

The `bulk/data` **dataset** (recordsize, auto-snapshot, quota) is declared in
terraform-proxmox `node_storage` and realized by `zfs_pools`. This role owns
the **POSIX layer** inside it, on hosts where `/bulk/data` exists:

- the shared `media` group at a **fixed GID** (`13000` by default) — the path
  is bind-mounted into several LXCs, so each guest's `media` group must map to
  the same host GID;
- the subdirectory skeleton `torrents/{movies,tv}` + `media/{movies,tv}`,
  owner `root`, group `media`, mode `2775` (group-writable like the
  `nas_storage` directory convention, plus setgid so app-created content keeps
  the `media` group).

Hosts without the data root (no bulk pool, or `zfs_pools` not yet applied)
skip these tasks entirely; the role never invents a plain directory on the
root filesystem.

## Plex config persistence (`bulk/appdata/plex`)

Plex stores its **identity + state** — `Preferences.xml` (the
`machineIdentifier`, the plex.tv claim token, and the "publish to plex.tv" flag)
and the library database (watch history) — under `/var/lib/plexmediaserver`. On
a plain LXC that directory lives on the **disposable rootfs**, so a container
**rebuild** wipes it: Plex comes back as a *brand-new server* (new identity →
orphaned history + shares, a "sign in / set up again" prompt). To stop that, the
plex service bind-mounts the dedicated **`bulk/appdata/plex`** dataset over
`/var/lib/plexmediaserver`, so identity + history live **off the rootfs** and
survive any restart **or** rebuild.

- **Dataset**: `bulk/appdata` (parent) + `bulk/appdata/plex` are declared in
  terraform-proxmox `node_storage` and realized by `zfs_pools`. `bulk/appdata` is
  the home for app *config/state* (distinct from `bulk/databases`, which is for
  database engines, and `bulk/data`, the re-acquirable media library).
- **Snapshots + DR**: `bulk/appdata` gets the **`critical`** sanoid template
  (hourly point-in-time — right for constantly-changing watch progress) on pve2,
  and a recursive syncoid pull to pve3. Both are configured in host_vars and
  cover every `bulk/appdata/<app>` child.
- **Ownership**: the mount carries `owner_user: plex`. Plex's config is owned by
  the `plex` *user*; the container leaves its UID map at the default offset, so
  the role chowns the host dataset to `unpriv_base + <live in-container plex
  uid/gid>` (resolved per container; the ids are package-assigned, never
  hardcoded).
- **Fresh-build ordering caveat**: on a *from-scratch* shell this role runs
  **before** the apps converge installs Plex, so `id plex` does not resolve yet
  and the ownership chown is skipped (non-fatal). Run order on a new build is:
  `media_lxc_features` (mount) → apps converge (installs Plex) →
  `media_lxc_features` once more (ownership reconciles). The dataset **data** is
  never at risk — it lives outside the rootfs that the rebuild replaces.

`bulk/appdata/<app>` is the correct future home for the Sonarr / Radarr /
qBittorrent / Prowlarr configs too (same rootfs-only vulnerability) — add a
second mount with `owner_user: <app>` per service to extend it.

### VMID resolution (renumber-proof)

The role never names a raw VMID. `playbooks/load_tofu.yml` projects the
tofu inventory's `containers` (keyed by service hostname, each with a
`vmid`) into `media_lxc_features_service_vmids_from_tofu` —
`{ service: vmid }` — and injects it onto each proxmox host. The role joins its
service-keyed feature map against that resolution at run time to build the
effective `{ vmid: features }` it acts on. A VMID renumber therefore flows in
through `tofu_inventory.json` and needs **zero** changes here: each service
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
  differs. OpenTofu-set `nesting=1` is preserved.
- **/dev/net/tun**: a marker-guarded `blockinfile` writes the two raw LXC lines
  to `/etc/pve/lxc/<vmid>.conf`; reports changed only on an actual edit.

A container is **restarted only if its config changed** (handler `pct reboot`,
notified by the mutating tasks). A fully converged host performs **zero**
restarts.

## Guards

- Only vmids resolved from `media_lxc_features_map` (service -> vmid via the
  tofu inventory) that are **actually present** on the host (per
  `pct list`) are touched — absent vmids (not yet created by OpenTofu), and
  services with no inventory vmid, are skipped silently.
- All tasks are skipped under Docker (`ansible_virtualization_type == 'docker'`)
  for molecule testing.

## Usage

```bash
# Dry run
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags media_lxc_features --check
# Apply (after tofu creates the LXCs, before apps converge)
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags media_lxc_features
```
