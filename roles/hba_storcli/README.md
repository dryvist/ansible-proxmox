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

Staging the `perccli64` package (manual, one-time per estate) is required
first — see "Why this exists" below.

## Why this exists

Indirect evidence (a disk enumerating as `ata-*` by-id and answering a plain
`smartctl -a` including self-test logs) is *suggestive* of JBOD passthrough,
but a single-disk RAID0 virtual disk can present similarly depending on
firmware. The only real confirmation is querying the controller itself.

Dell does not publish a stable, anonymously-fetchable URL for `perccli` — it
sits behind an interactive driver-details page on Dell's support site, and
the package name/version changes per refresh. This role therefore does
**not** attempt to auto-download it:

1. Download the Linux PERCCLI `.tar.gz`/`.rpm` from Dell's PERCCLI driver
   page (search "Dell PERCCLI Linux" — driver IDs `wd0r5` / `f48c2` at time
   of writing).
2. If only an RPM is offered: `alien -k -d <file>.rpm` to produce a `.deb`.
3. Place the resulting `.deb` somewhere this role's target host can reach
   (the estate's binaries/ISO store, or a path served over the existing
   internal file distribution).
4. Set `hba_storcli_package_path` to that reachable path.

If the binary is already installed (checked at
`hba_storcli_binary_search_paths`), staging is skipped entirely.

## Variables

See `defaults/main.yml`. Key ones:

- `hba_storcli_package_path` — reachable `.deb` path (required unless already installed)
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
