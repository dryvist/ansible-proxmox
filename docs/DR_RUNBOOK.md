# Disaster-Recovery Runbook — guest failover across always-on nodes

Operator runbook for promoting a guest onto a second node that already holds
an independent ZFS replica of the critical datasets, when a primary node is
lost. **All nodes in the cluster are always-on** — there is no power-cycle,
wake, or sleep step anywhere in this procedure.

> Placeholders only — no real IPs, domain, or node names. Substitute:
> `proxmox-1` (always-on, infra + SIEM VM), `proxmox-2` (always-on, media +
> the warm-standby `bulk/databases` + `bulk/appdata` namespaces on a `bulk`
> ZFS pool), `proxmox-3` (always-on, second independent replica target).
> `${PROXMOX_SUBDOMAIN}` is the internal subdomain (from Doppler).

## 1. How replication works

- Storage is **node-local ZFS** — no shared storage, no Ceph. Each node has
  its own `bulk` pool; `proxmox-3` holds replica datasets
  (`bulk/replica/proxmox-1/...`, `bulk/replica/proxmox-2/...`) declared in
  tofu-proxmox `node_storage`.
- Replication uses **syncoid** (from the `sanoid` package) in **PULL** mode:
  it runs **on `proxmox-3`** and SSHes out to each source to pull that
  source's sanoid snapshots. Pull-from-backup is safer than push (a
  compromised source cannot reach the backup) and tolerates the source being
  briefly unreachable.
- Syncoid runs on a **wall-clock timer**, same as every other node — there is
  no boot-triggered or power-window-gated replication anymore. See
  [`DATA_PROTECTION_STANDARD.md`](DATA_PROTECTION_STANDARD.md) for the
  telemetry each run reports.
- **Freshness == the last successful timer run.** A gap beyond the expected
  interval means syncoid failed on that run (investigate — see §3), not that
  the node was offline. There is no "expected to be behind" state.

## 2. What is on `proxmox-3` (and what is not)

| Dataset (on `proxmox-3`) | Source | Class | Notes |
| --- | --- | --- | --- |
| `bulk/replica/proxmox-1/vm-<id>-disk-0` | SIEM VM OS disk | P0 | Whole-disk zvol |
| `bulk/replica/proxmox-1/vm-<id>-disk-2` | SIEM VM `/opt/splunk` | P0 config / P3 index | Config **and** indexes share this disk — see note |
| `bulk/replica/proxmox-1/subvol-<id>-disk-1` | object-storage (RustFS) | P0 | The app-tarball store |
| `bulk/replica/proxmox-2/databases` (recursive) | `bulk/databases` | P0 | Postgres/SQLite archive namespace |
| `bulk/replica/proxmox-2/appdata` (recursive) | `bulk/appdata` | P1 | App config/state (incl. media app identity) |

**Not replicated to `proxmox-3`** (by design — see
[`DATA_PROTECTION_STANDARD.md`](DATA_PROTECTION_STANDARD.md) for the full
class-assignment table):

- **The media library** (`bulk/data`) — P3, large and re-acquirable;
  declared with `com.sun:auto-snapshot=false` in tofu-proxmox.
- **Guest definitions** (`/etc/pve/qemu-server/*.conf`, `/etc/pve/lxc/*.conf`).
  syncoid ships **data only**, never the VM/CT config. A failover therefore
  **recreates the guest definition** (tofu-proxmox apply targeting
  `proxmox-3`, or a manual `qm`/`pct create`) and attaches the cloned data —
  see §4.
- **SIEM indexed data is P3 (acceptable-loss).** The SIEM `/opt/splunk`
  config is what must survive; the indexes ride along on the same disk-2
  replica but are volatile and re-acquirable. Expect index recovery/fsck on
  first boot after a restore; do not block a cutover on index integrity.

## 3. Checking replication freshness

All of these run **on `proxmox-3`** — that is where syncoid runs in the PULL
model.

```bash
# Most recent replication log
ls -t /var/log/syncoid/ | head -1
tail -n 40 /var/log/syncoid/"$(date +%Y-%m-%d)".log     # look for any "FAILED (rc=...)"
systemctl status syncoid-replicate.timer

# Newest snapshot per replicated dataset — the replication high-water mark
zfs list -t snapshot -o name,creation -s creation -r bulk/replica/proxmox-1 | tail
zfs list -t snapshot -o name,creation -s creation -r bulk/replica/proxmox-2 | tail
```

Freshness = age of the newest snapshot per dataset, checked against the
mechanism's `.status` line per `DATA_PROTECTION_STANDARD.md`. Any gap beyond
the timer interval means the run failed (SSH trust or a source snapshot is
missing — investigate). A dataset that is **absent** entirely means that job
has never succeeded and needs an initial full send (§4.3).

