# pve_host_systemd_units

Installs application-owned, secret-free systemd unit contracts on Proxmox
hosts. The owning application profile renders each unit; this role only
installs the supplied content and manages the requested state.

`pve_host_systemd_units_contracts` defaults to an empty list. Each supplied item has:

| Key | Required | Default | Purpose |
| --- | --- | --- | --- |
| `name` | yes | — | A systemd `.service` unit name |
| `content` | yes | — | Complete unit text with `[Unit]`, `[Service]`, and `ExecStart` |
| `state` | no | `stopped` | `started` or `stopped` |
| `enabled` | no | `false` | Whether the unit starts at boot |

The role does not create application files, install packages, or carry model
identity. Pass the rendered contract in the same scoped runner invocation that
targets its host.
