# Disaster-Recovery Runbook — cold standby on an intermittent node

Operator runbook for the homelab resiliency program's standby model: a third
node (`<target-node>`) kept as a periodically-synced **cold** standby that holds
independent ZFS replicas of the critical datasets, so it can take over service if
a primary node is lost.

> Placeholders only — no real IPs, domain, or node names. Substitute:
> `proxmox-1` (always-on, infra + SIEM VM), `proxmox-2` (always-on, media + the
> warm-standby `bulk/databases` + `bulk/appdata` namespaces on a `bulk` ZFS pool),
> `<target-node>` (the normally-off offline-DR standby).
> `${PROXMOX_SUBDOMAIN}` is the internal subdomain (from Doppler).

## 1. How replication works

- Storage is **node-local ZFS** — no shared storage, no Ceph. Each node has its
  own `bulk` pool; the standby holds replica datasets
  (`bulk/replica/proxmox-1/...`, `bulk/replica/proxmox-2/...`) declared in
  terraform-proxmox `node_storage`.
- Replication uses **syncoid** (from the `sanoid` package) in **PULL** mode: it
  runs **on the standby** and SSHes out to each source to pull that source's
  sanoid snapshots. Pull-from-backup is safer than push (a compromised source
  cannot reach the backup) and tolerates the source being briefly unreachable.
- The standby is **normally powered off** to save electricity, and runs an
  **autonomous wake → replicate → sleep** cycle:
  - **Wake** — the always-on controller (`proxmox-1`) runs the
    `node_scheduled_wake` systemd timers, which issue an IPMI `chassis power on`
    to the standby's BMC on a schedule (twice a day by default).
  - **Replicate** — the standby replicates **on boot** (`syncoid` role with
    `syncoid_trigger: boot` installs a `syncoid-replicate-on-boot.service`
    oneshot). The wall-clock syncoid cron is deliberately NOT used on the
    standby: it would never fire inside a short power-on window.
  - **Sleep** — the on-boot service chains to the `node_auto_poweroff` oneshot
    via systemd `OnSuccess=`/`OnFailure=`, so the standby powers itself off the
    moment replication finishes (success or failure). A fixed-time
    `node_auto_poweroff` timer (22:00) remains as a guaranteed-off backstop if a
    run ever hangs.
- **Freshness == the last window the standby was online.** Because the standby is
  off most of the day, its replicas are at most as fresh as its most recent wake.
  A gap beyond the expected cadence means the standby failed to wake or syncoid
  failed while it was up (investigate — see §3).

## 2. What is on the standby (and what is not)

| Dataset (on the standby) | Source | Class | Notes |
| --- | --- | --- | --- |
| `bulk/replica/proxmox-1/vm-<id>-disk-0` | SIEM VM OS disk | Warm | Whole-disk zvol |
| `bulk/replica/proxmox-1/vm-<id>-disk-2` | SIEM VM `/opt/splunk` | Warm | Config **and** indexes share this disk — see note |
| `bulk/replica/proxmox-1/subvol-<id>-disk-1` | object-storage (RustFS/MinIO) | Warm | The app-tarball store |
| `bulk/replica/proxmox-2/databases` (recursive) | `bulk/databases` | Warm | Warm-standby DB namespace |
| `bulk/replica/proxmox-2/appdata` (recursive) | `bulk/appdata` | Warm | App config/state (incl. media app identity) |

**Not replicated to the standby** (by design):

- **The media library** (`bulk/data`) — large and re-acquirable; declared with
  `com.sun:auto-snapshot=false` in terraform-proxmox. Not a DR target.
- **Guest definitions** (`/etc/pve/qemu-server/*.conf`, `/etc/pve/lxc/*.conf`).
  syncoid ships **data only**, never the VM/CT config. A failover therefore
  **recreates the guest definition** (terraform-proxmox apply targeting the
  standby, or a manual `qm`/`pct create`) and attaches the cloned data — see §4.
- **SIEM indexed data is acceptable-loss.** The SIEM `/opt/splunk` config is what
  must survive; the indexes ride along on the same disk-2 replica but are volatile
  and re-acquirable. Expect index recovery / fsck on first boot after a restore;
  do not block a cutover on index integrity.

## 3. Checking replication freshness

The standby must be **powered on** to inspect (wait for a wake window, or power it
on out of band via IPMI). All of these run **on the standby** — that is where
syncoid runs in the PULL model.

```bash
# Most recent replication log + the on-boot service result from this boot
ls -t /var/log/syncoid/ | head -1
tail -n 40 /var/log/syncoid/"$(date +%Y-%m-%d)".log     # look for any "FAILED (rc=...)"
systemctl status syncoid-replicate-on-boot.service

# Newest snapshot per replicated dataset — the replication high-water mark
zfs list -t snapshot -o name,creation -s creation -r bulk/replica/proxmox-1 | tail
zfs list -t snapshot -o name,creation -s creation -r bulk/replica/proxmox-2 | tail
```

