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


def extract_script():
    with open(TEMPLATE) as fh:
        body = fh.read()

    for marker in ("STATE_DIR=", "check_capacity", "notify()"):
        if marker not in body:
            sys.exit("FAIL: %s is missing %r — the role changed shape and this "
                     "test no longer covers it" % (TEMPLATE, marker))
    return body


def render(thresholds, ntfy_url="http://notify.invalid/topic"):
    """Substitute the template's Jinja expressions with literal test values."""
    body = extract_script()
    body = body.replace("{{ proxmox_monitoring_ntfy_url }}", ntfy_url)
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


def run(tmp, capacity, curl_exit):
    """Run the monitor once against a stubbed pool at `capacity`%.

    `curl_exit` is the status the stub `curl` returns, i.e. whether the
    notification landed. Returns (returncode, stderr).
    """
    binq = os.path.join(tmp, "bin")
    os.makedirs(binq, exist_ok=True)
    # Built by concatenation, not %-formatting: the literal `%%` this printf
    # needs collides with Python's own format operator.
    write_exec(os.path.join(binq, "zpool"),
               "#!/bin/bash\nprintf 'tank\\t%s%%\\n' " + str(capacity) + "\n")
    # No quota'd filesystems: the dataset loop must be a no-op, not an error.
    write_exec(os.path.join(binq, "zfs"), "#!/bin/bash\nexit 0\n")
    write_exec(os.path.join(binq, "curl"),
               "#!/bin/bash\necho \"$@\" >>%s/curl.log\nexit %d\n"
               % (tmp, curl_exit))

    script = os.path.join(tmp, "monitor.sh")
    proc = subprocess.run(
        ["bash", script],
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


def curl_calls(tmp):
    path = os.path.join(tmp, "curl.log")
    if not os.path.exists(path):
        return 0
    with open(path) as fh:
        return len([ln for ln in fh if ln.strip()])


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
        if "notification failed" not in err:
            failures.append("a failed notification produced no stderr warning, "
                            "so nothing distinguishes it from a quiet pool")

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
        before = curl_calls(tmp)
        run(tmp, 90, curl_exit=0)
        if curl_calls(tmp) != before:
            failures.append("an unchanged band notified again — repeat alerts "
                            "on every interval train the recipient to ignore it")

    if failures:
        print("FAIL: zfs-capacity-monitor band-state contract")
        for f in failures:
            print("  - %s" % f)
        return 1
    print("PASS: a dropped notification does not advance the band, is retried, "
          "and an unchanged band stays quiet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
