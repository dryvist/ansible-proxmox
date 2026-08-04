#!/usr/bin/env python3
"""Assert the backup identity layers report WHAT was protected, not that a job ran.

A backup job selecting a bare guest id keeps succeeding after that id is
recycled onto a different guest. Every signal the estate collects — exit status,
archive mtime, archive size, prune activity, the task log — stays green, because
each one only asserts the job RAN. The health telemetry line carries the two
fields that assert what it protected instead.

Molecule cannot cover this. The behaviour under test is a directory of archives
whose names disagree with each other or with the inventory, and a container
scenario has no way to present a plausible archive history on real storage. So
the script is driven directly here against fixture dump directories, with
`logger` stubbed on PATH to capture the emitted line.

Three of the four cases below are failure modes; the fourth is the false-green
guard. That one matters most: with no identity map rendered, the mismatch field
must report UNKNOWN, never 0 — a map that failed to render must not be
indistinguishable from a map that found nothing wrong.

This test carries no copy of the script. It RENDERS the role's template against
the role's own defaults, so a change to either that this test no longer covers
fails here instead of passing against a stale duplicate.

Run: python3 tests/pve_backup_identity/test_identity_assert.py
"""
import os
import stat
import subprocess
import sys
import tempfile

import jinja2
import yaml

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ROLE = os.path.join(REPO, "roles", "pve_health_telemetry")
TEMPLATE = os.path.join(ROLE, "templates", "pve-health.sh.j2")
DEFAULTS = os.path.join(ROLE, "defaults", "main.yml")

# Fabricated ids. Nothing here corresponds to a real guest — the logic under
# test only cares that two archive names share an id.
RECYCLED = 4242
STABLE = 4243

failures = []


def host_clocksource():
    try:
        with open("/sys/devices/system/clocksource/clocksource0/"
                  "current_clocksource") as fh:
            return fh.read().strip()
    except OSError:
        return "unknown"


def render(dump_dir, map_path):
    """Render the role template against the role's own defaults."""
    with open(TEMPLATE) as fh:
        body = fh.read()
    for marker in ("backup_type_change", "backup_identity_mismatch"):
        if marker not in body:
            sys.exit("FAIL: %s no longer emits %r — the role changed shape and "
                     "this test no longer covers it" % (TEMPLATE, marker))

    with open(DEFAULTS) as fh:
        variables = yaml.safe_load(fh)
    variables.update({
        "ansible_managed": "test fixture",
        # The real settle window exists to outlast benign D-state waits; this
        # test asserts nothing about stall detection and should not pay for it.
        "pve_health_telemetry_dstate_settle_seconds": 0,
        "pve_health_telemetry_backup_dirs": [dump_dir],
        "pve_health_telemetry_identity_map_path": map_path,
        # Expect whatever this machine actually reports, so the unrelated
        # clocksource check cannot stamp the fixture warning and mask the
        # severity the backup fields are supposed to produce. A CI runner and a
        # workstation both report something other than the production default.
        "pve_health_telemetry_expected_clocksource": host_clocksource(),
    })

    # `bool` is an Ansible filter, not a core Jinja2 one, so plain Jinja2 would
    # fail on the template's own guard rather than on anything under test.
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    env.filters["bool"] = lambda v: str(v).lower() in ("true", "yes", "on", "1")
    return env.from_string(body).render(**variables)


def run(archives, mapping):
    """Run the script over a fixture dump dir; return the emitted key=value dict.

    `mapping` of None means no map file at all, which is the case the UNKNOWN
    sentinel exists for.
    """
    with tempfile.TemporaryDirectory() as work:
        dump_dir = os.path.join(work, "dump")
        os.makedirs(dump_dir)
        for name in archives:
            open(os.path.join(dump_dir, name), "w").close()

        map_path = os.path.join(work, "guest-identity.map")
        if mapping is not None:
            with open(map_path, "w") as fh:
                fh.write("# test fixture\n")
                for vmid, kind in mapping.items():
                    fh.write("%d %s\n" % (vmid, kind))

        script = os.path.join(work, "pve-health.sh")
        with open(script, "w") as fh:
            fh.write(render(dump_dir, map_path))
        os.chmod(script, os.stat(script).st_mode | stat.S_IEXEC)

        # Stub logger so the emitted line is captured instead of hitting the
        # journal. Everything else the script probes degrades to a sentinel on
        # its own when absent, which is the documented behaviour.
        binstub = os.path.join(work, "bin")
        os.makedirs(binstub)
        emitted = os.path.join(work, "emitted")
        logger = os.path.join(binstub, "logger")
        with open(logger, "w") as fh:
            fh.write('#!/bin/sh\nshift 4\nprintf "%s\\n" "$*" > ' + emitted + "\n")
        os.chmod(logger, os.stat(logger).st_mode | stat.S_IEXEC)

        env = dict(os.environ, PATH=binstub + os.pathsep + os.environ["PATH"])
        result = subprocess.run([script], env=env, capture_output=True, text=True)
        if not os.path.exists(emitted):
            sys.exit("FAIL: the script emitted no line at all (rc=%d)\n%s"
                     % (result.returncode, result.stderr))

        with open(emitted) as fh:
            line = fh.read().strip()
    return dict(field.split("=", 1) for field in line.split() if "=" in field)


def check(case, fields, expected):
    for key, want in expected.items():
        got = fields.get(key)
        if got != want:
            failures.append("%s: %s expected %r, got %r (line: %s)"
                            % (case, key, want, got, fields))


def qemu(vmid, day):
    return "vzdump-qemu-%d-2026_01_%02d-01_00_00.vma.zst" % (vmid, day)


def lxc(vmid, day):
    return "vzdump-lxc-%d-2026_01_%02d-01_00_00.tar.zst" % (vmid, day)


# 1. The recycle that started this: one id, both guest types, a month apart. A
#    guest cannot change type, so this needs no map and is unambiguous.
check("type change", run([qemu(RECYCLED, 4), lxc(RECYCLED, 19)],
                         {RECYCLED: "lxc"}),
      {"backup_type_change": "1", "severity": "critical"})

# 2. Recycled onto the SAME type. The names agree with each other, so only the
#    map catches it — this is the whole reason layer two exists.
check("same-type recycle", run([lxc(RECYCLED, 19)], {RECYCLED: "qemu"}),
      {"backup_type_change": "0", "backup_identity_mismatch": "1",
       "severity": "warning"})

# 3. FALSE-GREEN GUARD. No map rendered: the mismatch field must be UNKNOWN.
#    Reporting 0 here would make an unrendered map look like a clean check, and
#    the type-change layer must keep working regardless.
check("no map", run([qemu(RECYCLED, 4), lxc(RECYCLED, 19)], None),
      {"backup_identity_mismatch": "-1", "backup_type_change": "1",
       "severity": "critical"})

# 4. Archives that agree with the inventory raise nothing, so a healthy estate
#    is not permanently warning — an alarm that is always on is not an alarm.
check("clean", run([lxc(STABLE, 19), lxc(STABLE, 20)], {STABLE: "lxc"}),
      {"backup_type_change": "0", "backup_identity_mismatch": "0",
       "backup_archive_ids": "1", "severity": "info"})

if failures:
    print("FAIL: backup identity assertion\n  " + "\n  ".join(failures))
    sys.exit(1)
print("PASS: backup identity assertion (4 cases)")
