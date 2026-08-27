# pve_quorum_guard

Read-only check on corosync quorum headroom. Runs two query commands, reports
the arithmetic on every converge, and fails when headroom falls below the
declared minimum. It writes no corosync configuration and touches no guest.

## What headroom means

Headroom is how many voting members the cluster can lose at once and stay
quorate:

```text
headroom = highest_expected - declared_powered_off - quorum
```

`Highest expected` counts every configured voter. A voter that is powered off
still raises the quorum bar and can never cast its vote, so it costs a full
point of headroom while the raw numbers still look healthy. Declaring those
members in `pve_quorum_guard_powered_off_voters` is what makes the shortfall
visible.

At headroom 0 the cluster is quorate but one failure from `Activity blocked`,
and while blocked no `onboot` guest starts on the surviving members — including
the ones a recovery depends on.

## Installation

In-tree role — no external collection or Galaxy install. It is applied from
`playbooks/site.yml` to the Proxmox nodes alongside the other node-level checks,
and skips itself under Docker so molecule scenarios run without a cluster.

## Usage

```bash
# Report headroom on every node, no other roles:
ansible-playbook playbooks/site.yml --tags pve_quorum_guard

# Declare the members that are deliberately powered off (normally in
# inventory/group_vars, shown here as an extra var):
ansible-playbook playbooks/site.yml --tags pve_quorum_guard \
  -e '{"pve_quorum_guard_powered_off_voters": ["node-name"]}'
```

The report line is emitted on every run. A run fails only when headroom is
below `pve_quorum_guard_min_headroom`.

## Variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `pve_quorum_guard_enabled` | `true` | Run the check. |
| `pve_quorum_guard_min_headroom` | `1` | Voters the cluster must tolerate losing. |
| `pve_quorum_guard_powered_off_voters` | `[]` | Configured voters deliberately not powered, by corosync node name. |

A name in `pve_quorum_guard_powered_off_voters` that is not in the live nodelist
fails the guard rather than being ignored: a name matching nothing subtracts
nothing, which would restore the blind spot the list exists to remove.

## Remediation when it fails

Both options change the vote topology. Both are operator actions in a
maintenance window, because a corosync configuration change propagates through
the cluster filesystem and so requires the cluster to be quorate when it is
made. Neither is automated here.

**Zero-vote a permanently powered-off member.** Set `quorum_votes: 0` for that
node in the corosync nodelist and bump `config_version`. The node stays a
cluster member — manageable, able to host storage and guests when powered — but
stops raising the quorum bar. Reversible by the same edit. Prefer this to
removing the node: removal is effectively one-directional, since a removed node
must be reinstalled before it can rejoin.

**Add an external arbiter (QDevice).** A `corosync-qnetd` host outside the
cluster casting a vote is the only way a *single* surviving member stays
quorate. Two constraints decide whether it helps:

- **Algorithm.** Under `lms` the arbiter contributes `expected_votes - 1`
  votes, so one surviving member that can reach it remains quorate. Under
  `ffsplit` it contributes exactly one, which does not rescue a single member.
  `pvecm qdevice setup` selects the algorithm from the *node* count, not the
  vote count, so a cluster carrying a zero-vote member can be given `ffsplit`
  when `lms` was intended. Set the algorithm explicitly and verify it.
- **Arbiter availability.** Once configured, the arbiter's votes are part of
  the expected total, so an arbiter that is *down* raises the bar rather than
  lowering it and leaves the cluster less tolerant than it was with no arbiter
  at all. The host must therefore be more available than the cluster it
  arbitrates, and outside its failure domain — including its power domain.

`two_node`, `last_man_standing` and `auto_tie_breaker` do not substitute for
either. `two_node` applies only at exactly two members; `last_man_standing`
cannot reduce expected votes below two, so it never rescues a single member;
and all three are mutually exclusive with a QDevice, so adopting them forecloses
the arbiter option.

## What not to do

`pvecm expected <n>` lowers the bar without adding a vote. It clears the symptom
the guard reports while leaving the partition free to diverge from members it
cannot see, and it does not survive a restart. It is a break-glass step for a
human mid-recovery, never a remediation for this check and never automation.
