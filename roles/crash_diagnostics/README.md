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
2. Resolves every listed UUID with `blkid -U`. A UUID whose partition no longer
   exists is a normal state after a boot disk replacement: it is reported once
   per UUID with advice to run `proxmox-boot-tool clean` (never run by this
   role), and the install skips it instead of failing the play
3. Mounts each resolvable boot partition with `state: ephemeral`, so nothing is
   ever written to `/etc/fstab`
4. Copies memtest86+x64.bin from `/boot/` to **every** resolvable boot
   partition, so a mirrored rpool gets the files on all of its ESPs
5. Creates `/grub/custom.cfg` with proper menu entries on each ESP
6. Unmounts each ESP and removes its mount point in an `always:` block, so a
   failed copy never leaves the ESP mounted
7. Removes the legacy `/tmp/ansible-boot-partition` fstab entry on every host
   (older versions wrote a permanent, non-`nofail` line keyed by kernel device
   name that systemd re-mounted at every boot), then unmounts and removes the
   leftover mount point

**UEFI systems**: the GRUB `custom.cfg` mechanism only applies where
proxmox-boot-tool boots through GRUB (legacy BIOS). On UEFI hosts
proxmox-boot-tool installs systemd-boot, which ignores `grub/custom.cfg`, and
`linux16` is BIOS-only — the role skips the ESP install there and prints one
line saying so. The fstab cleanup still runs on UEFI hosts.

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
