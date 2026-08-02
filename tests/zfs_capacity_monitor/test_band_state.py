#!/usr/bin/env python3
"""Assert the ZFS capacity monitor cannot silence itself by failing to notify.

The monitor alerts on a band CHANGE, tracked in a per-pool state file. That
makes the state write the safety-critical line: if the band advances while the
notification did not actually go out, the next run sees no change and stays
quiet — the pool then fills through every remaining band in silence. The alert
that never arrives is indistinguishable from a healthy pool.

Molecule cannot cover this. The behaviour under test is what happens when the
notification endpoint is DOWN, and a container scenario has no way to present a
half-dead endpoint on a real pool. So the script is driven directly here, with
`zpool`/`zfs`/`curl` stubbed on PATH.

This test carries no copy of the script. It EXTRACTS the template from the role
and substitutes its Jinja expressions, so a change to the role that this test no
longer covers fails here instead of passing against a stale duplicate.

Run: python3 tests/zfs_capacity_monitor/test_band_state.py
"""
import os
import re
import stat
import subprocess
import sys
import tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEMPLATE = os.path.join(REPO, "roles", "proxmox_monitoring", "templates",
                        "zfs-capacity-monitor.sh.j2")

# Unroutable: these tests stub curl, so nothing is ever sent anywhere.
DEADMAN_DEFAULT = "http://deadman.invalid/zfs"


def extract_script():
    with open(TEMPLATE) as fh:
        body = fh.read()

    for marker in ("STATE_DIR=", "check_capacity", "notify()"):
        if marker not in body:
            sys.exit("FAIL: %s is missing %r — the role changed shape and this "
                     "test no longer covers it" % (TEMPLATE, marker))
    return body


def render(thresholds, deadman_url=DEADMAN_DEFAULT):
    """Substitute the template's Jinja expressions with literal test values."""
    body = extract_script()
    body = body.replace("{{ proxmox_monitoring_zfs_capacity_deadman_url }}",
                        deadman_url)
    joined = " ".join(str(t) for t in thresholds)
    body = re.sub(r"\{\{\s*proxmox_monitoring_zfs_capacity_thresholds[^}]*\}\}",
                  joined, body)
    body = re.sub(
        r"\{\{\s*proxmox_monitoring_zfs_dataset_capacity_thresholds[^}]*\}\}",
        joined, body)
    if "{{" in body:
        sys.exit("FAIL: unsubstituted Jinja remains after render — the template "
                 "grew a variable this test does not know about:\n%s" %
                 "\n".join(ln for ln in body.splitlines() if "{{" in ln))
    return body


def write_exec(path, body):
    with open(path, "w") as fh:
        fh.write(body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP)


def run(tmp, capacity, curl_exit, zpool_exit=0, curl_match_exit=None,
        curl_match=None, script="monitor.sh", zpool_warning="",
        zfs_warning=""):
    """Run the monitor once against a stubbed pool at `capacity`%.

    `curl_exit` is the status the stub `curl` returns, i.e. whether the
    notification landed. `curl_match`/`curl_match_exit` override that status for
    calls whose arguments contain `curl_match`, so one transport can be failed
    while another succeeds. Returns (returncode, stderr).
    """
    binq = os.path.join(tmp, "bin")
    os.makedirs(binq, exist_ok=True)
    # Built by concatenation, not %-formatting: the literal `%%` this printf
    # needs collides with Python's own format operator.
    if zpool_exit == 0:
        zpool_stub = "#!/bin/bash\n"
        if zpool_warning:
            zpool_stub += "echo %r >&2\n" % zpool_warning
        zpool_stub += ("printf 'tank\\t%s%%\\n' " + str(capacity) + "\n")
    else:
        zpool_stub = ("#!/bin/bash\necho 'cannot open pool' >&2\nexit "
                      + str(zpool_exit) + "\n")
    write_exec(os.path.join(binq, "zpool"), zpool_stub)
    # No quota'd filesystems: the dataset loop must be a no-op, not an error.
    zfs_stub = "#!/bin/bash\n"
    if zfs_warning:
        zfs_stub += "echo %r >&2\n" % zfs_warning
    zfs_stub += "exit 0\n"
    write_exec(os.path.join(binq, "zfs"), zfs_stub)

    curl_stub = "#!/bin/bash\necho \"$@\" >>%s/curl.log\n" % tmp
    if curl_match is not None:
        curl_stub += ('case "$*" in *%s*) exit %d ;; esac\n'
                      % (curl_match, curl_match_exit))
    curl_stub += "exit %d\n" % curl_exit
    write_exec(os.path.join(binq, "curl"), curl_stub)

    proc = subprocess.run(
        ["bash", os.path.join(tmp, script)],
        env={**os.environ, "PATH": binq + os.pathsep + os.environ["PATH"]},
        capture_output=True, text=True, timeout=30)
    return proc.returncode, proc.stderr


