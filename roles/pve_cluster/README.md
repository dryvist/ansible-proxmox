# pve_cluster

Idempotently **form and join** a Proxmox VE cluster using
[`community.proxmox.proxmox_cluster`][mod] — the IaC-driven wrapper around
`pvecm`, never a raw shell `pvecm`. The primary node creates the cluster on its
compute-VLAN corosync ring 0 (`link0`); secondary nodes join it. Re-running is a
no-op (the module supports check mode / idempotence).

[mod]: https://docs.ansible.com/ansible/latest/collections/community/proxmox/proxmox_cluster_module.html

## Installation

This role ships in the `ansible-proxmox` repository. It depends on the
`community.proxmox` collection (added to `requirements.yml`) and the
`proxmoxer >= 2.0` + `requests` Python libraries (provided by the Nix dev shell):

```bash
git clone https://github.com/dryvist/ansible-proxmox.git
cd ansible-proxmox
ansible-galaxy collection install -r requirements.yml
```

## Safety model

Cluster formation is high-risk and effectively one-directional, so the role is
**inert by default** and triple-guarded:

| Guard | Effect |
| --- | --- |
| `pve_cluster_enabled` (default `false`) | Role does nothing unless explicitly enabled for the run. |
| `pve_cluster_member_hosts` allow-list | Hard-asserts `inventory_hostname` is a declared member before acting. |
| Secondary join params | A joining node aborts unless `master_ip` + `fingerprint` are supplied. |
| Docker skip | All API/`proxmox_cluster` calls skip under `ansible_virtualization_type == 'docker'` for molecule. |

## No magic numbers

Every address comes from inventory or a Doppler/SOPS-injected var — never a
literal in this role:

- `link0` defaults to the host's own `ansible_host` (its compute-VLAN
  connection IP, itself env/SOPS-sourced).
- `master_ip` defaults to the primary's `ansible_host` via `hostvars`.
- API auth (`api_host`/`api_user`/`api_token_*`/`validate_certs`) reads the same
  `PROXMOX_VE_*` env vars Doppler injects for the rest of the pipeline.

## Inputs

```yaml
pve_cluster_enabled: false            # master switch — set true to act
pve_cluster_name: homelab             # cluster name (primary creates it)
pve_cluster_member_hosts: []          # allow-list, e.g. [pve, pve2]
pve_cluster_primary_host: pve         # which inventory host creates the cluster
pve_cluster_role: >-                  # auto: 'primary' on the primary, else 'secondary'
  {{ (inventory_hostname == pve_cluster_primary_host) | ternary('primary', 'secondary') }}
pve_cluster_link0: "{{ ansible_host }}"   # corosync ring 0 (compute VLAN)
pve_cluster_link1: ""                 # optional ring 1 (deferred to cluster v2)
pve_cluster_master_ip: "{{ hostvars[pve_cluster_primary_host].ansible_host }}"
pve_cluster_fingerprint: ""           # primary corosync cert fp — supply at run time
```

`pve_cluster_fingerprint` is host/cluster specific (changes on reinstall) and is
**not committed** — read it from `pvecm status` on the primary and pass via `-e`
or a SOPS-encrypted var.

## Usage

The cluster is formed by `playbooks/cluster.yml`, which targets the primary
first (creates) then secondaries (join). `pve3` is excluded while its
terraform `commissioned` flag is `false` (bad drive).

```bash
# Form the cluster (enable + allow-list supplied at run time, fingerprint via -e)
doppler run -- ansible-playbook -i inventory playbooks/cluster.yml \
  -e pve_cluster_enabled=true \
  -e pve_cluster_fingerprint="<primary fp from pvecm status>"
```

After forming, verify on the primary: `pvecm status` shows the expected nodes
quorate on their compute-VLAN IPs.

## Idempotency

`community.proxmox.proxmox_cluster` is check-mode capable: on an
already-formed/already-joined node it reports no change. The role additionally
reads `proxmox_cluster_status_info` on the primary and asserts the cluster is
quorate. All ZFS-free; under Docker every API task is skipped.
