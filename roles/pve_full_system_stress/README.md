# Full-system stress

This opt-in role runs memory, CPU, storage, GPU, and combined stress stages in
that order by default. Set `pve_full_system_stress_stages` to a non-empty,
canonical-order subset to repeat selected stages; for example, `[gpu, combined]`.
Only selected stages are validated and scheduled. Memory must be the longest
selected stage when memory is selected. Storage runs must be at least five
minutes. The `smoke` profile runs for 16 minutes of stage time. The `full`
profile runs for 120 minutes of stage time.

The start task checks the host, takes an atomic campaign lock, and schedules
one transient systemd service per stage. Each service has `RuntimeMaxSec`
equal to its declared stage duration. A transient timer starts each stage at
its scheduled offset. Each service runs its own hardware and serving guards
until its workload exits, records UTC stage boundaries and telemetry in the
journal, and stops later timers if a guard fires. Ten seconds separate the
scheduled end of one stage from the next stage.

## Semaphore template 18

Use template **18**, branch `develop`, playbook `playbooks/site.yml`, tag
`pve_full_system_stress`, and a limit containing the declared GPU host plus
`localhost`.

Start the full run with these extra variables:

```yaml
pve_full_system_stress_mode: start
pve_full_system_stress_profile: full
pve_full_system_stress_stages: [memory, cpu, storage, gpu, combined]
pve_full_system_stress_fio_size: 1G
```

Copy the run id from the task output. Poll status in a new short task with:

```yaml
pve_full_system_stress_mode: status
pve_full_system_stress_run_id: <run-id-from-start>
pve_full_system_stress_stages: [memory, cpu, storage, gpu, combined]
```

Pass the same stage list to status polls. Omitted stages are recorded as
`event=stage_skipped reason=not_selected` in the journal and listed under
`skipped_stages` in status output.

Repeat status polls until the journal reports `event=campaign_end` with
`outcome=success` or `outcome=abort`. Status reports the stage unit states,
journal lines, peak CPU/GPU/NVMe temperatures, peak GPU power and clocks,
throttle values, and current EDAC plus campaign MCE/Xid counts. Do not start a
second run while the campaign lock or any stress unit is active.

The `smoke` profile is the default. It uses the same start and status sequence
with `pve_full_system_stress_profile: smoke`.

The role detects memory ECC from SMBIOS type 16 and reports `memory_ecc` in
the campaign journal and status output. Unknown SMBIOS values stop the run.
