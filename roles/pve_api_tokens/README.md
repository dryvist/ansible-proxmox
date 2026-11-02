# pve_api_tokens

Mints one scoped Proxmox VE API token per consumer app and publishes it to that
app's OpenBao bucket, `secret/apps/<app>`. OpenBao has no Proxmox secrets
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
2. By default, grants it `pve_api_tokens_role` (`PVEAuditor`) at `/`. Entries
   with `privileges` instead reconcile a named role and grant it only on their
   `acl_paths` with propagation disabled.
3. If the bucket does not already hold a secret for `<app>@pve!ro`, or the
   token is missing from the cluster, removes any unpublished token and
   creates a new one. `privsep` defaults to false (`--privsep 0`); a true entry
   also grants that token the same role on the same paths.
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

## Hatchet kill-test token

The `hatchet-killtest` entry uses `HatchetKillTestPower`, whose only privilege
is `VM.PowerMgmt`. Its paths come from `containers_from_tofu` containers that
carry the dedicated `hatchet-killtest` tag; each entry's `ansible_pct_vmid`
becomes `/vms/<vmid>`. The entry requires exactly two such paths
(`acl_path_count: 2`) and fails, naming the tag source, if the count differs. A
tagged container without a VMID still counts and renders as `/vms/`, which the
per-guest path check refuses, so no ACL is granted. It is the
last consumer, so that failure comes after the read-only tokens. The user and
its privsep token receive the role only on those paths, with `--propagate 0`;
the token's effective rights are bounded by the intersection of both ACL sets.
A live token whose privsep differs is modified in place, keeping its secret.
The token is published to `secret/killtest/hatchet` (the entry's `kv_path`),
outside `secret/apps/*`, as `hatchet_killtest_pve_token_id` and
`hatchet_killtest_pve_token_secret`, with the cluster CA as
`hatchet_killtest_pve_ca`. It has no `--expire`, because no rotation job exists
for these tokens.

The live probe is `tests/access_verification/hatchet_token_probe.yml`. It reads
these inputs from the environment:

- `PVE_API_URL`, `PVE_API_TOKEN_ID` and `PVE_API_TOKEN_SECRET`;
- `PVE_NODE`, and `HATCHET_VMIDS`, both Hatchet VMIDs comma-separated;
- `OTHER_VMID` and `OTHER_GUEST_TYPE` (`qemu` or `lxc`), a guest outside the grant;
- `UNUSED_VMID`, a VMID no guest holds.

Every VMID must be numeric, and all four must differ. In order, the probe then:

1. requires `/version` to return 200 (positive control);
2. requires `/cluster/nextid?vmid=<UNUSED_VMID>` to return that VMID, which
   proves no guest holds it (the endpoint is open to every authenticated
   principal and answers 400 when the VMID is taken);
3. requires 403 from each of: the first Hatchet guest's config read, config
   write and console; the other guest's status read; a power start on
   `UNUSED_VMID`; node config and node storage reads; cluster storage config and
   ACL reads.

No request can change guest state: a too-broad grant fails the start on the
free `UNUSED_VMID` with 500 instead of 403. Read the token secret from OpenBao
at runtime; never put it in shell history or logs.
