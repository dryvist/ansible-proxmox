# node_auto_poweroff

Install a systemd timer that gracefully powers the node off on a schedule.

Built for a **normally-off node** (an offline-DR leg) that gets powered **on**
for a maintenance or replication window and should not be left running
overnight. Powering **off** is the OS's own job — this role just schedules
`systemctl poweroff` — so no BMC credentials are needed. Powering a node back
**on** is the separate [`idrac_power`](../idrac_power/README.md) role (IPMI,
which the OS cannot do for itself once the box is off).

The role is **inert by default**. Opt a host in via `node_auto_poweroff_enabled`
in its `host_vars`; it stays a no-op everywhere else.

## Installation

This role ships in the `ansible-proxmox` repository and is applied via
`playbooks/site.yml`. No separate installation is required beyond cloning the
repo and installing collection dependencies:

```bash
git clone https://github.com/dryvist/ansible-proxmox.git
cd ansible-proxmox
ansible-galaxy install -r requirements.yml
```

## What it does

- Renders `/etc/systemd/system/node-auto-poweroff.service` (a `oneshot` running
  `systemctl --no-block poweroff`) and `node-auto-poweroff.timer`.
- Enables and starts the timer so it fires at `node_auto_poweroff_on_calendar`
  (default daily 22:00 local).
- Skipped under Docker (molecule): the unit files render so the contract is
  verifiable, but the daemon-reload and timer start are not attempted.

`Persistent=false` is deliberate — a missed trigger is **not** caught up, so a
node that was off at the scheduled time and boots later keeps running instead of
powering straight back off. `--no-block` keeps the oneshot from deadlocking on
the shutdown transition it triggers; Proxmox's `pve-guests` ordering still stops
running guests first.

## Variables

| Variable | Default | Description |
| --- | --- | --- |
| `node_auto_poweroff_enabled` | `false` | Opt-in master switch (set per host) |
| `node_auto_poweroff_on_calendar` | `*-*-* 22:00:00` | systemd `OnCalendar` for the power-off; override per host for a different window |

## Usage

Enable for a normally-off node in `inventory/host_vars/<node>.yml`:

```yaml
node_auto_poweroff_enabled: true
# node_auto_poweroff_on_calendar: "*-*-* 23:30:00"   # optional override
```

Applied via `playbooks/site.yml`. The timer is installed **on the target node**,
so the node must be online during the run (it comes up via the `idrac_power`
auto-cycle, or power it on manually):

```bash
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml \
  --limit <normally-off-node> --tags node_auto_poweroff
```

Verify on the node:

```bash
systemctl list-timers node-auto-poweroff.timer   # shows the next trigger
systemctl cat node-auto-poweroff.service          # shows --no-block poweroff
```
