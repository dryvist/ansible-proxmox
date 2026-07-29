# node_watchdog

Makes a wedged node reset itself instead of sitting dark until someone notices.

## Two layers, and why they are separate

| Layer | Mechanism | Catches | Cannot catch |
| --- | --- | --- | --- |
| Hardware watchdog | `WATCHDOG_MODULE` in `/etc/default/pve-ha-manager`, driven by Proxmox's `watchdog-mux` | A hung kernel — the chipset/BMC resets the board without the kernel's cooperation | A node that is up and responsive but doing no useful work |
| Liveness daemon | `watchdog(8)`, configured **device-less** | Runaway load, memory exhaustion, a stale log, an unresponsive cluster filesystem, a failed pool | A kernel that has stopped executing (nothing left to run the checks) |

They cover each other's blind spot, which is why both exist.

## The device contention trap

Proxmox's `watchdog-mux` owns `/dev/watchdog`. Giving the `watchdog` daemon a
`watchdog-device` makes the two fight for it — the reliable way to turn this
role into the outage it exists to prevent.

So the daemon runs **device-less**: on sustained check failure it issues the
reboot itself. A systemd drop-in clears the packaged `ExecStartPre` so the unit
does not consider itself failed merely because the device is unavailable.

## What it does not cover

**Instantaneous power loss.** If the machine stops receiving power there is
nothing left running to time out and the watchdog is already gone. That case
needs the firmware setting restoring power state after an AC loss.

Arming it on a node suspected of power faults is still worthwhile, because it
becomes a **discriminator**: a node that dies while the watchdog is armed, with
no reset attributable to the watchdog, is positive evidence the kernel was alive
until the instant power was lost.

## Selecting the device

`node_watchdog_module` is resolved from the host's hardware class in inventory
via `node_watchdog_module_map` — never from a host name, so a new machine of a
known class needs no change here. Unknown classes fall back to `softdog`, and
the role says so loudly: softdog is a kernel timer and cannot fire when the
kernel is what stopped.

## Timing

Default is a 60s hardware timeout with checks every 10s, tolerating 3
consecutive failures — a restart roughly a minute after a failure that does not
resolve itself. Keep the timeout comfortably above `interval x retries`; a
spurious reset of a healthy node is worse than a slightly slower one.

## Verifying it works

Arming a watchdog and never testing it is the same as not having one. In a
maintenance window, on a node carrying nothing critical:

```sh
echo c > /proc/sysrq-trigger    # deliberate kernel panic
```

The node must reset within the timeout **and** produce a vmcore. If it resets
but leaves no vmcore, kdump is not working and the next real crash will again
leave nothing to analyse.

## Disarming

Set `node_watchdog_arm: false` in host_vars while commissioning a node or
holding it down deliberately. The role then stops and disables the daemon
rather than leaving a half-armed state.
