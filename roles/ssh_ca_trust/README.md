# ssh_ca_trust

Distribute trust in the OpenBao SSH client CA (the `ssh-certificate-authority`
ADR): automation authenticates with short-TTL SSH certificates signed by the
CA at `ssh-client-ca/`; humans stay on static `authorized_keys` so a CA outage
can never lock a human out.

## Installation

Ships in this repository's roles; no separate install. Applied via
`playbooks/site.yml`, gated inert (`ssh_ca_trust_rollout_enabled: false`)
unless a group flips rollout on for that host class.

## Usage

```bash
doppler run -- ./scripts/run-ansible.sh playbooks/site.yml --tags ssh_ca_trust
```

## What it does

1. Preflights: pinned CA fingerprint + `BAO_ADDR` present, clock
   NTP-synchronized (certificate validity is time-bound).
2. Fetches the CA public key and verifies it against the **pinned
   fingerprint** (`SSH_CA_FINGERPRINT`, recorded from the openbao converge's
   trusted-ceremony output). Fail-closed — never trust-on-first-use.
3. Writes `/etc/ssh/trusted-user-ca-keys.pem` (multi-key: CA rotation appends
   the new issuer via `ssh_ca_trust_extra_ca_keys` first, drops the old after
   cert-TTL drain), the per-user `AuthorizedPrincipalsFile` map under
   `/etc/ssh/principals/`, and a late-numbered `sshd_config.d` drop-in.
4. Proves the **effective** config (`sshd -T`) resolves to the CA directives,
   and that a static root key still authenticates (human lockout guard).
5. On PVE nodes, pushes the same trust into every **running** LXC via `pct`
   (no SSH chicken-and-egg); non-running containers are reported as blockers —
   static-key retirement stays gated on every guest carrying CA trust. Each
   container's sshd is hardened to the same `PasswordAuthentication no` /
   `KbdInteractiveAuthentication no` / principal-scoped `AllowUsers` as a PVE
   node, best-effort installs `openssh-server` on an apt-based guest that
   lacks it, and — where sshd is present — proves the **effective** config
   carries that hardening before recording the container as ready in
   `ssh_ca_trust_lxc_ready` (keyed by CTID; a container without sshd is
   recorded not-ready, never failed over its package manager).

## Principals (default-deny)

| Host class | User | Principals |
| --- | --- | --- |
| PVE node | root | `ansible`, `semaphore` |
| LXC (via pct) | root | `ansible`, `semaphore` |

`ai-agent` is **never** a hypervisor root principal; it reaches guest-level
accounts only where a group opts in via `ssh_ca_trust_principals` /
`ssh_ca_trust_lxc_principals` overrides.

## Variables

See `defaults/main.yml` — notably `ssh_ca_trust_ca_fingerprint` (required,
env `SSH_CA_FINGERPRINT`), `ssh_ca_trust_bao_addr` (env `BAO_ADDR`),
`ssh_ca_trust_extra_ca_keys` (rotation), and the principals maps.
