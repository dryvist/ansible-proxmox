# Guest power

Runs one power action on one Proxmox guest, on the node the cluster reports it
is live on: `start`, `stop`, `shutdown`, `reboot`, or `reset` (qemu only).
Transport is the root SSH access the `proxmox` inventory hosts already use; no
Proxmox API token is involved.

The role reads `pvesh get /cluster/resources` from the first `proxmox` node
that answers, requires exactly one guest with the VMID and type, then runs
`qm` or `pct` on the node placement reports and polls `status` until the wanted
state. `playbooks/guest-power.yml` then reads the state back on that node in a
play of its own, so the node appears in the play recap. A start of a running
guest or a stop of a stopped guest is a no-op.
Reboot and reset need a running guest. Check mode is refused.

## Usage

```bash
ansible-playbook -i inventory/hosts.yml playbooks/guest-power.yml \
  -e guest_power_vmid=<vmid> -e guest_power_type=qemu -e guest_power_action=reset
```

Target variables have no defaults, so an unscoped run fails before any node is
contacted.

## Node-wide start and stop

Use after a node boots without quorum and its boot-time startall aborted; the
node then starts its onboot guests in startup order. Semaphore template
`proxmox-guest-power`: survey action `startall` or `stopall`, `guest_power_node`
(a `proxmox` inventory host), optional `guest_power_vms` (comma VMIDs). Leave
the VMID and type blank.

`startall` refuses a node whose `pvecm status` is not quorate. The action runs
as the node's own task and the play returns its UPID; it does not wait for
completion, so check the node task log. To revert `startall`, run `stopall`
with the same `guest_power_vms`.
