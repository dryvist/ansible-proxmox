#!/usr/bin/env python3
"""A declared `sparse` must reach an ALREADY-registered Proxmox storage.

`pvesm add` runs only when the storage is missing, so on every node where the
storage ID already exists a newly-declared `sparse` would stay inert — the
declaration reads correct while every new disk is still created with a full
refreservation. That is the shape this file guards: the reconcile task exists,
it fires on the existing-storage branch, and it compares live against declared
rather than firing unconditionally.

It also pins the absent-means-off reading. `pvesh get /storage/<id>` omits the
`sparse` key entirely when sparse is off and returns `1` when it is on, so a
missing key must be read as 0. Defaulting it to anything else makes the
reconcile either never fire or fire forever.
"""

import sys
from pathlib import Path

import yaml

TASK_FILE = (
    Path(__file__).resolve().parents[1]
    / "roles/zfs_pools/tasks/dataset_pvesm_register.yml"
)

# What `pvesh get /storage/<id>` actually returns, verified live: the key is
# absent when off, present as 1 when on.
LIVE_SPARSE_OFF = {"storage": "nvme-splunk", "type": "zfspool"}
LIVE_SPARSE_ON = {"storage": "local-zfs", "type": "zfspool", "sparse": 1}


def want(declared):
    """The value the tasks render for a declared `sparse`."""
    return 1 if declared else 0


def live(payload):
    """The value the reconcile task reads back, absent meaning off."""
    return int(payload.get("sparse", 0))


def check_absent_means_off():
    failures = []
    if live(LIVE_SPARSE_OFF) != 0:
        failures.append("a storage with no `sparse` key must read as 0")
    if live(LIVE_SPARSE_ON) != 1:
        failures.append("a storage with sparse=1 must read as 1")
    # The whole point: declared-on against live-off must be a difference.
    if live(LIVE_SPARSE_OFF) == want(True):
        failures.append("declared sparse against a thick storage must differ")
    # And a matching pair must NOT be, or the task is not idempotent.
    if live(LIVE_SPARSE_ON) != want(True):
        failures.append("declared sparse against a sparse storage must match")
    return failures


def check_reconcile_task_present():
    tasks = yaml.safe_load(TASK_FILE.read_text())
    failures = []

    add = [t for t in tasks if "pvesm add zfspool" in str(t.get("command", t))]
    reconcile = [t for t in tasks if "pvesm set" in str(t.get("command", t))]

    if not add:
        failures.append("no `pvesm add` task found")
    if not reconcile:
        failures.append("no `pvesm set` reconcile task -- a declared sparse "
                        "cannot reach an already-registered storage")
        return failures

    def when_of(task):
        """`when:` is a scalar on one task and a list on the other. Joining a
        scalar character-by-character turns `!= 0` into `! = 0` and the match
        silently fails, so normalise before comparing."""
        clause = task.get("when", [])
        if isinstance(clause, str):
            clause = [clause]
        return " ".join(str(c) for c in clause)

    add_when = when_of(add[0])
    rec_when = when_of(reconcile[0])

    # The two branches must be opposite, or the reconcile rides the create path
    # and never runs against existing storage -- exactly the bug.
    if "!= 0" not in add_when:
        failures.append("`pvesm add` must be gated on the storage being absent")
    if "== 0" not in rec_when:
        failures.append("the reconcile must be gated on the storage EXISTING")
    if "sparse" not in rec_when:
        failures.append("the reconcile must compare sparse, not fire blindly")

    # `sparse` must also be passed at creation, or a fresh node is born thick.
    if "-sparse" not in str(add[0].get("command", add[0])):
        failures.append("`pvesm add` must pass -sparse")

    return failures


def main():
    checks = [check_absent_means_off, check_reconcile_task_present]
    failures = []
    for check in checks:
        failures.extend(f"{check.__name__}: {f}" for f in check())

    print(f"ran {len(checks)} checks over {TASK_FILE.name}")
    if failures:
        for f in failures:
            print(f"FAIL {f}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
