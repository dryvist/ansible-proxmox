#!/usr/bin/env bash
# Hardware, serving-unit, and telemetry guards for the detached stage supervisor.
edac_counts() {
  local memory_ecc=${1:-true} root=${2:-/sys/devices/system/edac/mc}
  local file value ce=0 ue=0 found_ue=0
  [[ "$memory_ecc" == true || "$memory_ecc" == false ]] || return 2
  if [[ "$memory_ecc" == false ]]; then
    printf 'not_applicable\n'
    return 0
  fi
  shopt -s nullglob
  for file in "$root"/*/ce_count; do
    [[ -r "$file" ]] || continue
    value=$(cat "$file") || return 2
    [[ "$value" =~ ^[0-9]+$ ]] || return 2
    ce=$((ce + value))
  done
  for file in "$root"/*/ue_count; do
    [[ -r "$file" ]] || continue
    value=$(cat "$file") || return 2
    [[ "$value" =~ ^[0-9]+$ ]] || return 2
    ue=$((ue + value))
    found_ue=1
  done
  ((found_ue == 1)) || return 2
  printf '%s %s\n' "$ce" "$ue"
}
kernel_counts() {
  local events
  events=$(journalctl -k --since "$campaign_started_at" --no-pager -o cat) || return 2
  mce_count=$(grep -Eic 'mce:|machine check|hardware error|uncorrected|EDAC.*(UE|uncorrected)' <<< "$events" || true)
  xid_count=$(grep -Eic 'NVRM.*Xid|Xid [0-9]+' <<< "$events" || true)
}
serving_guard() {
  local running vmid active
  local -a declared_vmids
  IFS=',' read -r -a declared_vmids <<< "$gpu_vmids_csv"
  running=$(pct list | awk '$2 == "running" {print $1}') || return 2
  for vmid in "${declared_vmids[@]}"; do
    [[ -n "$vmid" ]] || continue
    grep -Fxq "$vmid" <<< "$running" || continue
    active=$(pct exec "$vmid" -- systemctl list-units --type=service --state=active --no-legend --no-pager) || return 2
    if grep -Eiq "$llm_pattern" <<< "$active"; then return 1; fi
  done
}
sample_cpu() {
  local sensor name input value count=0 max=0 alarm=0 throttle=0 throttle_found=0 min_freq=0
  shopt -s nullglob
  for sensor in /sys/class/hwmon/hwmon*; do
    [[ -r "$sensor/name" ]] || continue
    name=$(cat "$sensor/name")
    [[ "$name" == k10temp ]] || continue
    for input in "$sensor"/temp*_input; do
      [[ -r "$input" ]] || continue
      value=$(cat "$input") || return 2
      [[ "$value" =~ ^[0-9]+$ ]] || return 2
      ((value > max)) && max=$value
      count=$((count + 1))
    done
    for input in "$sensor"/temp*_crit_alarm; do
      [[ ! -r "$input" || $(cat "$input") != 1 ]] || alarm=1
    done
  done
  ((count > 0)) || return 2
  for input in /sys/devices/system/cpu/cpu*/thermal_throttle/*_throttle_count; do
    [[ -r "$input" ]] || continue
    value=$(cat "$input") || return 2
    throttle=$((throttle + value))
    throttle_found=1
  done
  [[ "$throttle_found" == 1 ]] || throttle=unavailable
  for input in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq; do
    [[ -r "$input" ]] || continue
    value=$(cat "$input") || return 2
    if ((min_freq == 0 || value < min_freq)); then min_freq=$value; fi
  done
  ((min_freq > 0)) || min_freq=unavailable
  logger -t pve-full-system-stress -p daemon.info -- \
    "pve_full_system_stress run=${run_id} stage=${stage}" \
    "event=sample cpu_temp_mC=${max} cpu_temp_limit_mC=$((cpu_limit_c * 1000))" \
    "cpu_throttle_count=${throttle} cpu_min_freq_khz=${min_freq}"
  ((max < cpu_limit_c * 1000 && alarm == 0)) || return 1
}
sample_gpu() {
  local data limit_text gpu_temp power sm_clock mem_clock throttle limit
  data=$(nvidia-smi --query-gpu=temperature.gpu,power.draw,clocks.gr,clocks.mem,clocks_throttle_reasons.active --format=csv,noheader,nounits) || return 2
  [[ "$data" != *$'\n'* ]] || return 2
  IFS=',' read -r gpu_temp power sm_clock mem_clock throttle <<< "$data"
  gpu_temp=${gpu_temp//[[:space:]]/}
  power=${power//[[:space:]]/}
  sm_clock=${sm_clock//[[:space:]]/}
  mem_clock=${mem_clock//[[:space:]]/}
  throttle=${throttle//[[:space:]]/}
  [[ "$gpu_temp" =~ ^[0-9]+$ && "$power" =~ ^[0-9]+([.][0-9]+)?$ \
    && "$sm_clock" =~ ^[0-9]+$ && "$mem_clock" =~ ^[0-9]+$ ]] || return 2
  limit_text=$(nvidia-smi -q -d TEMPERATURE) || return 2
  limit=$(awk -F: 'tolower($1) ~ /gpu max operating temp/ {gsub(/[[:space:]cC]/, "", $2); print $2; exit}' <<< "$limit_text")
  [[ "$limit" =~ ^[0-9]+$ ]] || return 2
  logger -t pve-full-system-stress -p daemon.info -- \
    "pve_full_system_stress run=${run_id} stage=${stage}" \
    "event=sample gpu_temp_c=${gpu_temp} gpu_temp_limit_c=${limit}" \
    "gpu_power_w=${power} gpu_sm_clock_mhz=${sm_clock}" \
    "gpu_mem_clock_mhz=${mem_clock} gpu_throttle_active=${throttle}"
  ((gpu_temp < limit)) || return 1
}
sample_nvme() {
  local leaves leaf parent device smart warning temperature warning_hex index=0
  leaves=$(zpool status -P "$rpool" | awk '$1 ~ /^\/dev\// {print $1}') || return 2
  [[ -n "$leaves" ]] || return 2
  while IFS= read -r leaf; do
    parent=$(lsblk -nro PKNAME -- "$leaf" | head -1) || return 2
    device=$leaf
    [[ -z "$parent" ]] || device="/dev/${parent}"
    # JSON output is unit-stable: the text form follows nvme-cli's display
    # settings (Celsius or Fahrenheit), while JSON reports Kelvin.
    smart=$(nvme smart-log --output-format=json "$device") || return 2
    warning=$(grep -oE '"critical_warning"[[:space:]]*:[[:space:]]*[0-9]+' <<< "$smart" | grep -oE '[0-9]+$' | head -1)
    temperature=$(grep -oE '"temperature"[[:space:]]*:[[:space:]]*[0-9]+' <<< "$smart" | grep -oE '[0-9]+$' | head -1)
    [[ "$warning" =~ ^[0-9]+$ && "$temperature" =~ ^[0-9]+$ ]] || return 2
    warning_hex=$(printf '%x' "$warning")
    temperature=$((temperature - 273))
    logger -t pve-full-system-stress -p daemon.info -- \
      "pve_full_system_stress run=${run_id} stage=${stage}" \
      "event=sample nvme_device_index=${index} nvme_temp_c=${temperature}" \
      "nvme_critical_warning=${warning}"
    ((16#${warning_hex} == 0)) || return 1
    index=$((index + 1))
  done <<< "$leaves"
}
guard_sample() {
  local edac mce_count=0 xid_count=0 rc edac_decision=clear
  edac=$(edac_counts "$memory_ecc") || { abort edac_counters_unavailable; }
  if [[ "$edac" == not_applicable ]]; then
    current_ce=unavailable current_ue=unavailable edac_decision=not_applicable
  else
    read -r current_ce current_ue <<< "$edac"
    ((current_ue == 0)) || { abort edac_ue; }
  fi
  kernel_counts || { abort kernel_journal_unavailable; }
  ((mce_count == 0)) || { abort mce_detected; }
  ((xid_count == 0)) || { abort xid_detected; }
  if serving_guard; then
    serving_decision=clear
  else
    rc=$?
    ((rc == 1)) && abort serving_unit_active
    abort serving_guard_unavailable
  fi
  sample_cpu || { rc=$?; ((rc == 1)) && abort cpu_temperature_limit; abort cpu_temperature_sensor_unavailable; }
  gpu_decision=not_required
  if [[ "$watch_gpu" == true ]]; then
    sample_gpu || { rc=$?; ((rc == 1)) && abort gpu_temperature_limit; abort gpu_telemetry_unavailable; }
    gpu_decision=clear
  fi
  nvme_decision=not_required
  if [[ "$stage" == storage || "$stage" == combined ]]; then
    sample_nvme || { rc=$?; ((rc == 1)) && abort nvme_critical_warning; abort nvme_telemetry_unavailable; }
    nvme_decision=clear
  fi
  logger -t pve-full-system-stress -p daemon.info -- \
    "pve_full_system_stress run=${run_id} stage=${stage}" \
    "event=sample memory_ecc=${memory_ecc} edac_ce_count=${current_ce} edac_ue_count=${current_ue}" \
    "mce_count=${mce_count} xid_count=${xid_count}"
  log daemon.info \
    "event=guard_decisions edac=${edac_decision} mce=clear xid=clear cpu_temp=clear" \
    "serving=${serving_decision} gpu_temp=${gpu_decision} nvme=${nvme_decision}"
}
