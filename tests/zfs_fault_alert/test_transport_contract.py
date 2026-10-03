#!/usr/bin/env python3
"""Assert the zfs-fault-alert ntfy transport contract holds end to end.

Covers: a real firing publishes to the configured ntfy hub (never Zammad's
tickets API) with Priority: high, a configured publish token is sent as a
Bearer header and omitted when unset, --self-check hits the hub's own
health endpoint WITHOUT publishing an alert (it would otherwise page
Slack/Zammad on every converge), and a failed publish exits non-zero so the
missed-events poller leaves its cursor unadvanced and retries.

This test extracts the live template instead of carrying a copy of it, so a
change to the role that this test no longer covers fails here instead of
passing against a stale duplicate. Molecule cannot cover any of this: it
never runs the script, only renders/deploys it.

Run: python3 tests/zfs_fault_alert/test_transport_contract.py
"""
import os
import re
import stat
import subprocess
import sys
import tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEMPLATE = os.path.join(REPO, "roles", "zfs_fault_alert", "templates",
                        "zfs-fault-alert.sh.j2")

NTFY_URL = "http://ntfy.invalid/hardware"


def render():
    with open(TEMPLATE) as fh:
        body = fh.read()
    for marker in ("TOKEN_FILE=", "--self-check", "/v1/health"):
        if marker not in body:
            sys.exit("FAIL: %s is missing %r -- the role changed shape and "
                      "this test no longer covers it" % (TEMPLATE, marker))
    body = re.sub(r"\{\{\s*ansible_managed\s*\|\s*comment\s*\}\}", "# managed", body)
    body = body.replace('URL="{{ zfs_fault_alert_ntfy_url }}"', 'URL="%s"' % NTFY_URL)
    if "{{" in body:
        sys.exit("FAIL: unsubstituted Jinja remains after render:\n%s" %
                  "\n".join(ln for ln in body.splitlines() if "{{" in ln))
    return body


def write_exec(path, body):
    with open(path, "w") as fh:
        fh.write(body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)


def run(tmp, args, curl_exit=0, token=None):
    binq = os.path.join(tmp, "bin")
    os.makedirs(binq, exist_ok=True)

    # -w '%{http_code}' only appears on the --self-check branch; emit a
    # fake 200 there so a curl_exit=0 self-check reads as reachable.
    curl_stub = ('#!/bin/bash\necho "$@" >>%s/curl.log\n'
                 'if [[ "$*" == *-w* ]]; then echo -n 200; fi\n'
                 'exit %d\n') % (tmp, curl_exit)
    write_exec(os.path.join(binq, "curl"), curl_stub)
    write_exec(os.path.join(binq, "logger"), "#!/bin/bash\ntrue\n")

    if token is not None:
        with open(os.path.join(tmp, "ntfy-token"), "w") as fh:
            fh.write(token)

    body = render().replace("TOKEN_FILE=/etc/zfs-fault-alert/ntfy-token",
                            "TOKEN_FILE=%s/ntfy-token" % tmp)
    script = os.path.join(tmp, "zfs-fault-alert.sh")
    write_exec(script, body)

    return subprocess.run(
        ["bash", script] + args,
        env={**os.environ, "PATH": binq + os.pathsep + os.environ["PATH"]},
        capture_output=True, text=True, timeout=30)


def read_calls(tmp):
    path = os.path.join(tmp, "curl.log")
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        return [ln.strip() for ln in fh if ln.strip()]


def check():
    failures = []

    with tempfile.TemporaryDirectory() as tmp:
        proc = run(tmp, ["checksum error", "pool=rpool"])
        calls = read_calls(tmp)
        if proc.returncode != 0:
            failures.append("a successful publish exited non-zero: %r" % proc.stderr)
        if not any(NTFY_URL in c for c in calls):
            failures.append("no curl call targeted the configured ntfy hub URL")
        if any("api/v1/tickets" in c or "Token token=" in c for c in calls):
            failures.append("a call still targeted the Zammad tickets API")
        if not any("Priority: high" in c for c in calls):
            failures.append("no call set Priority: high")
        if not any("Tags: zfs" in c for c in calls):
            failures.append("no call set the zfs tag")

    with tempfile.TemporaryDirectory() as tmp:
        run(tmp, ["checksum error", "pool=rpool"], token="s3cr3t")
        calls = read_calls(tmp)
        if not any("Authorization: Bearer s3cr3t" in c for c in calls):
            failures.append("a configured publish token was not sent as a Bearer header")

    with tempfile.TemporaryDirectory() as tmp:
        run(tmp, ["checksum error", "pool=rpool"])
        calls = read_calls(tmp)
        if any("Authorization" in c for c in calls):
            failures.append("an Authorization header was sent with no token configured")

    with tempfile.TemporaryDirectory() as tmp:
        proc = run(tmp, ["--self-check"])
        calls = read_calls(tmp)
        if not any("/v1/health" in c for c in calls):
            failures.append("--self-check did not hit the hub health endpoint")
        if any(NTFY_URL in c for c in calls):
            failures.append("--self-check published to the alert topic")
        if proc.returncode != 0:
            failures.append("a successful self-check exited non-zero")

    with tempfile.TemporaryDirectory() as tmp:
        proc = run(tmp, ["checksum error", "pool=rpool"], curl_exit=7)
        if proc.returncode == 0:
            failures.append("a failed curl publish exited 0, which would let "
                            "the missed-events poller advance its cursor past "
                            "an unreported event")

    return failures


def main():
    failures = check()
    if failures:
        print("FAIL: zfs-fault-alert transport contract")
        for f in failures:
            print("  - %s" % f)
        return 1
    print("PASS: zfs-fault-alert publishes to the configured ntfy hub, "
          "self-check never publishes, and a failed publish exits non-zero")
    return 0


if __name__ == "__main__":
    sys.exit(main())
