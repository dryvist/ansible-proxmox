# Disaster-Recovery Runbook — warm/hot standby on an intermittent node

Operator runbook for the homelab resiliency program's standby model: a third
node (`<target-node>`, e.g. `proxmox-3`) kept as a continuously-synced standby
so it can take over service if a primary node is lost.

> Placeholders only — no real IPs, domain, or node names. Substitute:
> `proxmox-1` (always-on, infra + SIEM VM), `proxmox-2` (always-on, media on a
> `bulk` ZFS pool), `<target-node>` (the intermittently-online standby).
> `${PROXMOX_SUBDOMAIN}` is the internal subdomain (from Doppler).

## 1. How replication works

- Storage is **node-local ZFS** — no shared storage, no Ceph. Each node has its
  own `bulk` pool; the standby holds empty replica datasets
  (`bulk/replica/proxmox-1`, `bulk/replica/proxmox-2`) declared in
  terraform-proxmox `node_storage`.
- Replication uses **syncoid** (from the `sanoid` package), driven by the
  `zfs_replication` role (and/or the existing `syncoid` role). syncoid ships ZFS
  snapshots incrementally and **tolerates the target being offline**, unlike
  Proxmox-native `pvesr`.
- **Continuous when the standby is up, clean skip when it is down.** The
  `zfs_replication` role probes the standby's reachability before each run. If
  the standby is powered off — its normal steady state — the run is a no-op
  (logged, never a failure). The moment the standby boots, the next timer tick
  brings its replicas current.
- The standby is powered on for maintenance/replication windows via IPMI
  (`idrac_power`) and powers itself back off on a schedule (`node_auto_poweroff`)
  so it is not left running overnight.

## 2. Hot vs warm standby

| Class | Examples | State on the standby | Runs when standby is up? |
| --- | --- | --- | --- |
| **Hot** (stateless) | DNS secondary, reverse proxy / Traefik | Config only; no single-writer data | **Yes** — can actively serve alongside the primary, no split-brain risk |
| **Warm** (single-writer stateful) | Media stack, databases, the SIEM VM | Replicated data, guest **stopped** | **No** — started only during a failover cutover |

The distinction exists to avoid **split-brain**: two copies of a single-writer
service accepting writes at once corrupts state. Hot/stateless services have no
authoritative single writer, so they can run on the standby continuously. Warm
services must have exactly one writer, so the standby copy stays stopped until
the primary is confirmed down.

## 3. Checking replication freshness

On the **source** node (where the `zfs_replication` role runs):

```bash
# Most recent replication log
ls -t /var/log/zfs-replication/ | head -1
tail -n 40 /var/log/zfs-replication/$(date +%Y-%m-%d).log

# Timer status + next run
systemctl status zfs-replication.timer
systemctl list-timers zfs-replication.timer
```

On the **standby** (must be powered on to inspect):

```bash
# Newest snapshot per replicated dataset — the replication high-water mark
zfs list -t snapshot -o name,creation -s creation bulk/replica/proxmox-2/data | tail
zfs list -t snapshot -o name,creation -s creation bulk/replica/proxmox-1 | tail
```

Freshness = age of the newest snapshot on the standby. Expect it to be no older
than the last window the standby was online. A large gap means the standby has
been down (expected) or SSH trust / a source snapshot is missing (investigate).

## 4. Failover cutover (primary lost)

No load balancer — cutover is "start the warm guest on the standby + repoint DNS
A records." Do this only after confirming the primary is genuinely down (avoid
split-brain).

1. **Confirm the primary is down.** Power state via IPMI; do not proceed if it is
   merely unreachable on the network but still running.
2. **Power on the standby** (IPMI / `idrac_power`) if it is off.
3. **Final replica sync if the primary is briefly reachable** — otherwise the
   standby serves from its last replicated snapshot:

   ```bash
   # On the source side, force a run now if the primary is momentarily up
   /usr/local/bin/zfs-replicate.sh
   ```

4. **Promote the warm guest on the standby.** Clone/rollback the latest replica
   snapshot into a runnable dataset, then start the guest (CT/VM):

   ```bash
   pct start <ctid>     # container
   qm start <vmid>      # VM
   ```

5. **Repoint DNS.** Update the A record(s) for the affected service(s) to the
   standby's address. Internal traffic resolves by name
   (`<service>.${PROXMOX_SUBDOMAIN}`), so only the DNS A record changes — no
   client reconfiguration.

   ```bash
   # Example: update the service A record in the DNS manager to the standby IP
   # (Technitium / your DNS authority). TTLs should be low for fast cutover.
   ```

6. **Verify** the service answers on its name, then announce the cutover.

## 5. Fail-back (primary restored)

1. **Bring the primary back** and let it boot, but keep its warm guests
   **stopped** — the standby is currently the single writer.
2. **Reverse-replicate** the now-current data from the standby back to the
   primary (a one-off syncoid run with source/target swapped), so the primary's
   datasets catch up to the writes taken during the outage.
3. **Quiesce on the standby**: stop the warm guest so there is again exactly one
   writer.
4. **Start the guest on the primary**, verify it is healthy and current.
5. **Repoint DNS** A records back to the primary.
6. **Resume normal replication** (primary → standby). Confirm the timer is
   active and the first post-failback run succeeds.

## 6. Guardrails

- **Never run a warm guest on both nodes at once.** One writer, always.
- **Replication is best-effort against an intermittent target** — a down standby
  is a clean skip, not an alert. Alert only on the standby being *up* and
  replication still failing.
- **The replica is not a backup of last resort** — it tracks the source,
  including accidental deletes. Point-in-time recovery comes from sanoid
  snapshot retention (and, optionally, the `vzdump` leg), not from replication.
