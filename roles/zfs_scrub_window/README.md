# zfs_scrub_window

Keep ZFS scrub progress inside a nightly off-peak window. Debian's ZFS cron may
still start a scrub; this role only pauses an active scrub and resumes a paused
scrub, so it never starts a new one.

## Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `zfs_scrub_window_enabled` | `false` | Master switch. |
| `zfs_scrub_window_pools` | `[]` | Pools whose scrubs follow the window. |
| `zfs_scrub_window_resume_oncalendar` | `*-*-* 01:00:00 UTC` | Resume schedule. |
| `zfs_scrub_window_pause_oncalendar` | `*-*-* 07:00:00 UTC` | Pause schedule. |

For each pool, the role renders pause and resume oneshot services with matching
systemd timers. `Persistent=false` prevents a missed event from firing after
boot. Under Docker the units render for verification, while systemd operations
are skipped.
