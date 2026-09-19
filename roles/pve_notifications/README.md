# pve_notifications

Adds an ntfy webhook target and matchers to Proxmox VE's native notification
system (`/etc/pve/notifications.cfg`) so **vzdump failures, HA fencing,
replication failures, and available package updates** page ntfy — no custom
script, pure PVE-native config via `pvesh`.

## Installation

Ships with this repo. Reference it from a play (see `playbooks/site.yml`):

```yaml
- hosts: proxmox
  roles:
    - role: pve_notifications
```

## Usage

Enabled by default (`pve_notifications_enabled: true`) and additive-only, so
no explicit opt-in is required:

```bash
doppler run -- ansible-playbook -i inventory playbooks/site.yml --tags pve_notifications
```

Runs on a **single** node (`pve_notifications_config_host`) because
`/etc/pve/notifications.cfg` is cluster-wide state, replicated by pmxcfs.

### Why `pvesh`, not a template

The config file already carries a `proxman` webhook target (confirmed firing
today — see `roles/common/defaults/main.yml`). A whole-file `template` would
silently drop that target and anything else this role doesn't own, the same
trap `pve_ha`'s `datacenter_cfg.yml` documents for `datacenter.cfg`. This
role only ever calls `pvesh get/create/set` against the specific target and
matcher names it owns, so unrelated config is untouched.

## Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `pve_notifications_enabled` | `true` | Set false to disable. |
| `pve_notifications_config_host` | cluster primary | Single node the `pvesh` calls run on. |
| `pve_notifications_ntfy_target` | `ntfy-proxmox` | Webhook target name. |
| `pve_notifications_ntfy_url` | ntfy publish URL for topic `proxmox` | derived from `domain_from_tofu`. |
| `pve_notifications_matchers` | vzdump-failed, fencing, replication-failed, package-updates | `{name, type, severity?}` matchers routed at the target. |

`domain_from_tofu` is injected by `playbooks/load_tofu.yml` on every proxmox
host — run this role via `site.yml`, not standalone.

## Verification

No live converge is run by this role's authoring session (no credentials
sought). Reasoned idempotency: `pvesh get` on the target/matcher name decides
create vs. skip/update; a second run against an already-configured cluster
issues no `create`.

`molecule/pve_notifications` covers two things separately, since Docker's
`ansible_virtualization_type` makes the role's whole task block skip (same
idiom as `pve_cluster`/`pve_ha`): `converge.yml` proves the Docker-skip guard
holds and the role runs cleanly with no live cluster touched; `verify.yml`
does **not** exercise a real `pvesh` call (there is no PVE API in CI) — it
re-renders the matcher-create `argv` Jinja-native-list construct directly
with representative variables and asserts on its structure (both the
severity and no-severity shapes). It proves the Jinja is syntactically sound,
not that `pvesh create` accepts the resulting argv against a live cluster.
