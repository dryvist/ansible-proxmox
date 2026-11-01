# pve_upgrade

Upgrade and reboot PVE nodes with an HA maintenance drain. Set
`pve_node_cpu_vendor` in inventory as a map of PVE node names to `amd` or
`intel`. Available `ansible_processor` facts are a fallback. A running HA VM
without complete vendor and strict affinity data stops the upgrade before
maintenance.

Never live-migrate a VM across CPU vendors. If a VM's strict affinity includes
a different vendor, the drain relocates it cold to an available same-vendor
node. If none is available, the role stops it and lets HA restart it cold
after the source enters maintenance. Same-vendor VMs use the normal live
drain. LXC guests move by restart.
