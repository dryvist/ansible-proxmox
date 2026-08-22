# zfs_fault_alert

Immediate Zammad ticket on a specific, already-proven-real ZFS fault
signature: a checksum error, an I/O delay past a threshold, or zed's own
event queue overflowing ("Missed events" -- meaning this whole mechanism
went blind for that window).

## Why this exists, and why it is not just another `pve_health_telemetry` signal

`pve_health_telemetry` deliberately excludes zpool degradation ("already
journal -> syslog"), because duplicating anything ZED/systemd/corosync
already reports would mean two sources of truth for one fact. That pipe
(journal -> `pve_syslog_forwarder` -> Splunk `os` index) is still the
general-purpose path and this role does not replace it.

This role exists for one narrow case where that general path was judged
insufficient: Zammad #17242 found pve-w5900's rpool (single unmirrored
consumer NVMe) threw a real, signature-matched corruption-plus-hang event
three times in eight days, with SMART reading `PASSED` throughout. A log
line nobody is actively reading is not a control for a fault at that
severity -- so this fires a Zammad ticket directly from the host, in
parallel with (not instead of) the syslog path.

## What it watches

- `class=checksum` on the configured pool (`zfs_fault_alert_pool`) -- any
  occurrence fires.
- `class=delay` at or above `zfs_fault_alert_delay_threshold_ms` (default
  30000ms; the observed signature starts at ~70000ms).
- `zfs-zed.service`'s own journal for a "Missed events" line (queue
  overflow), checked every `zfs_fault_alert_missed_events_check_interval`.
  This is not a zed-dispatched event and would otherwise be invisible to the
  zed.d watcher above.

## Installation

An Ansible role, not a standalone package -- included in `playbooks/site.yml`
alongside the other PVE host roles. No separate install step; it ships with
this repo and runs via the normal `site.yml` converge.

## Usage

Disabled everywhere by default. A host opts in via `host_vars`:

```yaml
zfs_fault_alert_enabled: true
```

At converge time (never committed), pass:

- `zfs_fault_alert_openbao_addr` / `zfs_fault_alert_openbao_token` -- a
  short-lived OpenBao read token, same pattern as
  `roles/zammad/tasks/publish_mcp.yml`. Reads the existing
  `zammad_hermes_api_token` (`secret/apps/zammad`) and the published Zammad
  URL (`secret/ai/mcp/zammad` -> `ZAMMAD_MCP_URL`) -- no new credential is
  minted for this one more consumer.
- `zfs_fault_alert_zammad_customer` -- the ticket customer email. Not
  committed; this repo is public and the value is operator-specific.

## Verification

The converge itself proves the wiring is live: after deploying the token,
scripts, and timer, it runs `zfs-fault-alert.sh --self-check`, which
authenticates to Zammad with the deployed token and fails the play if that
does not succeed. Enabling a timer and dropping a zed.d script prove
nothing about whether either can actually reach Zammad -- this closes that
gap the same way `pve_health_telemetry` proves its own journal line reaches
the tag it claims to.
