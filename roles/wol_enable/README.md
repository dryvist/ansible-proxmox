# wol_enable

Persists Wake-on-LAN (magic packet) on a host's physical NIC across reboots.

BIOS/UEFI Wake-on-LAN must already be enabled -- this role only covers the OS
side. `ethtool -s <iface> wol g` does not survive a reboot on its own: the NIC
driver resets Wake-on to its hardware default (usually disabled) on every
bring-up. This role sets it immediately and installs a udev rule
(`/etc/udev/rules.d/99-wol-enable.rules`) that re-applies it on every
interface `add` event, so it holds after every future boot too.

On a Proxmox node it also publishes the NIC's MAC into that node's own config
as the `wakeonlan` key, which is what `pvenode wakeonlan <node>` reads to know
where to send the magic packet — the command refuses when the key is unset. The
key lives in `/etc/pve`, so every node in the cluster carries a copy and any
surviving node can wake any other by name.

The address is discovered on the node itself (`ethtool -P`, the permanent
hardware address, falling back to the runtime address when the NIC reports no
permanent one). When inventory already owns a pinned-uplink MAC, set
`wol_enable_mac` from that variable so the bridge, WoL lookup, and udev rule
share the same device identity. With a configured MAC, the role resolves the
current kernel interface name at converge time and matches the udev rule by
MAC instead of a kernel slot name.

Inert by default. Opt a host in via host_vars:

```yaml
wol_enable_enabled: true
wol_enable_interface: nic0     # stable physical NIC alias, not the bridge
wol_enable_mac: "{{ pve_host_network_uplink_mac }}"
```

Fails loud at converge time if the interface doesn't advertise magic-packet
support, if enabled with no interface set, or if no MAC address can be
resolved for the interface.

## Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `wol_enable_enabled` | `false` | Master switch. |
| `wol_enable_interface` | `""` | Stable alias for the physical NIC, not the bridge. Required when enabled. |
| `wol_enable_node_config` | `true` | Publish this node's `wakeonlan` key. Set false on a non-Proxmox host. |
| `wol_enable_mac` | `""` | MAC identity override; empty discovers on-node, populated resolves the current interface and udev match by MAC. |

## Installation

This role lives in this repository under `roles/wol_enable/`. Reference it
from a playbook in the `roles:` block -- no Galaxy install needed:

```yaml
- hosts: proxmox
  roles:
    - role: wol_enable
```

## Usage

Applied by `playbooks/site.yml` on every converge; scope a run to it with
`--tags wol_enable`.

Waking a host that is fully powered off is a magic packet sent from another
host on the same L2 segment (WoL does not typically cross a router without
directed-broadcast support). From any other node in the cluster:

```bash
pvenode wakeonlan <node>
```

That reads the target's `wakeonlan` key from `/etc/pve` — published by this
role — so no MAC has to be looked up or remembered. Outside a Proxmox cluster,
send the packet directly with the address `ethtool -P <iface>` reports on the
target:

```bash
wakeonlan <mac-address>
```

## Limits

A magic packet only reaches a NIC that still has standby power, which means AC
present at the PSU. A node with no AC cannot be woken by any network method;
bringing it back when AC returns is a firmware setting, not a packet. See
[`idrac_power`](../idrac_power/README.md) for the BMC-side power-restore
policy, and the commissioning notes in `docs/DR_RUNBOOK.md`.
