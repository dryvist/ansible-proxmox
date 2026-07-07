# pve_syslog_forwarder

Forward each Proxmox VE node's logs to the central syslog pipeline so
everything lands in Splunk. Installs `rsyslog`, which ingests the systemd
journal by default on Debian, and adds one drop-in rule that ships **all**
logs to the HAProxy syslog VIP.

```text
this PVE node (journald + rsyslog)
  -> syslog.<PROXMOX_SUBDOMAIN>:<linux port>  (TCP, disk-assisted queue)
     -> HAProxy syslog VIP
        -> Cribl Edge  (syslog pipeline)
           -> Splunk HEC  (os index)
```

Ported from the `syslog_forwarder` role in `ansible-proxmox-apps` (which covers
the infra LXCs); this role covers the hypervisors themselves.

## What It Does

`rsyslog` reads the systemd journal (`imjournal`) by default on Debian, so a
single forward rule captures host logs plus every native systemd service —
`pveproxy`, `pvedaemon`, `pve-firewall`, `corosync`, the ZFS event daemon, and
everything else on the node. The rule uses `omfwd` with a disk-assisted action
queue, so a HAProxy/Cribl outage buffers (up to
`pve_syslog_forwarder_queue_max_disk_space`) instead of dropping logs.

Unlike the LXC variant in `ansible-proxmox-apps`, no systemd sandboxing
override is needed: PVE nodes are real hosts and satisfy the stock
`rsyslog.service` hardening.

## Where It Runs

Wired into `playbooks/site.yml` against the `proxmox` group — every node
forwards on every converge. The syslog receiver chain (HAProxy, Cribl) runs in
LXCs managed by `ansible-proxmox-apps`, so there is no forward-into-yourself
loop at the host layer.

## Usage

Runs with the rest of `site.yml`, or target just this role by tag:

```bash
doppler run -- ansible-playbook -i inventory/hosts.yml playbooks/site.yml \
  --limit proxmox,localhost --tags pve_syslog_forwarder
```

### Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `pve_syslog_forwarder_target_host` | `syslog.{{ PROXMOX_SUBDOMAIN }}` | The `syslog` CNAME (→ HAProxy VIP). Never a literal. |
| `pve_syslog_forwarder_target_port` | `517` | Linux-family syslog port (→ Splunk `os` index). Pinned because `load_tofu.yml` does not inject `constants`; source of truth is terraform-proxmox `pipeline_constants.syslog_ports.linux`. |
| `pve_syslog_forwarder_protocol` | `tcp` | `tcp` (reliable) or `udp`. |
| `pve_syslog_forwarder_config_path` | `/etc/rsyslog.d/10-forward-cribl.conf` | Drop-in rule owned by this role. |
| `pve_syslog_forwarder_queue_max_disk_space` | `256m` | Disk-queue cap so a receiver outage buffers instead of dropping. |

The role asserts `PROXMOX_SUBDOMAIN` is set (injected via Doppler, like
`PROXMOX_NODE_PREFIX`) so the real domain is never committed.

## Verification

```bash
# On a PVE node: the drop-in exists and rsyslog is happy.
cat /etc/rsyslog.d/10-forward-cribl.conf
rsyslogd -N1
systemctl is-active rsyslog

# End to end: this node's logs appear in Splunk under the os index
#   index=os host=<node>
```

## License

Apache-2.0, matching the repository.
