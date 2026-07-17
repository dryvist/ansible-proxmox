# root_authorized_keys

Declaratively manage the **static human break-glass keys** in
`/root/.ssh/authorized_keys` so they can be **rotated via IaC** instead of a
manual one-off.

This role governs only the operator keys that must survive an OpenBao CA
outage. Automation does not use these — it authenticates with short-TTL
certificates from the OpenBao SSH client CA (see the `ssh_ca_trust` role and the
`ssh-certificate-authority` ADR). The two are complementary: `ssh_ca_trust`
distributes CA *trust*, this role manages the static *authorized_keys*.

## Design

- **Deny-by-default.** No-op unless `root_authorized_keys_enabled: true` for the
  host group AND `root_authorized_keys_present` is non-empty.
- **Not exclusive.** It ensures the declared keys are present and the declared
  retired keys are absent — it never rewrites the file to match a single list,
  so a mistake cannot silently wipe root's access.
- **Fail-closed.** Asserts at least one key is declared present before touching
  anything, and a final lockout guard refuses to finish if root would be left
  with zero static keys.

## Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `root_authorized_keys_enabled` | `false` | Opt in per host group. |
| `root_authorized_keys_present` | `[]` | Full authorized-keys-format lines to ensure present. Populate from the secrets store per group_vars — never commit a real key. |
| `root_authorized_keys_absent` | `[]` | Retired / leaked key(s) to ensure absent. |

## Rotation flow (zero-downtime)

1. Add the **new** key to `root_authorized_keys_present`, converge, and verify a
   break-glass SSH with the new key succeeds.
2. Move the **old** key from `_present` to `root_authorized_keys_absent`,
   converge. The old key is now gone; the lockout guard confirms the new key
   remains.

Both steps are ordinary converges — the old key stays valid throughout step 1,
so there is no window without working break-glass access.
