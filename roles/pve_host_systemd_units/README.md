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
| `python_virtualenv` | when packages are supplied | — | Existing absolute Python virtualenv used by the service |
| `python_packages` | no | `[]` | Python requirement strings installed into that virtualenv |

When `python_packages` is non-empty, the role installs them before managing the
unit and restarts the unit if the package set changes and its requested state is
`started`. The role does not create application files or carry model identity.
Pass the rendered contract in the same scoped runner invocation that targets
its host.
