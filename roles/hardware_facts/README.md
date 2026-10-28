# hardware_facts

Read-only. Reports what a machine physically contains: board, CPU, memory modules,
PCI devices, GPUs, drives, server power supplies and the storage pools drives belong to.

It works on any inventory host or group, so a new machine is a new inventory entry,
not a code change.

## Installation

In-tree role. No external collection or Galaxy install. `playbooks/hardware-facts.yml`
applies it to the hosts named in `hardware_facts_hosts`.

## Usage

```bash
# Report two categories for one host in the run log. Nothing is written.
ansible-playbook playbooks/hardware-facts.yml --limit '<host>,localhost' \
  -e hardware_facts_hosts=<host> -e hardware_facts_categories=memory,psu

# Everything, for a whole group, as one controller-side JSON file.
ansible-playbook playbooks/hardware-facts.yml --limit '<group>,localhost' \
  -e hardware_facts_hosts=<group> -e hardware_facts_output=artifact \
  -e hardware_facts_group=<group>
```

The Semaphore template `hardware-facts` runs the same playbook with the same three
survey values. It is marked non-mutating.

## What it reads

| Category | Source |
| --- | --- |
| `board`, `cpu` | `setup` hardware facts |
| `memory` | `dmidecode --type 17`, empty slots dropped |
| `psu` | `dmidecode --type 39` (server supplies only) |
| `pci`, `gpus` | `lspci` through the shared probe |
| `disks` | `pve_disk_inventory` on Proxmox nodes, `ansible_devices` elsewhere |
| `pools` | the `used` field of the drives above |

A desktop power supply reports nothing over SMBIOS, so it cannot appear here. Record
it by hand.

## Why it reuses what it does

- **Drives.** On Proxmox nodes the role includes `pve_disk_inventory` with
  `pve_disk_inventory_publish: false`. The same code reads the same API, and the role
  can never overwrite the drive artifact a consumer deletes against.
- **`lspci`.** `tasks/lspci.yml` is the one PCI probe. `nvidia_driver` and
  `hba_storcli` call it with `include_role` and `tasks_from: lspci`, and still read
  their own result variables.
- **Facts.** `setup` with `gather_subset` and `filter` covers board and CPU; no task
  re-parses `/proc`.

## Safety

- Every command is a read (`changed_when: false`, `check_mode: false`).
- The default output is the run log only. `artifact` writes one file, kept apart from
  `drives.json`, rewritten whole each run.
- With `hardware_facts_group` set, a run that targeted fewer hosts than that group
  refuses to write the artifact, unless `hardware_facts_allow_partial` is true.
- A missing `dmidecode` or `lspci` yields an empty category, not a failed run.

## Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `hardware_facts_categories` | `[]` (all) | List or comma-separated string of categories |
| `hardware_facts_output` | `report` | `report` or `artifact` |
| `hardware_facts_artifact` | `{{ playbook_dir }}/../.artifacts/hardware-facts.json` | Controller-side output path |
| `hardware_facts_group` | `""` | Group the artifact must cover in full |
| `hardware_facts_allow_partial` | `false` | Write the artifact for a partial run |
| `hardware_facts_proxmox_group` | `proxmox` | Hosts disk-inventoried through the Proxmox API |
| `hardware_facts_disk_ignore_prefixes` | loop, ram, zd, dm-, sr, fd, nbd | Device names that are not drives |
| `hardware_facts_gpu_classes` | VGA, 3D, Display | `lspci` class names counted as GPUs |
| `hardware_facts_dmi_memory_fields` | locator, size, type, speed, part, serial | Kept from DIMM records |
| `hardware_facts_dmi_psu_fields` | name, location, status, capacity, model | Kept from supply records |

## Tests

```bash
ansible-playbook tests/hardware_facts/verify.yml -i localhost, -c local
```

Offline: synthetic `dmidecode`, `lspci` and `ansible_devices` fixtures, no host contacted.
