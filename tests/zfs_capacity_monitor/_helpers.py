"""Shared fixtures for the zfs-capacity-monitor band-state contract tests.

This test carries no copy of the monitor script. It EXTRACTS the template
from the role and substitutes its Jinja expressions, so a change to the role
that these tests no longer cover fails here instead of passing against a
stale duplicate. `zpool`/`zfs`/`curl` are stubbed on PATH so the monitor can
be driven directly, including against a notification endpoint that is DOWN —
a case Molecule cannot present on a real pool.

Not a pytest module: these scripts are run directly (see each test file's
`Run:` line) so their PASS/FAIL summary and exit code are visible without a
pytest invocation. Import from here with the file's own directory on
sys.path (already true when run as `python3 test_*.py`).
"""
import os
import re
import stat
import subprocess
import sys

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


def ok_heartbeats(calls, deadman=DEADMAN_DEFAULT):
    """Calls to the OK endpoint: the deadman base, not its /fail sibling.

    Identified by the absence of the /fail suffix rather than by matching the
    end of the string. The ping carries a query string, so an end-anchored
    match silently finds nothing and every assertion built on it passes
    vacuously — which is the failure mode this file exists to prevent.
    """
    return [c for c in calls if deadman in c and "/fail" not in c]


def write_monitor(tmp, thresholds=(50, 75, 85, 90), deadman_url=DEADMAN_DEFAULT):
    """Render the monitor into `tmp/monitor.sh` with state redirected out of
    /var/lib so the test needs no root."""
    body = render(list(thresholds), deadman_url=deadman_url)
    body = body.replace('STATE_DIR="/var/lib/zfs-capacity-monitor"',
                        'STATE_DIR="%s/state"' % tmp)
    write_exec(os.path.join(tmp, "monitor.sh"), body)