def band_state(tmp):
    """The recorded band for pool `tank`, or None if nothing was recorded."""
    path = os.path.join(tmp, "state", "pool_tank.band")
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return fh.read().strip()


def curl_calls(tmp, containing=None):
    path = os.path.join(tmp, "curl.log")
    if not os.path.exists(path):
        return 0
    with open(path) as fh:
        lines = [ln for ln in fh if ln.strip()]
    if containing is not None:
        lines = [ln for ln in lines if containing in ln]
    return len(lines)


def main():
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        body = render([50, 75, 85, 90])
        # Redirect state out of /var/lib so the test needs no root.
        body = body.replace('STATE_DIR="/var/lib/zfs-capacity-monitor"',
                            'STATE_DIR="%s/state"' % tmp)
        write_exec(os.path.join(tmp, "monitor.sh"), body)

        # 1. Notification fails at 90%: the band must NOT be recorded, or the
        #    pool goes silent from here to ENOSPC.
        rc, err = run(tmp, 90, curl_exit=7)
        if band_state(tmp) is not None:
            failures.append(
                "band %r was recorded even though the notification failed — a "
                "single dropped push now silences that band permanently"
                % band_state(tmp))
        if rc != 0:
            failures.append("a failed notification aborted the run (rc=%d); it "
                            "must keep checking the remaining pools\n"
                            "      stderr: %s" % (rc, err.strip() or "(empty)"))
        # Assert on the fact reported, not the phrasing: the operator has to be
        # able to tell an undelivered alert from a quiet pool.
        if "not recorded" not in err:
            failures.append("a failed notification produced no stderr warning, "
                            "so nothing distinguishes it from a quiet pool "
                            "(stderr: %r)" % err.strip())

        # 2. Next run, endpoint healthy: the missed alert must be retried.
        before = curl_calls(tmp)
        rc, _ = run(tmp, 90, curl_exit=0)
        if curl_calls(tmp) <= before:
            failures.append("the retry run sent no notification — the alert "
                            "missed while the endpoint was down is lost")
        if band_state(tmp) != "90":
            failures.append("band is %r after a successful push, expected '90'"
                            % band_state(tmp))

        # 3. Still at 90%, endpoint healthy: no repeat. The alert fires on a
        #    band CHANGE, and a monitor that re-pushes every interval gets muted
        #    by whoever receives it.
        # An unchanged band must send NOTHING: no repeat alert (which trains the
        # recipient to ignore it) and no OK heartbeat either, because a pool
        # still sitting above its threshold must not clear its own alert.
        before = curl_calls(tmp)
        run(tmp, 90, curl_exit=0)
        if curl_calls(tmp) != before:
            failures.append("an unchanged band above threshold sent %d more "
                            "call(s); a repeat alert is noise and an OK "
                            "heartbeat would clear a live breach"
                            % (curl_calls(tmp) - before))

    failures += check_transports()

    if failures:
        print("FAIL: zfs-capacity-monitor band-state contract")
        for f in failures:
            print("  - %s" % f)
        return 1
    print("PASS: band state survives a dropped alert, the deadman beats only "
          "when every pool is under threshold, recovery clears cleanly, and an "
          "unreadable sensor trips it instead of reporting silence")
    return 0


