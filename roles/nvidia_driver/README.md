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

The second check is the one that matters for passthrough and the one most
likely to regress. Those device nodes are created *on demand* by the first
process to touch the GPU; on a headless hypervisor nothing does, so without
`nvidia-persistenced` (which this role enables) they are simply absent after a
reboot. An LXC device bind pointing at a path that does not exist leaves the
container running with no GPU and no error anywhere — the same silent
post-reboot regression class as a Wake-on-LAN flag that resets every boot.

Re-check both after a *subsequent* reboot too, not only the first one.

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
