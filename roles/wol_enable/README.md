# wol_enable

Persists Wake-on-LAN (magic packet) on a host's physical NIC across reboots.

BIOS/UEFI Wake-on-LAN must already be enabled -- this role only covers the OS
side. `ethtool -s <iface> wol g` does not survive a reboot on its own: the NIC
driver resets Wake-on to its hardware default (usually disabled) on every
bring-up. This role sets it immediately and installs a udev rule
(`/etc/udev/rules.d/99-wol-enable.rules`) that re-applies it on every
interface `add` event, so it holds after every future boot too.

Inert by default. Opt a host in via host_vars:

```yaml
wol_enable_enabled: true
wol_enable_interface: enp5s0   # the physical NIC, not the bridge
```

Fails loud at converge time if the interface doesn't advertise magic-packet
support, or if enabled with no interface set.

## Installation

This role lives in this repository under `roles/wol_enable/`. Reference it
from a playbook in the `roles:` block -- no Galaxy install needed:

```yaml
- hosts: proxmox
  roles:
    - role: wol_enable
```

## Sending a wake

This role has no BMC/IPMI equivalent on non-power-managed hardware, so
waking a host that is fully powered off is a magic packet sent from any host
on the same L2 segment (WoL does not typically cross a router without
directed-broadcast support):

```bash
wakeonlan <mac-address>
```

See the target host's host_vars for its documented NIC MAC address.
