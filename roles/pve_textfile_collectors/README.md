# pve_textfile_collectors

The role installs five scheduled collectors that write Prometheus textfiles to
the node_exporter textfile directory. Collectors report ZFS pool status and
latency, transaction group sync time, pool fill, and Corosync link and quorum
state. Each collector writes a success and duration metric.

## Variables

| Variable | Default | Description |
| --- | --- | --- |
| `pve_textfile_collectors_script_dir` | `/usr/local/lib/pve-textfile-collectors` | Installed collector scripts. |
| `pve_textfile_collectors_textfile_dir` | node_exporter textfile directory | Prometheus textfile output directory. |
| `pve_textfile_collectors_timeout_seconds` | `20` | Timeout for each external command. |
| `pve_textfile_collectors_txg_root` | `/proc/spl/kstat/zfs` | Root directory for ZFS transaction group statistics. |
| `pve_textfile_collectors_zpool_command` | `zpool` | ZFS pool command. |
| `pve_textfile_collectors_awk_command` | `awk` | Text processing command. |
| `pve_textfile_collectors_date_command` | `date` | Timestamp conversion command. |
| `pve_textfile_collectors_corosync_cmapctl_command` | `corosync-cmapctl` | Corosync statistics command. |
| `pve_textfile_collectors_corosync_quorumtool_command` | `corosync-quorumtool` | Corosync quorum command. |
| `pve_textfile_collectors_collectors` | five enabled collectors | Collector interval and enabled settings. |

## Metrics

| Metric | Labels | Description |
| --- | --- | --- |
| `pve_textfile_success` | `script` | Whether every command succeeded for a collector. |
| `pve_textfile_duration_seconds` | `script` | Collector execution duration in seconds. |
| `pve_zpool_scan_state` | `pool` | Scan state: none `0`, scanning `1`, finished `2`, canceled or paused `3`. |
| `pve_zpool_scan_pct` | `pool` | Percentage of the current scan completed. |
| `pve_zpool_scan_errors` | `pool` | Errors reported by the most recent scan. |
| `pve_zpool_scan_end_time_seconds` | `pool` | Unix time when the most recent scan ended, or zero. |
| `pve_zpool_health` | `pool`, `state` | Current ZFS pool health state. |
| `pve_zpool_read_ops` | `pool` | Read operations per second. |
| `pve_zpool_write_ops` | `pool` | Write operations per second. |
| `pve_zpool_read_bytes` | `pool` | Read bytes per second. |
| `pve_zpool_write_bytes` | `pool` | Write bytes per second. |
| `pve_zpool_wait_seconds` | `pool`, `op`, `kind` | ZFS I/O wait seconds; `op` is read or write and `kind` is total, disk, syncq, or asyncq. |
| `pve_zfs_txg_sync_seconds` | `pool`, `quantile` | Transaction group sync time for quantiles `0.5`, `0.9`, `0.99`, and `max`. |
| `pve_zfs_txg_dirty_bytes` | `pool` | Dirty bytes in the latest committed transaction group. |
| `pve_zpool_size_bytes` | `pool` | Total size of a ZFS pool in bytes. |
| `pve_zpool_alloc_bytes` | `pool` | Allocated bytes in a ZFS pool. |
| `pve_zpool_free_bytes` | `pool` | Free bytes in a ZFS pool. |
| `pve_zpool_frag_percent` | `pool` | Fragmentation percentage of a ZFS pool. |
| `pve_zpool_cap_percent` | `pool` | Capacity percentage of a ZFS pool. |
| `pve_corosync_link_connected` | `peer`, `link` | Whether a Corosync link is connected. |
| `pve_corosync_link_latency_avg_microseconds` | `peer`, `link` | Average Corosync link latency in microseconds. |
| `pve_corosync_link_latency_max_microseconds` | `peer`, `link` | Maximum Corosync link latency in microseconds. |
| `pve_corosync_quorate` | none | Whether the Corosync cluster has quorum. |
| `pve_corosync_votes` | `kind` | Corosync votes for expected, total, or quorum. |

The Corosync collector emits no Corosync samples and reports success when the
Corosync command tools are absent.
