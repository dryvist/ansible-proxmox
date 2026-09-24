# Crash Diagnostics Role

Configures kernel crash diagnostics, hardware error monitoring, and memory testing
for Proxmox VE systems.

## What It Does

1. **Installs debugging packages**: kdump-tools, crash, strace, tcpdump, rasdaemon,
   edac-utils, memtest86+, etc.
2. **Configures sysctl settings**: Kernel panic behavior, watchdogs, logging verbosity
3. **Configures GRUB parameters**: Boot-time panic settings via drop-in config
4. **Memory config logging**: Captures DIMM configuration at each boot
5. **Real-time MCE monitoring**: Monitors for hardware errors continuously
6. **memtest86+ boot entry**: Properly configures memtest86+ for ZFS-on-root systems

## Requirements

- Proxmox VE (Debian-based)
- Ansible 2.15+
- `ansible.posix` collection (for mount module)

## Usage

```bash
ansible-playbook -i inventory/hosts.yml playbooks/crash_diagnostics.yml
```

## memtest86+ on ZFS-on-Root Systems

When Proxmox uses ZFS on root with `proxmox-boot-tool`, the standard memtest86+
installation does NOT work because:

1. GRUB loads from a separate FAT32 boot partition (not `/boot/` on ZFS)
2. The memtest86+ package installs to `/boot/` on the ZFS root filesystem
3. GRUB cannot access `/boot/` on ZFS from the boot partition

**Incorrect path** (what the default config generates):

```text
/ROOT/pve-1@/boot/memtest86+x64.bin  # ZFS dataset path - inaccessible from boot partition
```

**Correct path** (what this role configures):

```text
/memtest86+x64.bin  # On FAT32 boot partition, UUID from proxmox-boot-uuids
```

This role automatically:

1. Detects proxmox-boot-tool managed systems via `/etc/kernel/proxmox-boot-uuids`
2. Reads the boot partition UUID
3. Mounts the boot partition temporarily
4. Copies memtest86+x64.bin from `/boot/` to the boot partition
5. Creates `/grub/custom.cfg` with proper menu entries

## Important Notes

- **Reboot required**: GRUB changes only take effect after reboot
- **Uses drop-in configs**: Safe for Proxmox upgrades
- **Removes old configs**: Cleans up legacy sysctl files if present
- **Hardware-only features**: MCE monitoring only runs on physical hardware

## Variables

See `defaults/main.yml` for all configurable options:

- `crash_diagnostics_packages` - List of packages to install
- `crash_diagnostics_sysctl_settings` - Kernel parameters
- `crash_diagnostics_grub_params` - Boot-time kernel parameters
- `crash_diagnostics_memory_log_dir` - Directory for boot-time memory logs
- `crash_diagnostics_mce_log_file` - Real-time MCE monitor log file

## Tags

- `crash_diagnostics` - All tasks
- `packages` - Package installation only
- `sysctl` - Sysctl configuration only
- `grub` - GRUB configuration only
- `rasdaemon` - RAS daemon for hardware error logging
- `memory_logging` - Boot-time memory configuration logging
- `mce_monitor` - Real-time MCE monitoring service
- `memtest` - memtest86+ boot partition installation
- `pstore` - systemd-pstore journal-storage drop-in

## Panic dump forwarding (systemd-pstore)

`systemd-pstore` defaults to `Storage=external`, which only writes captured
EFI/ACPI panic dumps to `/var/lib/systemd/pstore/` — a file never shipped to
Splunk. This role drops in `Storage=journal` (`/etc/pstore.conf.d/`), so the
dump content lands in the journal at boot and rides the same
`pve_syslog_forwarder` path as every other host log. Physical hosts only.
