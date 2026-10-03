# hba_storcli

Install Broadcom/Dell `perccli64` (the storcli-family CLI) and assert every
physical drive behind a MegaRAID-family RAID controller (e.g. Dell PERC
H730P) is genuine Non-RAID/JBOD passthrough, not a single-disk RAID0 virtual
disk. **Fails the converge** on a mismatch — a RAID0-wrapped disk hides
SMART/TLER data and defeats ZFS's own error handling, which matters most for
any pool declared as a reference standard.

## Installation

Ships in the `ansible-proxmox` repository; applied via `playbooks/site.yml`
or invoked directly:

```bash
ansible-playbook playbooks/site.yml --limit pve-r540,localhost --tags hba_storcli
```

If `perccli64` is not already installed, the role downloads it itself from a
pinned, checksum-verified Dell URL — no manual staging needed.

## Why this exists

Indirect evidence (a disk enumerating as `ata-*` by-id and answering a plain
`smartctl -a` including self-test logs) is *suggestive* of JBOD passthrough,
but a single-disk RAID0 virtual disk can present similarly depending on
firmware. The only real confirmation is querying the controller itself.

## Installing perccli64

By default the role downloads `hba_storcli_archive_url` (Dell's PERCCLI
driver page, driver id `tdghn`), verifies it against
`hba_storcli_archive_checksum`, and installs the `.deb` it contains. Bump the
pinned version deliberately — re-verify the checksum on Dell's driver page
before moving it.

For an air-gapped host, set `hba_storcli_package_path` to a locally-reachable
`.deb` instead; this skips the download entirely.

If the binary is already installed (checked at
`hba_storcli_binary_search_paths`), neither path runs.

## Variables

See `defaults/main.yml`. Key ones:

- `hba_storcli_archive_url` / `hba_storcli_archive_checksum` — pinned vendor download (default path)
- `hba_storcli_package_path` — reachable `.deb` path override (air-gapped hosts)
- `hba_storcli_controller_index` — which `/cN` to query (default `0`)
- `hba_storcli_acceptable_states` — drive states treated as true passthrough

## Usage

Run once per host with a MegaRAID-family controller. The role is read-only
against the array itself — it never issues a `zpool`/`zfs` command, only
`perccli64` queries — so it is safe to run at any time, including mid-scrub
or mid-expansion.

## Molecule

`molecule/hba_storcli/` — every task is guarded off under Docker
(`ansible_virtualization_type == 'docker'`), so CI proves the role loads and
converges cleanly without a real controller. **Live drive-mode verification
only happens against real hardware**, not in molecule.
