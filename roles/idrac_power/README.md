# idrac_power

Power-control a rack server's BMC over IPMI (`ipmitool -I lanplus`). Built to
bring a normally-powered-off node (an offline-DR leg) up at the start of a
`site.yml` run and shut it down gracefully at the end, so its replication/backup
targets are seeded only while it is online.

The `ipmitool` calls are **delegated to a controller node** (`idrac_power_controller`)
that can reach the BMC subnet (`NETWORK_CIDR_BMC`). That controller is **derived,
not hard-coded** — the first node in the shared `PROXMOX_VE_NODES` list that isn't
the target — so no node name lives in the role. The target node itself may be
powered off, so the power op never SSHes to it. The role is **idempotent**: it
queries `chassis power status` first and only acts on a state mismatch.

## Installation

Ships in the `ansible-proxmox` repository; applied via `playbooks/site.yml`
(the auto-cycle plays) or invoked directly. No separate install beyond the repo:

```bash
git clone https://github.com/dryvist/ansible-proxmox.git
cd ansible-proxmox
ansible-galaxy install -r requirements.yml
```

`ipmitool` is installed by the role on the controller node.

## What it does

- `idrac_power_action: on` → powers the target on (if off), then waits for its
  SSH to come up (`wait_for_connection`).
- `idrac_power_action: off` → graceful ACPI `chassis power soft` (if on), then
  polls until the BMC reports power off.
- `idrac_power_action: status` (default) → query only, no change.
- Reconciles the chassis **power-restore policy** on every run, whatever the
  action, so a node that this role never cycles still gets the setting.
- Skipped under Docker (molecule) and when `idrac_power_bmc_host` is unset.

## Power-restore policy

What the chassis does when AC returns after a power loss — the same firmware
setting a Dell PowerEdge BIOS calls **AC Power Recovery**. Defaults to
`always-on`: the alternatives make the return of AC conditional, and a node
nobody is present to press a button on needs the unconditional setting.

It is applied over IPMI (`ipmitool chassis policy`) rather than a vendor BIOS
tool. The BMC applies it immediately — no staged BIOS job, no reboot — and it
works across vendors and BMC generations, including ones with no remote
BIOS-attribute interface at all. It also reuses the credentials and controller
delegation this role already has.

The policy is read back from `ipmitool chassis status` first and set only on a
mismatch. Set `idrac_power_restore_policy: ""` to leave it alone.

A node with **no BMC** has no remote path to this setting: it is a BIOS/UEFI
option ("AC Power Recovery" / "Restore AC Power Loss" → On) set at the console
during commissioning. See `docs/DR_RUNBOOK.md`.

## Variables

| Variable | Default | Description |
| --- | --- | --- |
| `idrac_power_enabled` | `true` | Master enable |
| `idrac_power_autocycle` | `true` | site.yml auto power on/off around the run |
| `idrac_power_action` | `status` | `status` / `on` / `off` (set per caller) |
| `idrac_power_controller` | first non-target node from `PROXMOX_VE_NODES` | Always-on node that runs ipmitool; derived, never hard-coded |
| `idrac_power_boot_timeout` | `720` | Seconds to wait for SSH after power-on (old hardware boots slowly) |
| `idrac_power_off_retries` | `60` | Poll budget (×10s ⇒ 10 min) for graceful off |
| `idrac_power_username` / `_password` | `IDRAC_USERNAME` / `IDRAC_PASSWORD` env | BMC creds (no_log) |
| `idrac_power_bmc_host` | _(unset)_ | Per-host BMC address — FQDN preferred over IP (host_vars / env) |
| `idrac_power_restore_policy` | `always-on` | Chassis state when AC returns; `""` leaves it alone |

## Usage

Auto-cycle is wired into `site.yml` and gated on `pve_power_managed: true` per
host. To disable for a quick run:

```bash
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml -e idrac_power_autocycle=false --limit <always-on-hosts>
```

To power a node on/off directly (e.g. during commissioning):

```bash
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags idrac_power
```

## Scope / follow-up

The graceful power-off runs as the final play; if a run fails mid-way the target
is left powered on (re-run or power off manually). A guaranteed-off (block/always)
refinement is tracked for a future iteration.
