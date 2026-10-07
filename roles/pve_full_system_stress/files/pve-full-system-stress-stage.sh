#!/usr/bin/env bash
# Detached stage supervisor for the pve_full_system_stress role.
set -Eeuo pipefail
run_id=$1 stage=$2 duration=$3 sample_seconds=$4 cpu_limit_c=$5
watch_gpu=$6 campaign_started_at=$7 gpu_vmids_csv=$8 llm_pattern=$9
previous_stage=${10} future_stages_csv=${11} rpool=${12} scratch_file=${13}
lock_path=${14} guard_script=${15}
memory_ecc=${16}
shift 16
log() {
  logger -t pve-full-system-stress -p "$1" -- \
    "pve_full_system_stress run=${run_id} stage=${stage} ${*:2}"
}
declare -a child_pids=()
abort_reason=''
stage_succeeded=false
cancel_future() {
  local future unit
  IFS=',' read -r -a future_array <<< "${future_stages_csv}"
  for future in "${future_array[@]}"; do
    [[ -n "$future" ]] || continue
    unit="pve-full-system-stress-${run_id}-${future}"
    log daemon.err "event=guard_decision guard=future_stage unit=${unit} decision=stop"
    systemctl stop "${unit}.timer" "${unit}.service" >/dev/null 2>&1 || true
  done
}
stop_children() {
  local pid state live
  for pid in "${child_pids[@]}"; do kill -TERM "$pid" >/dev/null 2>&1 || true; done
  for _ in 1 2 3 4 5; do
    live=0
    for pid in "${child_pids[@]}"; do
      state=$(ps -o stat= -p "$pid" 2>/dev/null | tr -d '[:space:]' || true)
      [[ -z "$state" || "$state" == Z* ]] || live=1
    done
    if ((live == 0)); then break; fi
    sleep 1
  done
  for pid in "${child_pids[@]}"; do
    state=$(ps -o stat= -p "$pid" 2>/dev/null | tr -d '[:space:]' || true)
    if [[ -n "$state" && "$state" != Z* ]]; then kill -KILL "$pid" >/dev/null 2>&1 || true; fi
    wait "$pid" >/dev/null 2>&1 || true
  done
  child_pids=()
}
release_lock() {
  if [[ -r "${lock_path}/run-id" ]] && [[ $(cat "${lock_path}/run-id") == "${run_id}" ]]; then
    rm -f "${lock_path}/run-id"
    rmdir "${lock_path}" 2>/dev/null || true
  fi
}
cleanup_scripts() { rm -f -- "$0" "$guard_script"; }
on_exit() {
  local rc=$?
  trap - EXIT TERM INT
  if [[ "$rc" == 0 && "$stage_succeeded" == true ]]; then
    log daemon.info "event=stage_end outcome=success end_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    if [[ "$stage" == combined ]]; then
      log daemon.info "event=campaign_end outcome=success end_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      release_lock
      cleanup_scripts
    fi
  else
    [[ -n "$abort_reason" ]] || abort_reason=stage_failed
    log daemon.err "event=abort reason=${abort_reason}"
    cancel_future
    stop_children
    log daemon.err "event=stage_end outcome=abort reason=${abort_reason} end_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    log daemon.err "event=campaign_end outcome=abort reason=${abort_reason} end_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    release_lock
    cleanup_scripts
  fi
}
on_signal() { abort_reason=runtime_limit_or_signal; exit 143; }
trap on_exit EXIT
trap on_signal TERM INT
abort() { abort_reason=$1; exit 1; }
[[ "$memory_ecc" == true || "$memory_ecc" == false ]] || abort invalid_memory_ecc_value
stage_started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
log daemon.info "event=stage_start start_utc=${stage_started_at} duration_seconds=${duration} memory_ecc=${memory_ecc}"
if [[ "$stage" == memory ]]; then
  log daemon.info "event=campaign_start start_utc=${campaign_started_at} memory_ecc=${memory_ecc}"
fi
if [[ -n "$previous_stage" ]]; then
  if journalctl -t pve-full-system-stress --no-pager -o cat \
    | grep -F "run=${run_id} stage=${previous_stage} event=stage_end" \
    | grep -Fq 'outcome=success'; then
    log daemon.info "event=guard_decision guard=previous_stage decision=clear"
  else
    log daemon.err "event=guard_decision guard=previous_stage decision=abort"
    abort previous_stage_incomplete
  fi
fi
if [[ "$stage" == memory ]]; then
  dimm_layout=$(dmidecode -t memory | awk '
    /Memory Device$/ { device++ }
    /^[[:space:]]*(Locator|Bank Locator|Size|Type|Speed|Configured Memory Speed|Manufacturer|Part Number|Rank):/ {
      gsub(/^[[:space:]]+/, "")
      gsub(/[[:space:]]+/, "_")
      print "dimm=" device " " $0
    }
  ')
  [[ -n "$dimm_layout" ]] || abort dimm_layout_unavailable
  while IFS= read -r line; do log daemon.info "event=dimm ${line}"; done <<< "$dimm_layout"
fi
source "$guard_script"
edac_initial=$(edac_counts "$memory_ecc") || abort edac_counters_unavailable
if [[ "$edac_initial" == not_applicable ]]; then
  log daemon.info "event=edac_guard memory_ecc=false decision=not_applicable"
else
  read -r baseline_ce baseline_ue <<< "$edac_initial"
  ((baseline_ue == 0)) || abort edac_ue_before_stage
  log daemon.info "event=edac_guard memory_ecc=true ue_count=${baseline_ue} decision=clear"
fi
guard_sample
[[ "$stage" != memory ]] || :
component_count=0
while (($#)); do
  [[ "$1" == --component ]] || abort invalid_component_arguments
  shift
  cwd=$1
  shift
  command=()
  while (($#)) && [[ "$1" != --component ]]; do command+=("$1"); shift; done
  [[ -n "${command[*]}" ]] || abort empty_component_command
  if [[ -n "$cwd" ]]; then
    (cd -- "$cwd" && exec "${command[@]}") &
  else
    "${command[@]}" &
  fi
  child_pids+=("$!")
  component_count=$((component_count + 1))
done
((component_count > 0)) || abort no_components_started
log daemon.info "event=workloads_start components=${component_count} runtime_seconds=$((duration - 5))"
next_sample=$((SECONDS + sample_seconds))
while [[ -n "${child_pids[*]}" ]]; do
  remaining=()
  for pid in "${child_pids[@]}"; do
    state=$(ps -o stat= -p "$pid" 2>/dev/null | tr -d '[:space:]' || true)
    if [[ -n "$state" && "$state" != Z* ]]; then
      remaining+=("$pid")
    elif wait "$pid"; then
      :
    else
      abort workload_failed
    fi
  done
  child_pids=("${remaining[@]}")
  [[ -n "${child_pids[*]}" ]] || break
  if ((SECONDS >= next_sample)); then
    guard_sample
    next_sample=$((SECONDS + sample_seconds))
  fi
  sleep 1
done
guard_sample
if [[ -n "$scratch_file" ]]; then rm -f -- "$scratch_file"; fi
stage_succeeded=true