DEADMAN = DEADMAN_DEFAULT


def read_calls(tmp):
    """Every curl invocation logged so far, or [] if none were made.

    Absent is a legitimate outcome — a monitor that notifies nothing writes no
    log — and it is exactly the outcome under test, so it must read as an
    assertion failure rather than a traceback.
    """
    path = os.path.join(tmp, "curl.log")
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        return [ln.strip() for ln in fh if ln.strip()]


def ok_heartbeats(calls):
    """Calls to the OK endpoint: the deadman base, not its /fail sibling.

    Identified by the absence of the /fail suffix rather than by matching the
    end of the string. The ping carries a query string, so an end-anchored
    match silently finds nothing and every assertion built on it passes
    vacuously — which is the failure mode this file exists to prevent.
    """
    return [c for c in calls if DEADMAN in c and "/fail" not in c]


def check_transports():
    """The delivery contract for the single deadman path."""
    failures = []

    # 4. A breach reaches the /fail endpoint and is recorded as reported.
    with tempfile.TemporaryDirectory() as tmp:
        body = render([50, 75, 85, 90, 94], deadman_url=DEADMAN)
        body = body.replace('STATE_DIR="/var/lib/zfs-capacity-monitor"',
                            'STATE_DIR="%s/state"' % tmp)
        write_exec(os.path.join(tmp, "monitor.sh"), body)

        run(tmp, 94, curl_exit=0)
        if curl_calls(tmp, containing=DEADMAN + "/fail") == 0:
            failures.append("a breach sent nothing to the /fail endpoint")
        if band_state(tmp) != "94":
            failures.append("a delivered breach did not record band 94 (got "
                            "%r), so it will not be treated as reported"
                            % band_state(tmp))

    # 5. A breach must NOT also send the OK heartbeat in the same run — that
    #    would clear the very alert it just raised.
    with tempfile.TemporaryDirectory() as tmp:
        body = render([50, 75, 85, 90, 94], deadman_url=DEADMAN)
        body = body.replace('STATE_DIR="/var/lib/zfs-capacity-monitor"',
                            'STATE_DIR="%s/state"' % tmp)
        write_exec(os.path.join(tmp, "monitor.sh"), body)

        run(tmp, 94, curl_exit=0)
        calls = read_calls(tmp)
        ok_pings = ok_heartbeats(calls)
        if ok_pings:
            failures.append("a breaching run also sent an OK heartbeat (%d), "
                            "which clears the alert it just raised" % len(ok_pings))

    # A clean pass, by contrast, must beat — otherwise a dead monitor and a
    # healthy pool look identical.
    #
    # Run from FRESH state, not after the breach above. Dropping from a breach
    # also emits a recovery notification, and that lands on the same OK
    # endpoint as the heartbeat — so a run with prior state cannot tell the two
    # apart, and the assertion passes whether the heartbeat exists or not.
    # Verified by deleting the heartbeat from the template: with prior state
    # the test still passed; from fresh state it fails as it must.
    with tempfile.TemporaryDirectory() as tmp:
        body = render([50, 75, 85, 90, 94], deadman_url=DEADMAN)
        body = body.replace('STATE_DIR="/var/lib/zfs-capacity-monitor"',
                            'STATE_DIR="%s/state"' % tmp)
        write_exec(os.path.join(tmp, "monitor.sh"), body)

        run(tmp, 10, curl_exit=0)
        calls = read_calls(tmp)
        if not ok_heartbeats(calls):
            failures.append("a clean pass sent no heartbeat, so a stopped "
                            "monitor is indistinguishable from a healthy pool")

    # 5b. Every ping must ask the destination to create itself. The deadman is
    #     addressed by slug, and an unregistered slug answers 404 — so without
    #     this the monitor runs, exits 0, and reports to nothing, which is the
    #     precise condition it exists to detect. Observed live before this
    #     guard existed.
    with tempfile.TemporaryDirectory() as tmp:
        body = render([50, 75, 85, 90, 94], deadman_url=DEADMAN)
        body = body.replace('STATE_DIR="/var/lib/zfs-capacity-monitor"',
                            'STATE_DIR="%s/state"' % tmp)
        write_exec(os.path.join(tmp, "monitor.sh"), body)

        run(tmp, 94, curl_exit=0)   # breach -> /fail
        run(tmp, 10, curl_exit=0)   # recovery + heartbeat
        unprovisioned = [c for c in read_calls(tmp)
                         if DEADMAN in c and "create=1" not in c]
        if unprovisioned:
            failures.append(
                "%d ping(s) did not request creation of the destination; an "
                "unregistered endpoint answers 404 and the monitor then "
                "reports to nothing while exiting 0"
                % len(unprovisioned))

    # 6. Recovery must clear the alert, and must go to the OK endpoint rather
    #    than /fail — otherwise a pool that drained still reads as breached and
    #    the next real crossing has nothing to escalate from.
    with tempfile.TemporaryDirectory() as tmp:
        body = render([50, 75, 85, 90, 94], deadman_url=DEADMAN)
        body = body.replace('STATE_DIR="/var/lib/zfs-capacity-monitor"',
                            'STATE_DIR="%s/state"' % tmp)
        write_exec(os.path.join(tmp, "monitor.sh"), body)

        run(tmp, 94, curl_exit=0)          # breach
        os.remove(os.path.join(tmp, "curl.log"))
        run(tmp, 10, curl_exit=0)          # drained

        if band_state(tmp) != "0":
            failures.append("after recovery the band is %r, expected '0' — the "
                            "pool would stay latched as breached"
                            % band_state(tmp))
        if curl_calls(tmp, containing=DEADMAN + "/fail") != 0:
            failures.append("recovery hit the /fail endpoint; it must report OK")
        if curl_calls(tmp) == 0:
            failures.append("recovery sent nothing at all")

    # 7. An unreadable sensor must trip the deadman and fail loudly. "zpool
    #    list did not answer" is not "the pool is fine".
    with tempfile.TemporaryDirectory() as tmp:
        body = render([50, 75, 85, 90, 94], deadman_url=DEADMAN)
        body = body.replace('STATE_DIR="/var/lib/zfs-capacity-monitor"',
                            'STATE_DIR="%s/state"' % tmp)
        write_exec(os.path.join(tmp, "monitor.sh"), body)

        rc, err = run(tmp, 50, curl_exit=0, zpool_exit=1)
        if rc == 0:
            failures.append("a failing `zpool list` exited 0 — cron would "
                            "record a successful run against no data")
        if curl_calls(tmp, containing=DEADMAN + "/fail") == 0:
            failures.append("a failing `zpool list` did not trip the deadman, "
                            "so an unreadable sensor reports as silence")
        if "zpool list" not in err:
            failures.append("a failing `zpool list` produced no diagnostic on "
                            "stderr (got %r)" % err.strip())

    # 8. Benign sensor warnings belong on stderr, never in the tab-delimited
    #    data consumed by the capacity loops. Merging both streams makes the
    #    warning a fake pool/dataset row and produces integer-expression errors.
    with tempfile.TemporaryDirectory() as tmp:
        body = render([50, 75, 85, 90, 94], deadman_url=DEADMAN)
        body = body.replace('STATE_DIR="/var/lib/zfs-capacity-monitor"',
                            'STATE_DIR="%s/state"' % tmp)
        write_exec(os.path.join(tmp, "monitor.sh"), body)

        rc, err = run(tmp, 10, curl_exit=0,
                      zpool_warning="zpool benign warning",
                      zfs_warning="zfs benign warning")
        if rc != 0:
            failures.append("benign sensor warnings aborted the monitor "
                            "(rc=%d, stderr=%r)" % (rc, err.strip()))
        if "integer expression expected" in err:
            failures.append("sensor stderr was parsed as capacity data "
                            "(stderr=%r)" % err.strip())
        for warning in ("zpool benign warning", "zfs benign warning"):
            if warning not in err:
                failures.append("sensor warning %r was hidden instead of "
                                "remaining diagnostic" % warning)

    return failures


if __name__ == "__main__":
    sys.exit(main())
