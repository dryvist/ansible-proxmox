# pve_host_network

Detects, and optionally enforces, the host network contract on hypervisor
nodes.

## What It Does

Verifies that the host management address lives on the **untagged bridge**,
never on a tagged VLAN sub-interface. The bridge stays VLAN-aware so guests
tag into any VLAN, but the host itself is untagged and therefore matches the
switch port's native VLAN.

Detection is read-only and always runs. Enforcement renders
`/etc/network/interfaces` from a template and is opt-in.

## The Failure This Prevents

If the management address sits on a tagged sub-interface while the switch port
delivers untagged frames, inbound traffic lands on a bridge that has no
address and is silently dropped. The host can **transmit** but never
**receive**.

Every standard liveness probe is unicast — ICMP, SSH, the API, cluster
membership — so all of them fail and the node looks powered off while it is in
fact running normally. There is no panic, no crash dump and no hardware event,
because nothing has actually failed. Without this check the symptom is easily
mistaken for dead hardware.

## Requirements

- Debian-family host using `ifupdown2` (shipped by the hypervisor platform).
- Facts gathered, for default-route and bridge interface resolution.

## Installation

Included from the site play; no separate installation step. To run it alone:

```bash
ansible-playbook playbooks/site.yml --tags pve_host_network
```

## Usage

Detect drift across all nodes (read-only, the default):

```bash
ansible-playbook playbooks/site.yml --tags pve_host_network
```

Render the interfaces file on one host without applying it:

```bash
ansible-playbook playbooks/site.yml --tags pve_host_network \
  --limit <host> -e pve_host_network_enforce=true
```

Render and apply it live:

```bash
ansible-playbook playbooks/site.yml --tags pve_host_network \
  --limit <host> -e pve_host_network_enforce=true -e pve_host_network_apply=true
```

## Modes

| Variable | Default | Effect |
| --- | --- | --- |
| `pve_host_network_fail_on_drift` | `true` | Fail the play when the address is not on the bridge. |
| `pve_host_network_enforce` | `false` | Render `/etc/network/interfaces` from the template. |
| `pve_host_network_apply` | `false` | Apply a rendered change live via `ifreload -a`. |

Enforcement is off by default because a bad render disconnects a node with no
remote way back in; writing the file and applying it are deliberately separate
flags.

When enforcing, the role refuses to proceed without an explicit address,
gateway and uplink, takes a timestamped backup, and validates that the
rendered file contains an address line before installing it.

## Variables

Addresses are supplied from inventory or the environment and are never
committed to this repository. The uplink is resolved from facts unless
overridden per host. See `defaults/main.yml`.

## Tags

- `pve_host_network`
- `network`

## API

None. This role exposes no callable interface; it is consumed through the site
play and the variables above.

## Contributing

Changes follow the repository's standard flow: feature branch, `ansible-lint`
clean, molecule scenario where applicable, conventional-commit subject.

## License

Same as the containing repository.
