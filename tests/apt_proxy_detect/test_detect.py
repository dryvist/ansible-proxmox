#!/usr/bin/env python3
"""Exercise the apt caching-proxy auto-detect hook against real TCP listeners.

The hook is a shell script the pve_repositories role writes to
/usr/local/bin/apt-proxy-detect. It cannot be covered by molecule: the point of
it is what happens when a proxy is UNREACHABLE, and a container scenario has no
way to present a half-dead cache pair.

This test does not carry a copy of that script. It EXTRACTS the script out of
roles/pve_repositories/tasks/main.yml and substitutes the two Jinja expressions,
so a change to the role that this test no longer covers fails here instead of
passing silently against a stale duplicate.

Run: python3 tests/apt_proxy_detect/test_detect.py
"""
import os
import re
import socket
import stat
import subprocess
import sys
import tempfile
import textwrap
import threading

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TASKS = os.path.join(REPO, "roles", "pve_repositories", "tasks", "main.yml")


def extract_hook_script():
    """Pull the literal `content: |` block of the auto-detect task out of the role."""
    with open(TASKS) as fh:
        lines = fh.readlines()

    start = next(
        (i for i, ln in enumerate(lines)
         if "dest: /usr/local/bin/apt-proxy-detect" in ln), None)
    if start is None:
        sys.exit("FAIL: no task writes /usr/local/bin/apt-proxy-detect — the "
                 "role changed shape and this test no longer covers it")

    content_at = next(
        (i for i in range(start, min(start + 6, len(lines)))
         if lines[i].strip() == "content: |"), None)
    if content_at is None:
        sys.exit("FAIL: the auto-detect task no longer uses a `content: |` "
                 "block — extraction is stale")

    indent = len(lines[content_at]) - len(lines[content_at].lstrip()) + 2
    body = []
    for ln in lines[content_at + 1:]:
        if ln.strip() and (len(ln) - len(ln.lstrip())) < indent:
            break
        body.append(ln[indent:] if len(ln) > indent else "\n")
    script = textwrap.dedent("".join(body))

    if "/dev/tcp/" not in script or "DIRECT" not in script:
        sys.exit("FAIL: extracted script is missing its probe or its DIRECT "
                 "fallback — extraction is wrong, or the role regressed")
    return script


HOOK = extract_hook_script()


def render(urls, default_port):
    """Substitute the role's two Jinja expressions and run the result."""
    body = HOOK
    body = re.sub(r"\{\{\s*pve_repositories_apt_proxies[^}]*\}\}",
                  " ".join("'%s'" % u for u in urls), body)
    body = re.sub(r"\{\{\s*pve_repositories_apt_proxy_default_port\s*\}\}",
                  str(default_port), body)
    if "{{" in body:
        sys.exit("FAIL: unsubstituted Jinja remains in the hook: %r" % body)

    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as fh:
        fh.write(body)
        path = fh.name
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    try:
        return subprocess.run([path], capture_output=True,
                              text=True, timeout=30).stdout.strip()
    finally:
        os.remove(path)


class Listener:
    """A socket that accepts and immediately closes, i.e. a reachable port."""

    def __init__(self):
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.sock.listen(8)
        self.stopped = False
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        while not self.stopped:
            try:
                self.sock.accept()[0].close()
            except OSError:
                return

    def close(self):
        self.stopped = True
        self.sock.close()


def reachable(port):
    try:
        socket.create_connection(("127.0.0.1", port), 2).close()
        return True
    except OSError:
        return False


def main():
    live = Listener()
    LIVE = "http://127.0.0.1:%d" % live.port
    DEAD, DEAD2 = "http://127.0.0.1:1", "http://127.0.0.1:2"

    # Controls on the harness itself. Without these a broken fixture reads as a
    # passing test: "DIRECT" is the right answer for a dead pool AND for a
    # listener that never came up.
    if not reachable(live.port):
        sys.exit("FAIL: harness listener is down — no result below would mean anything")
    if reachable(1):
        sys.exit("FAIL: port 1 is open — the dead fixtures are not dead")

    cases = [
        ("first dead, second live", [DEAD, LIVE], 3142, LIVE),
        ("single live", [LIVE], 3142, LIVE),
        ("whole pool dead falls back to DIRECT", [DEAD, DEAD2], 3142, "DIRECT"),
        ("preference order honoured", [LIVE, DEAD], 3142, LIVE),
        ("no explicit port, default reachable", ["http://127.0.0.1"], live.port,
         "http://127.0.0.1"),
        ("no explicit port, default dead", ["http://127.0.0.1"], 1, "DIRECT"),
    ]

    failures = []
    for name, urls, port, want in cases:
        got = render(urls, port)
        ok = got == want
        print("%-38s -> %-30s %s" % (name, got, "ok" if ok else "FAIL (want %s)" % want))
        if not ok:
            failures.append(name)

    # Negative control: kill the listener and a case that just passed must flip.
    live.close()
    got = render([LIVE], 3142)
    ok = got == "DIRECT"
    print("%-38s -> %-30s %s" % ("listener killed (negative control)", got,
                                 "ok" if ok else "FAIL"))
    if not ok:
        failures.append("negative control did not flip to DIRECT")

    if failures:
        sys.exit("\nFAILURES: %s" % failures)
    print("\napt-proxy-detect: all cases passed")


if __name__ == "__main__":
    main()
