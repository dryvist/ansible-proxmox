# swap

Configure compressed RAM swap on Proxmox hosts with Debian's
systemd-zram-generator, then retire the legacy ZFS swap zvol.

## Installation

Applied by `playbooks/site.yml` and `playbooks/commission_rack_server.yml`.
Nothing is installed by hand. The role installs `systemd-zram-generator`.

## Usage

```bash
ansible-playbook playbooks/site.yml --tags swap
```

Read-only probes run in check mode. Commands that change swap or ZFS state, and
the asserts, are skipped in check mode. The fstab edit is previewed by
Ansible's check-mode support.

## Variables

Role defaults (`defaults/main.yml`), shared by every node:

| Variable | Value | Purpose |
| --- | --- | --- |
| `swap_zram_size` | `min(ram / 4, 16384)` | zram size, in MiB, from RAM |
| `swap_zram_compression_algorithm` | `zstd` | Compression for the zram device |
| `swap_zram_priority` | `100` | Swap priority for the zram device |

`vm.swappiness` stays managed by the kernel_tuning role.

## Behavior

The role renders `/etc/systemd/zram-generator.conf`, reloads systemd, and
starts `systemd-zram-setup@zram0.service` and `dev-zram0.swap`. It then asserts
that `/dev/zram0` is active in `/proc/swaps`.

Only after that assertion passes does the role retire the legacy ZFS swap
zvol `rpool/swap`:

1. Swap it off if it is active. The kernel lists swap by the resolved device
   node (for example `/dev/zd0`), so the match covers the `/dev/zvol` symlink
   and its target.
2. Remove the exact fstab line the ZFS swap role wrote.
3. Assert the zvol is no longer active swap.
4. Destroy the dataset, only if it exists as a volume.

A re-run changes nothing once the zvol is gone.
