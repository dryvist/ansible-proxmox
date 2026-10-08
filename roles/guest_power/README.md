# Guest power

Runs one power action on one Proxmox guest, on the node the cluster reports it
is live on: `start`, `stop`, `shutdown`, `reboot`, or `reset` (qemu only).
Transport is the root SSH access the `proxmox` inventory hosts already use; no
Proxmox API token is involved.

The role reads `pvesh get /cluster/resources` from the first `proxmox` node
that answers, requires exactly one guest with the VMID and type, then runs
`qm` or `pct` on the node placement reports and polls `status` until the wanted
state. A start of a running guest or a stop of a stopped guest is a no-op.
Reboot and reset need a running guest. Check mode is refused.

## Usage

```bash
ansible-playbook -i inventory/hosts.yml playbooks/guest-power.yml \
  -e guest_power_vmid=<vmid> -e guest_power_type=qemu -e guest_power_action=reset
```

Target variables have no defaults, so an unscoped run fails before any node is
contacted.
