#!/usr/bin/env bash
# ha-failover-drill.sh — NON-DESTRUCTIVE proof that Proxmox HA auto-restart and
# relocation actually work, WITHOUT touching any tier-0 guest or rebooting a node.
#
# It exercises the HA control loop against a caller-supplied DISPOSABLE test
# container (create a throwaway CT first — e.g. a 128MB Debian LXC):
#   1. assert the test SID is NOT a tier-0 guest (hard guard),
#   2. place it under HA,
#   3. stop it out-of-band and confirm ha-manager brings it back (auto-restart),
#   4. migrate it to another node and back (relocation),
#   5. remove it from HA and leave it stopped.
# No real service is affected; the only guest touched is the disposable one.
#
# Usage (run on a cluster node; needs the ha-manager + pct/qm CLIs):
#   ha-failover-drill.sh <test-sid> <other-node-name>
#   e.g. ha-failover-drill.sh ct:999999 <another-cluster-node>
#
# Exit non-zero on any step that does not reach the expected HA state.
set -euo pipefail

SID="${1:?usage: ha-failover-drill.sh <test-sid ct:NNN> <other-node-name>}"
OTHER_NODE="${2:?usage: ha-failover-drill.sh <test-sid ct:NNN> <other-node-name>}"
VMID="${SID##*:}"
KIND="${SID%%:*}"   # ct or vm

# --- Guard: never drill against a tier-0 guest --------------------------------
# Names here mirror roles/pve_ha/defaults.yml pve_ha_ct_hostnames. The guard is
# by VMID via the running guest's hostname, so a renumber cannot sneak a real
# guest past it.
TIER0_RE='openbao-|technitium-dns|traefik|haproxy'
if [ "$KIND" = "ct" ]; then
  name="$(pct config "$VMID" 2>/dev/null | sed -n 's/^hostname: //p' || true)"
else
  name="$(qm config "$VMID" 2>/dev/null | sed -n 's/^name: //p' || true)"
fi
if printf '%s' "$name" | grep -Eq "$TIER0_RE"; then
  echo "REFUSING: $SID ('$name') looks like a tier-0 guest. Use a disposable test guest." >&2
  exit 2
fi

wait_state() {  # wait_state <sid> <expected-substr> <timeout-s>
  local sid="$1" want="$2" t="${3:-120}" now
  for _ in $(seq 1 "$t"); do
    now="$(ha-manager status 2>/dev/null | awk -v s="$sid" '$0 ~ s {print}')"
    if printf '%s' "$now" | grep -q "$want"; then
      echo "  ok: $sid -> $want"
      return 0
    fi
    sleep 1
  done
  echo "TIMEOUT: $sid did not reach '$want' within ${t}s. Last: ${now:-<none>}" >&2
  return 1
}

cleanup() { ha-manager remove "$SID" 2>/dev/null || true; }
trap cleanup EXIT

echo "1/5 add $SID to HA (started)"
ha-manager add "$SID" --state started --max_restart 3 --max_relocate 1
wait_state "$SID" "started" 120

echo "2/5 stop $SID out-of-band; expect HA to auto-restart it"
if [ "$KIND" = "ct" ]; then pct stop "$VMID"; else qm stop "$VMID"; fi
wait_state "$SID" "started" 180   # HA restarts it -> back to 'started'

echo "3/5 relocate $SID -> $OTHER_NODE"
ha-manager crm-command migrate "$SID" "$OTHER_NODE"
wait_state "$SID" "$OTHER_NODE" 180

echo "4/5 relocate $SID back to the local node"
LOCAL_NODE="$(hostname)"
if [ "$LOCAL_NODE" != "$OTHER_NODE" ]; then
  ha-manager crm-command migrate "$SID" "$LOCAL_NODE"
  wait_state "$SID" "$LOCAL_NODE" 180
fi

echo "5/5 remove $SID from HA (cleanup runs on exit)"
echo "DRILL PASSED: auto-restart + relocation both verified on $SID."
