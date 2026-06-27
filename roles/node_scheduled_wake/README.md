# node_scheduled_wake

Power a normally-off node **ON** via IPMI on a schedule. This is the wake
counterpart to [`node_auto_poweroff`](../node_auto_poweroff/README.md) (the sleep
half): together they let an offline-DR node cycle through a
**wake → replicate → sleep** loop autonomously, so it is powered up only for the
few minutes its backup actually needs.

## How it works

- Runs on an always-on **controller** that can reach the BMC subnet (the target
  itself is off, so the power-on cannot originate there — the same reason
  [`idrac_power`](../idrac_power/README.md) delegates ipmitool to a controller).
- Installs one systemd **timer + oneshot service per target**. The service's
  `ExecStart` is a single `ipmitool -I lanplus -H <bmc> -U <user> -E chassis
  power on` — idempotent (a no-op if the target is already on), no custom script.
- The BMC password is supplied through a root-only `0600` EnvironmentFile
  (`/etc/node-scheduled-wake/<target>.env`); `ipmitool -E` reads
  `$IPMITOOL_PASSWORD`, so it never appears on the command line or in
  `systemctl cat`.
- `Persistent=false`: a missed window is **not** caught up — wait for the next.

Once the target boots it runs its own on-boot replication
(`syncoid_trigger: boot` in the `syncoid` role) and powers itself off on
completion (`node_auto_poweroff`), closing the loop. The wall-clock syncoid cron
is the wrong trigger for a wake-driven node — it would never fire inside a short
power-on window — which is why the target replicates **on boot** instead.

## Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `node_scheduled_wake_enabled` | `true` | Master switch. |
| `node_scheduled_wake_on_calendar` | `["*-*-* 03:00:00", "*-*-* 15:00:00"]` | Default wake schedule (systemd `OnCalendar`, local time). |
| `node_scheduled_wake_bmc_username` | `{{ env IDRAC_USERNAME }}` | BMC user (from Doppler). |
| `node_scheduled_wake_bmc_password` | `{{ env IDRAC_PASSWORD }}` | BMC password (from Doppler; written to the EnvironmentFile only). |
| `node_scheduled_wake_targets` | `[]` | Targets to wake. **Empty ⇒ role is inert.** |

Each `node_scheduled_wake_targets` entry:

```yaml
node_scheduled_wake_targets:
  - name: <node>                       # target node name (unit naming)
    bmc_host: "{{ lookup('env', 'X') }}" # BMC address — FQDN preferred (env/SOPS, never committed)
    on_calendar:                       # optional per-target schedule override
      - "*-*-* 03:00:00"
      - "*-*-* 15:00:00"
```

Set `node_scheduled_wake_targets` only in the **controller's** host_vars so the
role stays inert everywhere else.

## Operational caveat: maintenance converges

Once the woken node carries `syncoid_trigger: boot` + `node_auto_poweroff_on_complete`,
**every** boot (including the power-on at the start of a `site.yml` maintenance
run) triggers the on-boot replicate, which powers the node off on completion —
so a converge can be cut short ~1 min in. Before a maintenance converge of such a
node, hold it up: `systemctl mask node-auto-poweroff.service` on the target (the
on-boot replicate's `OnSuccess=` then no-ops), and unmask when done. A
site.yml-level fix (mask during the power-managed window, unmask before the
explicit IPMI power-off) is tracked as a follow-up.

## Molecule

Under Docker the ipmitool install, daemon-reload, and timer enable are skipped;
the unit + credentials files still render, so the scenario proves the role
templates a service + timer per target from the contract. Live IPMI power-on is
validated on real hardware, not in molecule.
