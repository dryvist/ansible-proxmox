# kernel_tuning

Configures kernel tuning parameters for Proxmox systems, including both runtime sysctl settings and boot-time kernel command line parameters.

## Features

### Sysctl Tuning

Optimizes VM and memory management parameters:

- **vm.swappiness**: Prefer RAM over swap (configurable)
- **vm.vfs_cache_pressure**: Optimize directory/inode cache retention
- **vm.dirty_ratio** and **vm.dirty_background_ratio**: NVMe-optimized writeback
- **vm.overcommit_memory**: Memory allocation heuristic

### Boot Parameter Management (Proxmox-specific)

Manages kernel boot parameters via `/etc/kernel/cmdline` (UEFI) or GRUB configuration (Legacy BIOS), and `proxmox-boot-tool refresh`.

**WARNING**: This feature requires Proxmox VE. It will be skipped gracefully on non-Proxmox systems. For UEFI, it requires an existing `/etc/kernel/cmdline` file.

Available boot parameters:

- **clocksource**: Force a clocksource (empty by default — the kernel picks TSC where sound)
- **tsc**: TSC mode override, e.g. `nowatchdog` (empty by default)
- **nosmt**: Disable simultaneous multithreading
- **Crash diagnostics**: nmi_watchdog, softlockup_panic, hung_task_panic, mce, edac_report
- **crashkernel**: kdump reservation (only if `kernel_tuning_manage_crashkernel: true`)

## Role Variables

### Default Variables

See `defaults/main.yml` for complete list. Key variables:

| Variable                            | Default | Purpose                                                    |
| ----------------------------------- | ------- | ---------------------------------------------------------- |
| `kernel_tuning_boot_params_enabled` | `false` | Enable boot parameter management                           |
| `kernel_tuning_clocksource`         | `""`    | Forced clocksource; empty lets the kernel choose           |
| `kernel_tuning_disable_smt`         | `false` | Add `nosmt` parameter                                      |
| `kernel_tuning_manage_crashkernel`  | `false` | Manage crashkernel (conflicts with crash_diagnostics role) |

### Hardware-Specific Settings

Boot parameters are **hardware-specific** and should not be enabled by default for all systems:

- **AMD Zen1 systems**: address the C6-entry TSC trigger via `kernel_tuning_disable_zen_c6` / deep-C-state disabling rather than forcing HPET — forcing HPET measured 76x the per-read cost of TSC (see `defaults/main.yml`)
- **AMD Zen2+ systems**: Generally stable with defaults
- **Intel systems**: May not need special parameters

### Enable for Specific Hosts

Use host_vars or group_vars to enable for specific systems:

```yaml
# host_vars/problematic-proxmox-host.yml
kernel_tuning_boot_params_enabled: true
# Keep TSC and skip the watchdog demotion (see host comments for the tradeoff)
kernel_tuning_tsc_mode: nowatchdog
kernel_tuning_disable_smt: true
```

## Conflict Resolution

### With crash_diagnostics Role

Both `kernel_tuning` and `crash_diagnostics` manage crash-related boot parameters (watchdog, panic settings). To avoid conflicts:

- **Use crash_diagnostics for boot params**: Set `kernel_tuning_boot_params_enabled: false` (default)
- **Use kernel_tuning for boot params**: Set `kernel_tuning_boot_params_enabled: true` and update crash_diagnostics to NOT manage boot params

The `crashkernel` parameter is disabled by default (`kernel_tuning_manage_crashkernel: false`) to prevent conflicts.

## Requirements

- Ansible 2.9+
- Proxmox VE (for boot parameter management)
- Root/sudo access

## Testing

Molecule tests verify sysctl configuration in Docker containers. Boot parameter tests are limited to existence checks since Docker doesn't have `/etc/kernel/cmdline`.

For full boot parameter validation on actual Proxmox systems:

**UEFI systems**, verify:

```bash
cat /etc/kernel/cmdline
```

**Legacy BIOS systems**, verify:

```bash
cat /etc/default/grub.d/99-kernel-tuning.cfg
# Then check final boot parameters:
cat /proc/cmdline
```

## Example Playbook

```yaml
- hosts: all
  roles:
    - role: kernel_tuning
      vars:
        kernel_tuning_swappiness: 10
```

With boot parameters enabled for AMD Zen1:

```yaml
- hosts: zen1_hosts
  roles:
    - role: kernel_tuning
      vars:
        kernel_tuning_boot_params_enabled: true
        kernel_tuning_disable_smt: true
```

## License

Part of ansible-proxmox project
