# git_mirror

Daily bare-mirror of every public repository belonging to a configured list
of GitHub owners, into the generic `<pool>/git-mirror` archive namespace
(see the [`zfs_pools`](../zfs_pools/README.md) role) — the same shape already
proven by [`pve_config_backup`](../pve_config_backup/README.md), applied to
git history.

## Scope: public repositories only (v1)

Repos are cloned/fetched **anonymously over HTTPS** — no credential of any
kind. Mirroring a private repository needs a node-side credential path (an
AppRole scoped to the `github/` engine, minted on this node) that does not
exist yet, and inventing that plumbing under converge pressure is exactly
the kind of unattended credential decision this estate reserves for a human.
Deliberately not built here — tracked as an explicit follow-up.

Public repos are also the IaC-critical ones (`tofu-proxmox`,
`ansible-proxmox`, and everything else under the public tree), so this
already covers what a rebuild actually needs.

## Installation

Ships in `ansible-proxmox`, applied via `playbooks/site.yml`. No separate
install. Inert (`git_mirror_enabled: false`, `git_mirror_owners: []`) unless
set per-host.

## How it works

Daily (`systemd` timer): for each configured owner, enumerate its public
repos via the (unauthenticated) GitHub REST API (`/users/<owner>/repos`,
which lists public repos for an organisation login as well as a user one),
then `git clone --mirror`
any not yet present locally or `git remote update --prune` any that are. No
repo list is baked into the script — a new repo on GitHub is picked up on
the next run with no converge needed. The archive directory sits inside the
existing `<pool>/git-mirror` dataset, so it is snapshotted (`sanoid`) and,
once wired, cross-node replicated (`syncoid`) by the storage layer.

Retention is deliberately unbounded here: `remote update --prune` mirrors
the remote's own branch/tag set, but never deletes a repository directory
that disappears from the owner's public listing (e.g. renamed, transferred,
made private) — a deleted-upstream repo's last-known mirror is exactly the
scenario this role exists for. Removing a stale mirror directory is a
manual, deliberate action, not something this timer does automatically.

## Owner list — environment, not inventory

`git_mirror_owners` holds account names, which are operator-specific
identity, and this repository is public. Inventory therefore reads them from
`GIT_MIRROR_OWNERS` (whitespace-separated logins) rather than declaring them
inline, the same treatment private hostnames get in this inventory. Unset
means an empty list, which leaves the role inert instead of installing a
timer that mirrors nothing.

## Variables

| Variable | Default | Description |
| --- | --- | --- |
| `git_mirror_enabled` | `false` | Master enable — set per-host |
| `git_mirror_owners` | `[]` | Owner logins to mirror — env-sourced per-host, never written into this repo |
| `git_mirror_archive_dir` | `/bulk/git-mirror` | Mirror destination |
| `git_mirror_on_calendar` | `*-*-* 05:15:00` | `systemd` `OnCalendar` (daily) |
| `git_mirror_persistent` | `true` | Run a missed schedule on next boot |
| `git_mirror_healthcheck_url` | `""` | Optional healthchecks.io URL |

## Usage

```bash
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags git_mirror
```

## Restore

A mirrored repository is a normal bare repo — `git clone <path>` it, or
`git remote add origin <path> && git fetch` into a working tree. Verify
`HEAD` matches the real remote (`git ls-remote https://github.com/<owner>/<repo>.git HEAD`)
before relying on a mirror as the source of truth for a rebuild.
