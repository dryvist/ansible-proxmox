# Container start

Starts explicitly approved LXC guests with `pct start` over SSH on the node
each guest is currently placed on. This role cannot stop, restart, create,
delete, or enroll a guest in HA.

The allowlist is keyed by the service name in the published `tofu-proxmox`
inventory. The role reads `pvesh get /cluster/resources` from the first
`proxmox` node that answers, requires exactly one LXC with the declared VMID
and hostname, logs the decision for each guest (already running, or start),
then runs `pct start` and `pct status` on the node that placement reports. The
default allowlist is empty, so an unscoped run touches no node.

## Installation

Part of this repository's roles; no separate install. Transport is the same root SSH access the `proxmox` inventory hosts already
use; no Proxmox API token is involved.

## Usage

```bash
doppler run -- ansible-playbook -i inventory/hosts.yml \
  playbooks/container-start.yml \
  -e '{"container_start_services":["service-name"]}'
```

`site.yml` imports `playbooks/container-start.yml`, so the allowlist declared in
`inventory/group_vars` is applied on every site converge.