Integrity (optional, stronger): `proxmox-3`'s newest snapshot for a dataset
should have the **same `zfs get guid`** as the source's snapshot of the same
name, and the two should share at least one common snapshot (an unbroken
incremental chain). Zero common snapshots ⇒ the next pull needs a full reseed.

## 4. Failover cutover (a primary is lost)

No load balancer — cutover is "recreate + start the guest on `proxmox-3` from
its replica + repoint DNS." Do this only after confirming the primary is
genuinely down (avoid split-brain — one writer, always).

1. **Confirm the primary is down.** Check power state via IPMI; do not
   proceed if it is merely unreachable on the network but still running.
2. **Final replica sync if the primary is briefly reachable** — otherwise
   `proxmox-3` serves from its last replicated snapshot. Force a pull **on
   `proxmox-3`**:

   ```bash
   /usr/local/bin/syncoid-replicate.sh          # or, via Ansible:
   # ansible-playbook playbooks/site.yml -l proxmox-3 -e syncoid_run_now=true
   ```

3. **Promote the guest on `proxmox-3`.** Because guest **configs are not
   replicated**, recreate the definition, then attach the cloned replica
   data:

   - **VM (zvol-backed, e.g. the SIEM VM):** clone the latest replica
     snapshot of each disk into a runnable, storage-registered dataset under
     `proxmox-3`'s pool using the expected `vm-<id>-disk-<n>` name, then
     recreate/rescan the VM and start it:

     ```bash
     for n in 0 2; do
       snap=$(zfs list -H -t snapshot -o name -s creation \
                bulk/replica/proxmox-1/vm-<id>-disk-$n | tail -1)
       zfs clone "$snap" bulk/vm-<id>-disk-$n     # into a pool Proxmox storage maps
     done
     # recreate the guest config (tofu-proxmox apply -l proxmox-3, or
     # `qm create <id> ...`), then:
     qm rescan --vmid <id>
     qm start <id>
     # SIEM only: indexes are crash-consistent — expect Splunk recovery/fsck on
     # first start; config is intact.
     ```

   - **Container (subvol/bind-mount-backed, e.g. databases / appdata
     consumers):** clone the replica subvol (or a child of
     `bulk/replica/.../appdata`) into the path the container bind-mounts,
     recreate the CT definition, repoint its bind mount at the cloned
     dataset, then `pct start <ctid>`.

   - **Database data (any engine):** rebuild the guest via its role, then
     restore the newest logical dump from `bulk/databases/<instance>` (or the
     Tier-2 cloud copy) per [`DATABASE_DR_STANDARD.md`](./DATABASE_DR_STANDARD.md) —
     do not clone the live DB volume; the dumps are the app-consistent artifact.

4. **Repoint DNS.** Update the A record(s) for the affected service(s) to
   `proxmox-3`'s address. Internal traffic resolves by name
   (`<service>.${PROXMOX_SUBDOMAIN}`), so only the DNS A record changes — no
   client reconfiguration. Keep TTLs low for fast cutover.
5. **Verify** the service answers on its name, then announce the cutover.

## 5. Fail-back (primary restored)

1. **Bring the primary back** and let it boot, but keep its guests
   **stopped** — `proxmox-3` is currently the single writer.
2. **Reverse-replicate** the now-current data from `proxmox-3` back to the
   primary (a one-off syncoid run with source/target swapped), so the
   primary's datasets catch up to the writes taken during the outage.
3. **Quiesce on `proxmox-3`**: stop the promoted guest so there is again
   exactly one writer.
4. **Start the guest on the primary**, verify it is healthy and current.
5. **Repoint DNS** A records back to the primary.
6. **Resume normal operation on `proxmox-3`**: confirm its regular syncoid
   timer produces a fresh pull on its next scheduled run.

## 6. Guardrails

- **Never run a guest on both nodes at once.** One writer, always.
- **Every node is always-on; silence from any of them is a failure, not an
  expected state.** Unlike a node that is deliberately offline on a
  schedule, there is no "clean skip" case here — a missing or stale
  `.status` line for a syncoid job means the job failed, full stop. Alerting
  follows the telemetry contract in
  [`DATA_PROTECTION_STANDARD.md`](DATA_PROTECTION_STANDARD.md): absence is
  caught by the Splunk left-join against `data_protection_expected.csv`, not
  by a per-node "is it supposed to be down" exception.
- **The replica is not a backup of last resort** — it tracks the source,
  including accidental deletes. Point-in-time recovery comes from sanoid
  snapshot retention, not from replication.
