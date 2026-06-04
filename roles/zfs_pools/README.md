# zfs_pools

Manages ZFS **datasets, quotas, and Proxmox storage registration** for the
per-node pools declared in `terraform-proxmox`'s `node_storage` output.

## Installation

This role ships in the `ansible-proxmox` repository and is applied via
`playbooks/site.yml`. No separate installation is required beyond cloning the
repo and installing collection dependencies:

```bash
git clone https://github.com/dryvist/ansible-proxmox.git
cd ansible-proxmox
ansible-galaxy collection install -r requirements.yml
```

## Scope (and what it deliberately does NOT do)

`terraform-proxmox` declares storage; `ansible-proxmox` realizes it. The
Proxmox API cannot create ZFS pools (`zpool create` is an OS operation), so the
contract is split:

| Layer                                      | Owns                                             |
| ------------------------------------------ | ------------------------------------------------ |
| Host commissioning (auto-install / manual) | `zpool create` from physical devices             |
| **this role**                              | datasets, quotas, `pvesm` storage registration   |
| terraform-proxmox                          | references the datastore by `id` on VM/LXC disks |

**Pool creation is opt-in and off by default.** Creating a pool needs the
host-specific device list (`by-id` paths), which is not in the committed
contract, and getting it wrong destroys data. By default the role asserts a
`register=true` pool already exists and manages datasets within it. To allow
creation, set in untracked `host_vars`:

```yaml
zfs_pools_allow_create: true
zfs_pools_devices:
  tank: ["/dev/disk/by-id/...", "/dev/disk/by-id/...", "/dev/disk/by-id/..."]
```

## Inputs

`inventory/load_tofu.yml` injects `zfs_pools_from_tofu` onto each
proxmox host: the `node_storage[<node>]` entry for that host, keyed by the
host's `proxmox_node_name` (defaults to the inventory hostname). Set
`proxmox_node_name` in `host_vars` when the inventory name differs from the
tofu node name (e.g. inventory `node-a` → tofu `pve2`).

Shape (`zfs_pools_map`):

```yaml
zfs_pools_map:
  tank:
    type: zfspool
    raid: raidz1 # informational
    protected: true # storage-safety (hold/readonly enforcement: design pending)
    register: true # run `pvesm add zfspool` if not already registered
    content: [images, rootdir]
    datasets:
      backups:
        quota: "1T"
        properties:                 # optional; any zfs property=value
          recordsize: "1M"
          compression: "zstd"
          "com.sun:auto-snapshot": "false"
```

### Per-dataset properties

`datasets.<name>.properties` is an optional map of arbitrary ZFS properties
(`recordsize`, `compression`, `readonly`, `atime`, `com.sun:auto-snapshot`,
user properties, …). Each is read with `zfs get -H -o value` and only set when
it differs, so re-runs report no change. Declare values in **ZFS canonical
form** (`recordsize: "1M"`, `compression: "zstd"`, `readonly: "on"`) and
**quote** them so YAML does not coerce `on`/`off`/`true`/`false` to booleans.
`quota` keeps its own dedicated (byte-compared) handling — do not also put it
under `properties`.

## Usage

```bash
# Dry run — storage tasks only
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags zfs_pools --check
# Apply
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags zfs_pools
```

## Idempotency

- Pools: checked with `zpool list`; only created when explicitly allowed.
- Datasets: checked with `zfs list`; created with `zfs create -p` when absent.
- Quotas: compared in **bytes** (`zfs get -Hp` vs `human_to_bytes(desired)`), so
  `1T` and `1024G` do not cause spurious changes.
- Properties: each `properties` entry compared as a string (`zfs get -H -o
  value`) and only `zfs set` when it differs.
- Registration: `pvesm status --storage <pool>` gates `pvesm add`.

All ZFS / `pvesm` tasks are skipped under Docker (`ansible_virtualization_type
== 'docker'`) for molecule testing.
