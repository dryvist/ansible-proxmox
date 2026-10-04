# pve_api_tokens

Mints one read-only Proxmox VE API token per consumer app and publishes it to
that app's OpenBao bucket, `secret/apps/<app>`. OpenBao has no Proxmox secrets
engine, so the token is created here, on the cluster.

## Installation

The role is part of this repository and runs from `playbooks/site.yml`. It
needs:

- OpenBao access from the controller, the same as `nas_storage`.
- An exact create/update/read grant on each `secret/data/apps/<app>` path in
  the ansible-converge policy (ansible-proxmox-apps
  `openbao_credential_publish_apps`).

## Usage

```sh
scripts/run-ansible.sh playbooks/site.yml --tags pve_api_tokens
```

The role acts from one node, `pve_api_tokens_config_host`, because users, ACLs
and tokens are cluster-wide. For each entry in `pve_api_tokens_consumers` it:

1. Ensures a dedicated `<app>@pve` user exists. It has no password, so it
   cannot log in.
2. Grants it `pve_api_tokens_role` (`PVEAuditor`) at `/`.
3. If the bucket does not already hold a secret for `<app>@pve!ro`, or the
   token is missing from the cluster, removes any unpublished token and
   creates a new one with `--privsep 0`.
4. Merges `<field_prefix>_token_id` and `<field_prefix>_token_secret` into the
   bucket, using check-and-set on the version just read.
5. When `certificate_field` is set, publishes the cluster CA into that field
   with a fresh read and check-and-set. The certificate is public; the token
   remains hidden from task output.

A converge where nothing is missing changes nothing. A mint whose publish fails
is minted again on the next converge.

## Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `pve_api_tokens_consumers` | homarr, pve-exporter | Consumers: `app` (bucket and user name), `field_prefix`, and optional `certificate_field` |
| `pve_api_tokens_role` | `PVEAuditor` | Role granted at `/` |
| `pve_api_tokens_realm` | `pve` | Realm of the dedicated users |
| `pve_api_tokens_token_name` | `ro` | Token name under each user |

## Verification

`python3 tests/test_pve_api_tokens.py` pins the mint decision and the OpenBao
read gate.
