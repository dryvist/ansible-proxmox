# pve_disk_inventory

Read-only. Gathers every node's physical drives and writes one aggregated
artifact on the controller for Nautobot to ingest.

## Why this exists

Nautobot is the system of record for physical hardware, and `dcim.InventoryItem`
is its native model for a component installed in a device. Nothing populated it,
so there was no record anywhere of which drive sits in which machine — not their
serials, not their capacities, not which pool they belong to.

## Why an artifact and not an API call from Nautobot

This repo already holds SSH certificate access to every node, so `pvesh` runs
locally as root and needs **no Proxmox API token at all**. Reaching the same data
from Nautobot would have meant minting a second Proxmox credential purely so a
read-only job could list disks, plus a new network path from an application guest
to the hypervisor API.

The consumer already reads this repo's `hosts.yml` through `ANSIBLE_PROXMOX_HOSTS`.
The drive artifact travels the same way, through `ANSIBLE_PROXMOX_DRIVES`.

## Why `pvesh` and not `lsblk`

The API returns `serial`, `vendor`, `model`, `wwn`, `type`, `health`, `wearout`
and `used` as first-class fields. A parser over `lsblk` has to re-derive several
of those and gets them wrong in ways that look right:

- NVMe partitions are `nvme0n1p3`, so stripping trailing digits yields `nvme0n1p`
  and **every NVMe silently reads as "not in a pool"**.
- A BMC's virtual media enumerates as a real disk, with a model and a serial
  shared across every host of the same make.
- Removable media is indistinguishable without the removable flag.

None of those failure modes exist here, because the API answers the question
directly.

## A note on SAS serials

For **SAS** drives the API reports the WWN in the `serial` field. This is a
transport limitation, **not** a misconfigured controller: verified on a node
whose HBA is in full passthrough (`smartctl -i` with no `-d megaraid` returns the
real vendor serial, SMART is Available and Enabled, and there are zero RAID
virtual disks). A SATA drive on the *same* controller reports a real serial and a
different WWN.

The consumer detects `serial == wwn` and records **no serial** rather than
writing a fabricated identity that would be indistinguishable from a real one.

## Safety

- Every node command is a read (`changed_when: false`).
- `check_mode: false` on the read, so a dry run does not leave the register empty
  and kill the parse — the `pve_ha` role shipped exactly that defect and made its
  own dry run impossible.
- **A node reporting zero drives fails the play.** The consumer deletes drives it
  stops seeing, so an unnoticed empty result would silently wipe that node's
  inventory. A diskless hypervisor is not a real state; an unreadable API is.
- The artifact is rewritten whole each run, so a drive that left a machine
  disappears from the file rather than lingering because nothing removed it.

## Installation

In-tree role — no external collection or Galaxy install. It is applied from
`playbooks/site.yml` to the Proxmox nodes alongside the other node-level reads,
and skips itself under Docker so molecule scenarios run without a cluster.

## Usage

```bash
# Refresh the drive artifact only, no other roles:
ansible-playbook playbooks/site.yml --tags pve_disk_inventory

# Write it somewhere else (the consumer points at it via ANSIBLE_PROXMOX_DRIVES):
ansible-playbook playbooks/site.yml --tags pve_disk_inventory \
  -e pve_disk_inventory_artifact=/tmp/drives.json
```

The artifact is rewritten whole on every run. Point the Nautobot converge at it:

```bash
export ANSIBLE_PROXMOX_DRIVES="$PWD/.artifacts/drives.json"
```

## Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `pve_disk_inventory_enabled` | `true` | Gate the whole role |
| `pve_disk_inventory_artifact` | `{{ playbook_dir }}/../.artifacts/drives.json` | Controller-side output path |
| `pve_disk_inventory_exclude_types` | `[usb]` | Media types that are not estate storage |