Freshness = age of the newest snapshot per dataset. Expect it no older than the
last window the standby was online (≈ the wake cadence). A larger gap means the
standby has been down longer than expected (it failed to wake) or SSH trust / a
source snapshot is missing (investigate). A dataset that is **absent** entirely
means that job has never succeeded and needs an initial full send (§4.3).

Integrity (optional, stronger): the standby's newest snapshot for a dataset
should have the **same `zfs get guid`** as the source's snapshot of the same
name, and the two should share at least one common snapshot (an unbroken
incremental chain). Zero common snapshots ⇒ the next pull needs a full reseed.

## 4. Failover cutover (a primary is lost)

No load balancer — cutover is "recreate + start the guest on the standby from its
replica + repoint DNS." Do this only after confirming the primary is genuinely
down (avoid split-brain — one writer, always).

1. **Confirm the primary is down.** Check power state via IPMI; do not proceed if
   it is merely unreachable on the network but still running.
2. **Power on the standby** (IPMI / `idrac_power`) if it is off, and stop it from
   auto-sleeping mid-restore: `systemctl stop node-auto-poweroff.timer` and
   `systemctl mask node-auto-poweroff.service` (the on-boot replicate chains to
   that oneshot on completion). Unmask when the restore is done.
3. **Final replica sync if the primary is briefly reachable** — otherwise the
   standby serves from its last replicated snapshot. Force a pull **on the
   standby**:

   ```bash
   /usr/local/bin/syncoid-replicate.sh          # or, via Ansible:
   # ansible-playbook playbooks/site.yml -l <target-node> -e syncoid_run_now=true
   ```

4. **Promote the guest on the standby.** Because guest **configs are not
   replicated**, recreate the definition, then attach the cloned replica data:

   - **VM (zvol-backed, e.g. the SIEM VM):** clone the latest replica snapshot of
     each disk into a runnable, storage-registered dataset under the standby's
     pool using the expected `vm-<id>-disk-<n>` name, then recreate/rescan the VM
     and start it:

     ```bash
     for n in 0 2; do
       snap=$(zfs list -H -t snapshot -o name -s creation \
                bulk/replica/proxmox-1/vm-<id>-disk-$n | tail -1)
       zfs clone "$snap" bulk/vm-<id>-disk-$n     # into a pool Proxmox storage maps
     done
     # recreate the guest config (terraform-proxmox apply -l <target-node>, or
     # `qm create <id> ...`), then:
     qm rescan --vmid <id>
     qm start <id>
     # SIEM only: indexes are crash-consistent — expect Splunk recovery/fsck on
     # first start; config is intact.
     ```

   - **Container (subvol/bind-mount-backed, e.g. databases / appdata consumers):**
     clone the replica subvol (or a child of `bulk/replica/.../appdata`) into the
     path the container bind-mounts, recreate the CT definition, repoint its bind
     mount at the cloned dataset, then `pct start <ctid>`.

5. **Repoint DNS.** Update the A record(s) for the affected service(s) to the
   standby's address. Internal traffic resolves by name
   (`<service>.${PROXMOX_SUBDOMAIN}`), so only the DNS A record changes — no
   client reconfiguration. Keep TTLs low for fast cutover.
6. **Verify** the service answers on its name, then announce the cutover.

## 5. Fail-back (primary restored)

1. **Bring the primary back** and let it boot, but keep its guests **stopped** —
   the standby is currently the single writer.
2. **Reverse-replicate** the now-current data from the standby back to the
   primary (a one-off syncoid run with source/target swapped), so the primary's
   datasets catch up to the writes taken during the outage.
3. **Quiesce on the standby**: stop the promoted guest so there is again exactly
   one writer.
4. **Start the guest on the primary**, verify it is healthy and current.
5. **Repoint DNS** A records back to the primary.
6. **Resume normal operation on the standby**: unmask `node-auto-poweroff.service`,
   re-enable `node-auto-poweroff.timer`, and let the wake → replicate → sleep
   cycle resume. Confirm the next scheduled wake produces a fresh pull.

## 6. Guardrails

- **Never run a guest on both nodes at once.** One writer, always.
- **A normally-off standby is a clean skip, not an alert.** In the PULL model
  syncoid runs *on the standby*; while it is off there is no run, no log, and no
  failure. Do not alert on "no replication while down" — alert on the standby
  being *up* and replication still failing, or on replicas growing **stale beyond
  the wake cadence** (a freshness deadman tied to a successful on-boot pull is a
  tracked follow-up).
- **The replica is not a backup of last resort** — it tracks the source,
  including accidental deletes. Point-in-time recovery comes from sanoid snapshot
  retention (and, when added, a `vzdump`/PBS leg), not from replication.
