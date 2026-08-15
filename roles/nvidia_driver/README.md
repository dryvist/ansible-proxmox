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
event. The property you need is that they exist *while nothing is touching the
GPU*, which is only observable on a fresh boot, before anything else runs.

**`nvidia-persistenced` does not do this job.** Measured 27 seconds after a
boot, with persistenced already active: `/dev/nvidia0`, `/dev/nvidiactl` and
`/dev/nvidia-modeset` were present, `/dev/nvidia-uvm` and
`/dev/nvidia-uvm-tools` were not. The role therefore installs a small oneshot
unit that runs `nvidia-modprobe -c 0 -u` at boot — NVIDIA's own tool for exactly
this. Every CUDA runtime needs Unified Memory, and an LXC guest cannot create
those nodes itself (no kernel module to load), so without the unit the container
starts fine and fails at inference, far from the cause.

Re-check after a *subsequent* reboot too, not only the first one, and assert
the unit is active *before* looking at the nodes.

Do not hardcode the device majors anywhere downstream. Across a single reboot on
one host, `nvidia-uvm` moved 507 → 510 and the `nvidia-caps` nodes moved
510 → 236.

## Kernel upgrades

DKMS rebuilds the module against each new kernel, which is why
`proxmox-default-headers` is installed alongside the running kernel's headers.
Without the metapackage the build silently stops happening after a kernel
upgrade and the GPU disappears on the next reboot.

## Test coverage limits

The molecule scenario covers the **inert** path only: it converges with the
role disabled and asserts nothing was installed or written. There is no PCI bus
and no buildable kernel inside a container, so the driver install, the DKMS
build, and the device-node behaviour cannot be exercised there. Those are
verified on the host by the commands above.
