# pve_host_network

Pins a Proxmox host uplink to a stable `nicN` name using its permanent MAC and
configures the management bridge to use that same name.

## Contract

- Inventory must define `pve_host_network_uplink_mac` for every enforced node.
- `pve_host_network_uplink` must match `nic` followed by a number. The default
  is `nic0`.
- The role writes the `.link` file and `/etc/network/interfaces` in the same
  enforcement run. It rebuilds initramfs if the `.link` changes.
- The current management address and default gateway come from gathered host
  facts when explicit `pve_host_network_address` or
  `pve_host_network_gateway` overrides are absent.
- A reboot is required before the new name and bridge configuration take
  effect. The role does not reload networking or reboot the host.
- Missing MACs, uplink names, addresses, or gateways fail before network files
  are written.

## Proxmox interface-pinning tool

Proxmox VE 9 documents `pve-network-interface-pinning`; earlier discussion
used the name `proxmox-network-interface-pinning`. The current tool generates
MAC-matched `.link` files in `/usr/local/lib/systemd/network` and defaults to
names such as `nic1` and `nic2`. Its `generate` operation also stages edits to
`/etc/network/interfaces`, node firewall configuration, and SDN controller and
fabric configuration as `.new` files. Review those staged files and reconcile
them before reboot. The tool does not update the cluster-wide
`/etc/pve/firewall/cluster.fw`, since a pinned mapping is local to each node.

The role renders the `.link` file directly from host inventory so the pinned
name and bridge port are declared together. Review other node-local interface
references, including firewall and SDN configuration, before a rollout; the
role does not rewrite those files. Systemd applies the rename at boot, so an
incorrect MAC or an unreviewed bridge change can disconnect a node.

The documented manual `.link` format matches both `MACAddress` and
`Type=ether`, sets `Name=nicN`, requires rebuilding initramfs, and takes effect
after reboot. Use a name in the `nicN` form to match the Proxmox tool's output.
The manual guide recommends names beginning with `en` or `eth` when the
interface must be recognized as physical by the Proxmox GUI; `nicN` follows the
native tool's generated naming, so manage this interface through the declared
configuration and verify GUI behavior before relying on GUI network edits.

Sources, retrieved 2026-10-05:

- [Proxmox VE Administration Guide: Network Interface Pinning](https://pve.proxmox.com/pve-docs/pve-admin-guide.html#network_interface_pinning)
- [Proxmox VE network documentation source](https://github.com/proxmox/pve-docs/blob/master/pve-network.adoc)
- [Proxmox interface-pinning CLI source](https://github.com/proxmox/pve-manager/blob/master/PVE/CLI/pve_network_interface_pinning.pm)
- [Proxmox developer discussion on the tool name](https://lists.proxmox.com/pipermail/pve-devel/2025-August/074392.html)

## Rollout

Renaming an uplink can sever remote access. Roll out one node at a time, with
working local console or iDRAC access available for that node:

1. Confirm the permanent MAC and management address in inventory. Check the
   target node's current interface and references in firewall and SDN config.
2. Run the role for that node with enforcement enabled and review the rendered
   `.link` and `/etc/network/interfaces` changes. The bridge must use the same
   `nicN` name as the `.link` file.
3. Let the role rebuild initramfs if the link file changed. Do not run a broad
   cluster rollout; the role leaves the host online with staged files.
4. Reboot that node from an approved maintenance window while console or iDRAC
   access is available. A reboot is required for the rename.
5. Verify the interface name, bridge port, management route, and cluster
   connectivity before moving to the next node.

Never roll out a rename without recovery access. If the node does not return,
use the console or iDRAC to correct the MAC match or restore the prior network
configuration.

## Usage

Detection is read-only and runs by default:

```bash
ansible-playbook playbooks/site.yml --tags pve_host_network
```

Render and stage the pinned link and bridge configuration for one node:

```bash
ansible-playbook playbooks/site.yml --tags pve_host_network \
  --limit <host> -e pve_host_network_enforce=true
```

## Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `pve_host_network_fail_on_drift` | `true` | Fail when the management default route is not on the bridge. |
| `pve_host_network_enforce` | `false` | Write the pinned link and bridge config together. |
| `pve_host_network_bridge` | `vmbr0` | Management bridge. |
| `pve_host_network_uplink` | `nic0` | Stable pinned interface name; must match `nicN`. |
| `pve_host_network_uplink_mac` | empty | Required permanent MAC for the pinned interface. |
| `pve_host_network_address` | current host fact | Management address in CIDR form; set an override when required. |
| `pve_host_network_gateway` | current host fact | Management gateway; set an override when required. |

## Tags

- `pve_host_network`
- `network`

## License

Same as the containing repository.
