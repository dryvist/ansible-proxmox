# cluster_ssh_trust

Keeps inter-node **root SSH** working automatically across the Proxmox
cluster. Two independent halves of that trust, both repaired here:

- Seeds each node's `/root/.ssh/known_hosts` with the **current** host keys
  of every cluster peer, by **both hostname and management IP**. Without
  this, root SSH between nodes (syncoid replication, `pvecm`, live migration)
  fails with *Host key verification failed* — after a node rename/reinstall
  (`pve` renamed to `node-a`), or when a peer is trusted by name but native
  migration connects by IP (observed live: `pve-w5900` -> `pve-r540` failed
  by IP, worked by name).
- Repairs the pmxcfs-shared `/etc/pve/priv/authorized_keys` if THIS node's
  own public key has dropped out of it. Current PVE gives every node its own
  per-node keypair (`/root/.ssh/id_rsa` is a real file, not a shared
  symlink); `pvecm updatecerts` is what folds each node's pubkey into that
  shared file. If a node's entry silently disappears from it — observed
  live on `pve-w1700`, `id_rsa` itself untouched — the node can no longer
  authenticate outbound or be authenticated to, and native `qmigrate` fails
  with *Permission denied (publickey,password)* / *Can't connect to
  destination address using public key*.

## Installation

This role ships in the `ansible-proxmox` repository and is applied via
`playbooks/site.yml`. No separate installation is required beyond cloning the
repo and installing collection dependencies:

```bash
git clone https://github.com/dryvist/ansible-proxmox.git
cd ansible-proxmox
ansible-galaxy install -r requirements.yml
```

## What it does

- Runs `ssh-keyscan` for each peer in `cluster_ssh_trust_scan_targets` (every
  peer name plus its resolved management IP) and merges the keys into
  `/root/.ssh/known_hosts`, de-duplicated.
- Peer names are read from **`PROXMOX_VE_NODES`**. The value is tokenised with
  `regex_findall`, so plain comma-separated, bracketed (`[node-a, node-b]`),
  or quoted forms all work. When the variable is absent (e.g. molecule), it
  falls back to the `pve_cluster_members` inventory group. Each peer's IP is
  then resolved from `hostvars[peer].ansible_host`, when the peer matches a
  known inventory host.
- Idempotent: re-runs only report `changed` when a new/rotated key is added.
- Checks whether this node's `/root/.ssh/id_rsa.pub` is present in
  `/etc/pve/priv/authorized_keys`; if not, runs `pvecm updatecerts --force`
  (the vendor-native repair — pve-docs `pvecm(1)`) and fails closed if the
  key is still missing afterwards.
- Restarts `pveproxy`/`pvedaemon` (handler) whenever that repair runs, and
  asserts the certificate pveproxy is serving on `127.0.0.1:8006` matches
  the pinned one at `/etc/pve/local/pve-ssl.pem` — `updatecerts` can
  regenerate the file without the already-running proxy picking it up.
- Then proves it: runs `ssh -n -o BatchMode=yes root@<peer IP> true` against
  every peer's management IP — the exact connection native migration/`pvecm`
  make — and fails closed if any peer is still unreachable. The two checks
  above can both pass while one specific peer pair is still broken (that is
  exactly what `pve-w5900` -> `pve-r540` was), so this is the real proof,
  not an inference from the other two.
- A peer that Ansible already found unreachable gathering facts for this run
  (`cluster_ssh_trust_unreachable_peers`) is excluded from that by-IP proof,
  with a logged warning, instead of failing the assert for every other node
  in the cluster. One offline node must not abort the whole site converge.
  Its `known_hosts`/`authorized_keys` entries are never dropped — the
  `ssh-keyscan` seed only appends and de-duplicates, it never truncates — so
  trust for that peer is simply left as-is, not re-verified. A peer that IS
  reachable but still fails the by-IP check is a genuine, unrelated trust
  break and keeps failing closed.
- Skipped under Docker so molecule can converge.

## Variables

| Variable | Default | Description |
| --- | --- | --- |
| `cluster_ssh_trust_enabled` | `true` | Master enable |
| `cluster_ssh_trust_peers` | from `PROXMOX_VE_NODES` (fallback: `pve_cluster_members`) | Peer hostnames |
| `cluster_ssh_trust_unreachable_peers` | peers unreachable this run | Excluded from the by-IP reachability proof (warned, not failed) |
| `cluster_ssh_trust_peer_ips` | resolved from inventory, minus unreachable peers | Peer management IPs (best-effort) |
| `cluster_ssh_trust_scan_targets` | `peers + peer_ips`, de-duplicated | What `ssh-keyscan` actually scans |

## Usage

```bash
# Applied automatically as part of site.yml; or target it directly:
./scripts/run-ansible.sh playbooks/site.yml --tags cluster_ssh_trust
```

## Scope

This role manages SSH trust and repairs shared authorization entries. It does
not manage keypairs.
