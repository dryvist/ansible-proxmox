# pve_node_exporter

Install [prometheus node_exporter](https://github.com/prometheus/node_exporter)
on each Proxmox VE host as a pinned-version native systemd service, exposing
host metrics (CPU, memory, disk, ZFS, network) on port `9100`. Beside it, the
role installs [zfs_exporter](https://github.com/pdf/zfs_exporter) the same way,
exposing per-dataset ZFS space accounting on port `9134`.

## What It Does

1. Creates a dedicated no-login system user (`node-exporter`).
2. Downloads the **pinned** upstream release tarball to a versioned path under
   `/opt/node_exporter/` and verifies its SHA256 checksum.
3. Unpacks it (versioned, `creates:`-guarded) and installs the binary to
   `/usr/local/bin/node_exporter` — only rewritten on a version bump.
4. Optionally creates the textfile-collector directory so scripts can publish
   custom metrics by dropping `*.prom` files.
5. When packaged collectors are enabled, creates their output directory, installs
   their configured packages, and enables the SMART, NVMe, and IPMI sensor
   timers. The service reads that directory as a second textfile-collector
   source.
6. Deploys a hardened systemd unit and enables/starts the service.
7. When `pve_node_exporter_zfs_exporter_enabled` (default), downloads the
   **pinned** zfs_exporter release tarball to a versioned path under
   `/opt/zfs_exporter/`, always verifies its SHA256 checksum, installs the
   binary to `/usr/local/bin/zfs_exporter`, and runs it as a second hardened
   systemd service (`zfs_exporter`) under the same service account.

Re-runs are no-ops; bumping `pve_node_exporter_version` (plus checksum) rolls
the fleet forward on the next converge, and the same holds for
`pve_node_exporter_zfs_exporter_version`.

## Where It Runs

Wired into `playbooks/site.yml` against the `proxmox` group. By default the
exporter binds the node's **management IP** (the default-route interface fact,
derived at runtime — never hardcoded), so metrics are only reachable on the
management VLAN.

## Usage

Runs with the rest of `site.yml`, or target just this role by tag:

```bash
ansible-playbook -i inventory/hosts.yml playbooks/site.yml \
  --limit proxmox,localhost --tags pve_node_exporter
```

### Variables

| Variable                                       | Default                                         | Purpose                                              |
| ---------------------------------------------- | ----------------------------------------------- | ---------------------------------------------------- |
| `pve_node_exporter_version`                    | `1.12.1`                                        | Pinned upstream release.                             |
| `pve_node_exporter_download_url`               | GitHub releases URL                             | Override to a local mirror for offline converges.    |
| `pve_node_exporter_checksum`                   | SHA256 per architecture                         | Verify the pinned release checksum.                  |
| `pve_node_exporter_listen_address`             | node's mgmt IP (`ansible_default_ipv4.address`) | Bind address.                                        |
| `pve_node_exporter_port`                       | `9100`                                          | Listen port.                                         |
| `pve_node_exporter_user`                       | `node-exporter`                                 | Service account.                                     |
| `pve_node_exporter_install_dir`                | `/opt/node_exporter`                            | Versioned install root.                              |
| `pve_node_exporter_textfile_collector_enabled` | `true`                                          | Enable the textfile collector.                       |
| `pve_node_exporter_textfile_collector_dir`     | `/var/lib/node_exporter/textfile_collector`     | Drop `*.prom` files here to expose custom metrics.   |
| `pve_node_exporter_extra_args`                 | `[]`                                            | Extra CLI flags appended to `ExecStart`.             |

### Packaged hardware collectors

With `pve_node_exporter_packaged_collectors_enabled: true` (default) the role creates
`pve_node_exporter_packaged_collectors_dir` (`/var/lib/prometheus/node-exporter`) before
installing the packages in `pve_node_exporter_packaged_collectors_packages`
(`prometheus-node-exporter-collectors`, `smartmontools`, `nvme-cli`, `ipmitool`), because the
package starts its timers on install and the collector units write into that directory, and enables the timers in
`pve_node_exporter_packaged_collectors_timers` (SMART, NVMe, IPMI sensor). Each timer skips hosts
without the matching hardware. The service reads the directory through a second
`--collector.textfile.directory` flag.

### ZFS dataset exporter

node_exporter's `zfs` collector reports pool and ARC statistics only.
zfs_exporter adds one series per dataset (filesystem or volume) and property,
labelled `name`, `pool` and `type`, plus its pool series:

| Metric                               | ZFS property      | Collected for        |
| ------------------------------------ | ----------------- | -------------------- |
| `zfs_dataset_used_bytes`             | `used`            | filesystems, volumes |
| `zfs_dataset_used_by_snapshot_bytes` | `usedbysnapshots` | filesystems, volumes |
| `zfs_dataset_available_bytes`        | `available`       | filesystems, volumes |
| `zfs_dataset_quota_bytes`            | `quota`           | filesystems          |
| `zfs_dataset_referenced_bytes`       | `referenced`      | filesystems, volumes |
| `zfs_dataset_volume_size_bytes`      | `volsize`         | volumes              |

The snapshot collector is off (`--no-collector.dataset-snapshot`), so no
per-snapshot series exist and cardinality stays bounded by the dataset count.
An unset quota reports `0`.

| Variable                                               | Default                                             | Purpose                                             |
| ------------------------------------------------------ | --------------------------------------------------- | --------------------------------------------------- |
| `pve_node_exporter_zfs_exporter_enabled`               | `true`                                              | Install and run zfs_exporter.                       |
| `pve_node_exporter_zfs_exporter_version`               | `2.5.1`                                             | Pinned upstream release.                            |
| `pve_node_exporter_zfs_exporter_download_url`          | GitHub releases URL                                 | Override to a local mirror for offline converges.   |
| `pve_node_exporter_zfs_exporter_checksum`              | SHA256 per architecture                             | Always verified; move it with the version.          |
| `pve_node_exporter_zfs_exporter_port`                  | `9134`                                              | Listen port, on `pve_node_exporter_listen_address`. |
| `pve_node_exporter_zfs_exporter_install_dir`           | `/opt/zfs_exporter`                                 | Versioned install root.                             |
| `pve_node_exporter_zfs_exporter_filesystem_properties` | `available,quota,referenced,used,usedbysnapshots`   | Properties collected per filesystem.                |
| `pve_node_exporter_zfs_exporter_volume_properties`     | `available,referenced,used,usedbysnapshots,volsize` | Properties collected per volume.                    |
| `pve_node_exporter_zfs_exporter_extra_args`            | `[]`                                                | Extra CLI flags appended to `ExecStart`.            |

#### Scrape target

Each node serves `http://<node-mgmt-ip>:9134/metrics`, on the same address as
node_exporter's `:9100`. This repository declares no scrape jobs: the
Prometheus job that scrapes the Proxmox nodes' `:9100` targets lives in
`ansible-proxmox-apps`, and the node firewall rules for exporter ports live in
`tofu-proxmox`. Add the `<node>:9134` target and allow TCP `9134` there.

## Verification

```bash
systemctl is-active node_exporter
curl -s http://<node-mgmt-ip>:9100/metrics | head

# Version actually running matches the pin
/usr/local/bin/node_exporter --version

systemctl is-active zfs_exporter
curl -s http://<node-mgmt-ip>:9134/metrics | grep '^zfs_dataset_used_bytes'
/usr/local/bin/zfs_exporter --version
```

## License

Apache-2.0, matching the repository (node_exporter itself is Apache-2.0;
zfs_exporter is MIT).
