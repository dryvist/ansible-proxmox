# ntp

Configures chrony for time synchronization. Supports client, server, and
hybrid modes via variable combinations.

## Installation

This role lives in this repository under `roles/ntp/`. Reference it from a
playbook in the `roles:` block — no Galaxy install needed:

```yaml
- hosts: proxmox
  roles:
    - role: ntp
```

For consumption from sibling repos (`ansible-proxmox-apps`, `ansible-splunk`),
vendor the role or reference it via `requirements.yml` pointing at this repo.

## API

The role's behavior is driven entirely by the variables documented below.
Mode selection (client / server / hybrid) is variable-driven, but a small
number of tasks are fact-gated: the systemd task is skipped under Docker
(`ansible_virtualization_type != 'docker'`) so the role can be molecule-tested
in containers.

### Modes

The combination of `ntp_servers` and `ntp_serve` selects the mode:

- **Client (default)** — `ntp_servers: []`, `ntp_serve: false`. Syncs from
  `ntp_pools` (public Debian pool).
- **Internal client** — `ntp_servers` non-empty, `ntp_serve: false`. Syncs
  from `ntp_servers` plus `ntp_pools` (public pool kept as additional
  sources for resilience).
- **Server** — `ntp_servers: []`, `ntp_serve: true`. Syncs from `ntp_pools`,
  serves to `ntp_allow_cidrs`.
- **Hybrid** — `ntp_servers` non-empty, `ntp_serve: true`. Syncs from
  `ntp_servers` plus `ntp_pools`, serves to `ntp_allow_cidrs`.

### Source selection

Both `ntp_servers` entries (rendered as `server` directives) and `ntp_pools`
entries (rendered as `pool` directives) are always included in the chrony
configuration. Chrony picks the best source automatically by stratum and
jitter — it does not strictly prefer earlier-listed entries.

To make chrony **strictly prefer** internal entries over public pool
members (e.g., to keep traffic on-LAN whenever an internal server is
reachable), include the `prefer` keyword in each `ntp_servers` entry:

```yaml
ntp_servers:
  - "192.168.0.10 iburst prefer"
  - "192.168.0.11 iburst prefer"
```

When all internal `prefer`-marked entries become unreachable, chrony falls
back to selecting among the remaining sources (the public pool).

### Variables

See `defaults/main.yml` for the authoritative list and inline rationale.

- `ntp_servers` (list, default `[]`) — Internal NTP servers. Each entry is
  the full chrony directive following the `server` keyword, so include any
  options you want (e.g., `["192.168.0.10 iburst", "192.168.0.11 iburst prefer"]`).
  Mirrors the `ntp_pools` pattern.
- `ntp_pools` (list, default Debian pool with 4 entries) — Used only when
  `ntp_servers` is empty.
- `ntp_serve` (bool, default `false`) — Enable server mode.
- `ntp_allow_cidrs` (list, default `[]`) — CIDRs allowed to query this host.
  Required when `ntp_serve: true`.
- `ntp_service_state` (string, default `started`) — Passed through to systemd.
- `ntp_service_enabled` (bool, default `true`) — Passed through to systemd.
- `ntp_config_file` (string, default `/etc/chrony/chrony.conf`).

## Usage

### Proxmox hosts (server mode, wired in `playbooks/site.yml`)

```yaml
- role: ntp
  vars:
    ntp_serve: true
    ntp_allow_cidrs:
      - "192.168.0.0/16"
      - "10.0.0.0/8"
```

Result: hosts sync from the Debian public pool and serve NTP to all internal
RFC1918 traffic on UDP/123. Companion firewall rule lives in
`terraform-proxmox/modules/firewall/` (see issue #285).

### Internal clients (used by ansible-proxmox-apps and ansible-splunk)

In the consumer repo's `inventory/group_vars/all.yml`:

```yaml
ntp_servers: "{{ lookup('env', 'PROXMOX_NTP_SERVERS') | split(',') | map('trim') | reject('equalto', '') | list }}"
```

With `PROXMOX_NTP_SERVERS` injected via Doppler. An empty value falls back to
the public pool, so the role stays safe if Doppler is unavailable.

## Verification (server mode)

```sh
chronyc tracking          # current sync state
chronyc clients           # connected clients (server mode)
chronyc sources -v        # upstream sources
```

From a client subnet:

```sh
chronyc -h <proxmox-host> tracking
```

## Idempotency

The `validate: chronyd -p -f %s` directive on the template task pre-validates
the rendered config; a syntax error fails the play before chronyd is told to
restart. Restart fires only via the `Restart chrony` handler — when the file
actually changes.

The systemd task is skipped under Docker (`ansible_virtualization_type !=
'docker'`) so the role can be molecule-tested in containers.

## Contributing

Changes to this role should be paired with a `molecule test` run from the
repo root. Update this README whenever a variable is added, removed, or
changes default value.

## License

Internal — same license as the parent `ansible-proxmox` repository.
