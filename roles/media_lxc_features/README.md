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
| seerr | `/bulk/appdata/seerr`->`/opt/seerr/config` | yes | no |
| sonarr | `/bulk/data`->`/data`, `/bulk/appdata/sonarr`->`/var/lib/sonarr` | no | no |
| radarr | `/bulk/data`->`/data`, `/bulk/appdata/radarr`->`/var/lib/radarr` | no | no |
| download-vpn | `/bulk/data`->`/data`, `/bulk/appdata/qbittorrent`->`/home/qbittorrent`, `/bulk/appdata/prowlarr`->`/var/lib/prowlarr` | yes | yes |

Every mounted service gets the unified `bulk/data` dataset -> `/data`. One
dataset (replacing the old separate `downloads` + `media` datasets/mounts) is
what lets qBittorrent and the *arrs **hardlink** between `/data/torrents/*` and
`/data/media/*` — hardlinks cannot cross dataset boundaries. All bind-mounts are
**read-write** (no `ro=1`), the role's existing convention (plex is read-mostly
by usage, not by mount flag). `/dev/net/tun` is char device **10:200** (verified
on the primary node). Every service additionally gets a **persistent config
mount** — see below.

A mount may carry `owner_user: <name>` (or `owner_uid`/`owner_gid` for an owner
with no named user, e.g. seerr's Docker `node` uid 1000). That marks an
app-**private** config dataset that must be owned by the app itself (not the
shared `media` group), and the role chowns the host path to that owner's mapped
host uid/gid.

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

## App config persistence (`bulk/appdata/<app>`)

Every media app keeps its **own database + settings** under a single config
directory. On a plain LXC that directory lives on the **disposable rootfs**, so a
container **rebuild** wipes it. To stop that, each service bind-mounts a dedicated
**`bulk/appdata/<app>`** dataset over its config dir, so all of its state lives
**off the rootfs** and survives any restart **or** rebuild. The app rebuilds
itself from its own DB on startup — there is no export/replay step.

| service | config dir | what persists |
| --- | --- | --- |
| plex | `/var/lib/plexmediaserver` | identity (`machineIdentifier` + claim + publish) + watch-history DB |
| sonarr | `/var/lib/sonarr` | `sonarr.db` (series, history, queue, blocklist) + `config.xml` |
| radarr | `/var/lib/radarr` | `radarr.db` + `config.xml` |
| download-vpn | `/home/qbittorrent` | qBittorrent prefs + `.local/share` `BT_backup` (active torrents / resume / seeding) |
| download-vpn | `/var/lib/prowlarr` | `prowlarr.db` (indexers, private-tracker auth, app-sync links) |
| seerr | `/opt/seerr/config` | `settings.json` + `db.sqlite3` (users, requests, registrations) |

- **Dataset**: `bulk/appdata` (parent) + one `bulk/appdata/<app>` child per
  service are declared in terraform-proxmox `node_storage` and realized by
  `zfs_pools`. `bulk/appdata` is the home for app *config/state* (distinct from
  `bulk/databases`, for database engines, and `bulk/data`, the re-acquirable
  media library).
- **Snapshots + DR**: `bulk/appdata` gets the **`critical`** sanoid template
  (hourly point-in-time — right for constantly-changing state) on the always-on
  storage node, and a recursive syncoid pull to the offline-DR leg. Both are
  configured in host_vars and cover every `bulk/appdata/<app>` child, so a new
  child inherits hourly snapshots + DR with no extra config.
- **Ownership**: each config mount carries `owner_user: <app>` (or
  `owner_uid: 1000` for seerr's unnamed Docker `node`). The config is owned by the
  app itself; the container leaves its UID map at the default offset, so the role
  chowns the host dataset to `unpriv_base + <in-container uid/gid>` (resolved live
  for named users; the ids are package-assigned, never hardcoded). qBittorrent and
  Prowlarr both run as the `qbittorrent` user, so download-vpn's two config mounts
  share that owner. WireGuard config lives at `/etc/wireguard` (outside
  `/home/qbittorrent`), so the whole-home qBittorrent mount is safe.
- **Fresh-build ordering caveat**: on a *from-scratch* shell this role runs
  **before** the apps converge installs each app, so `id <app>` does not resolve
  yet and the ownership chown is skipped (non-fatal). Run order on a new build is:
  `media_lxc_features` (mount) → apps converge (installs the apps) →
  `media_lxc_features` once more (ownership reconciles). The dataset **data** is
  never at risk — it lives outside the rootfs that the rebuild replaces.
- **First cutover (existing live data)**: an app already running on the rootfs has
  its current DB there, not yet on the empty dataset. Mounting the empty dataset
  over it would hide that DB. The role handles this **automatically and safely**:
  - It **stats every host mount source first** and only applies a bind-mount whose
    source already exists. A missing `bulk/appdata/<app>` dataset (zfs_pools not yet
    run) is warned and **skipped**, never `pct`-auto-created as an empty dir over a
    live config.
  - For each app-config mount it then runs a **one-time seed** (`seed_config_dataset.yml`):
    if the dataset exists but is empty and the in-container config dir is populated
    and the mount is not yet applied, it streams the live config dir into the
    dataset **before** the mount is set. Guarded to run exactly once — once the
    dataset is non-empty (or the mount is present) it is a no-op forever.
  - Order on a first cutover: zfs_pools (creates the dataset) → media_lxc_features
    (seed → mount → ownership reconcile → restart). The app restarts onto the
    seeded dataset; every future rebuild then persists with no manual step.

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
