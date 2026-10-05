# nvidia_driver

Installs NVIDIA's host GPU driver on an opted-in Proxmox node, so LXC guests
can be handed the card through device passthrough.

## Installation

This role lives in this repository under `roles/nvidia_driver/`. Reference it
from a playbook in the `roles:` block — no Galaxy install needed:

```yaml
- hosts: proxmox
  roles:
    - role: nvidia_driver
```

## Usage

Inert by default. Opt a host in via its host_vars — named for the **inventory
hostname**, since a host_vars file named for anything else loads for no host
and leaves this role silently doing nothing:

```yaml
nvidia_driver_enabled: true
```

Fails loud at converge time if a host is opted in but has no NVIDIA PCI device
on the bus. Converge just this role with `--tags nvidia_driver`.

## Why not Debian's `nvidia-driver`

The driver comes from NVIDIA's own apt repository for this Debian release, not
from Debian's `non-free` component. In LXC passthrough the container loads no
kernel module of its own — its userland libraries must match the host's kernel
module version exactly, or `nvidia-smi` inside the guest fails with
`Driver/library version mismatch`. Guest images pull from NVIDIA's repository,
so sourcing the host from it too is what keeps the two matched across upgrades.
Debian's packaging also sits in `non-free`, which these nodes do not enable, and
widening every node's package surface to get one driver onto one node is a worse
trade than a `.sources` file scoped to the opted-in host.

## A reboot is required, and the role does not take it

`nouveau` binds the card at boot from the initramfs, and the NVIDIA module
cannot load while it holds the device. The role blacklists nouveau and
regenerates the initramfs, then **reports** that a reboot is needed rather than
taking one — rebooting a hypervisor interrupts every guest on it, so that is an
operator decision inside a maintenance window.

## Verify after the reboot — both checks, not just the first

```bash
nvidia-smi                # driver loaded, card enumerated
ls -l /dev/nvidia*        # character devices present
```

The second check is the one that matters for passthrough, and it has two traps.

**The nodes are created on demand, so reading them creates them.** They are
materialised by the first process to touch the GPU — and on a headless
hypervisor, that process is your check. `ls /dev/nvidia*` after running
`nvidia-smi` proves nothing: the check and the thing being checked are the same
event. The property you need is that they exist _while nothing is touching the
GPU_, which is only observable on a fresh boot, before anything else runs.

**`nvidia-persistenced` does not do this job.** Measured 27 seconds after a
boot, with persistenced already active: `/dev/nvidia0`, `/dev/nvidiactl` and
`/dev/nvidia-modeset` were present, `/dev/nvidia-uvm` and
`/dev/nvidia-uvm-tools` were not. The role therefore installs a small oneshot
unit that runs `nvidia-modprobe -c 0 -u` at boot — NVIDIA's own tool for exactly
this. Every CUDA runtime needs Unified Memory, and an LXC guest cannot create
those nodes itself (no kernel module to load), so without the unit the container
starts fine and fails at inference, far from the cause.

Re-check after a _subsequent_ reboot too, not only the first one, and assert
the unit is active _before_ looking at the nodes.

Do not hardcode the device majors anywhere downstream. Across a single reboot on
one host, `nvidia-uvm` moved 507 → 510 and the `nvidia-caps` nodes moved
510 → 236.

## Kernel upgrades

DKMS rebuilds the module against each new kernel, which is why
`proxmox-default-headers` is installed alongside the running kernel's headers.
Without the metapackage the build silently stops happening after a kernel
upgrade and the GPU disappears on the next reboot.

## Version pin — and why the driver must not auto-upgrade

`nvidia_driver_version` pins an exact driver series (`nvidia_driver_packages`
installs `nvidia-open=<version>-1`). NVIDIA's apt repository serves more than
one series at a time, so an unpinned `apt install nvidia-open` can resolve a
newer `nvidia-open` than the guest images' userland expects — and because an
LXC guest loads no kernel module of its own, any mismatch between the host's
module and the guest's userland breaks `nvidia-smi` in the guest with
`Driver/library version mismatch`.

Pinning `nvidia-open` alone is not enough: `nvidia-persistenced` and whatever
transitively provides `nvidia-smi` are packaged separately and would still
float onto the repository's newest series on a plain `apt upgrade`. That is
why `nvidia_driver_packages` also installs NVIDIA's own
`nvidia-driver-pinning-<version>` package — it ships apt preferences that
hold that whole dependency chain to the pinned series, which is also what
stops this host auto-upgrading the driver out from under a running guest.
The role asserts the pinning package is present whenever a version is
pinned; there is no extra `apt-mark hold` needed on top of it.

Bump `nvidia_driver_version` deliberately, together with every guest image
pulling the same repository, and re-verify the new version against NVIDIA's
repo first — see the `# renovate: ignore` note on the var for why this is a
manual bump rather than an automated one.

## Optional GPU power limit

`nvidia_driver_power_limit_w` is undefined (a no-op) by default. Set it on a
host whose card's factory power draw exceeds what the chassis or PSU should
sustain continuously (e.g. a Max-Q card) and the role installs a
`nvidia-power-limit.service` boot-time unit that runs `nvidia-smi -pm 1` and
`nvidia-smi -pl <watts>`. Both persistence mode and any power limit reset at
every reboot and at every driver unload/reload — that is why this is a
boot-time unit rather than a one-shot task run at converge time.
The unit runs after `nvidia-persistenced.service` and before
`pve-guests.service`, so it completes before Proxmox starts on-boot guests.
Before starting the unit, the role asserts the requested value is within every
GPU's reported minimum and maximum; after starting it, the role reads back and
asserts each live limit matches within 1 W. An unsupported value fails loudly
instead of relying on the driver to clamp it. Use
`--tags nvidia_driver_power_limit` to apply and verify the power limit by itself;
that tag selects only GPU discovery and driver-state checks plus the power-limit
unit and its readback. It does not select driver installation, reboot reporting,
or graphics-clock tasks.

## Optional maximum graphics clock

`nvidia_driver_graphics_clock_max_mhz` defaults to null, so graphics clocks are
unlocked unless a host explicitly sets a positive integer MHz value. When set,
the role installs and enables a separate `nvidia-graphics-clock.service` that
runs `nvidia-smi -lgc 0,<max>` at boot before Proxmox starts guests. The NVIDIA
role requires a positive integer and checks it against every GPU's reported
maximum before installing the unit. NVIDIA applies the closest supported
frequency to the requested maximum. This setting is independent of the power
cap; `--tags nvidia_driver_graphics_clock` selects the clock-lock path. Removing
the setting stops and disables that unit, resets graphics clocks when the
NVIDIA module is loaded, removes the unit, and reloads systemd. The
power-limit-only tag does not run clock-lock or cleanup tasks.

## Optional CUDA stress utility

`nvidia_driver_gpu_burn_enabled` defaults to false. When enabled, the role
checks out a pinned GPU Burn revision under
`/var/lib/llm-cache/bin/gpu-burn` and builds it for
`nvidia_driver_gpu_burn_compute` using
`nvidia_driver_gpu_burn_cuda_path`. Use `nvidia_driver_packages_extra` for the
host's build and stress packages; these settings are supplied through
host_vars.

## Test coverage limits

The molecule scenario covers the **inert** path only: it converges with the
role disabled and asserts nothing was installed or written. There is no PCI bus
and no buildable kernel inside a container, so the driver install, the DKMS
build, and the device-node behaviour cannot be exercised there. Those are
verified on the host by the commands above.
