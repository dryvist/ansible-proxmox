#!/usr/bin/env python3
"""Exercise the pmxcfs SSH symlink repair gate in cluster_ssh_trust.

The task is a shell script the cluster_ssh_trust role runs on real PVE nodes
to detect and repair /root/.ssh/id_rsa and /root/.ssh/authorized_keys when
either has been replaced by a plain file instead of its pmxcfs symlink. It
cannot be covered by molecule: the Docker test container has no pmxcfs, no
`pvecm`, and the task is deliberately skipped there (`ansible_virtualization_
type != 'docker'`) — so the real assertion is this contract test.

This test does not carry a copy of the script. It EXTRACTS the script out of
roles/cluster_ssh_trust/tasks/main.yml and substitutes its two hardcoded
/root/.ssh paths for temp-dir equivalents (root's real home is neither safe
nor writable from a workstation test run), so a change to the role that this
test no longer covers fails here instead of passing silently against a stale
duplicate. `pvecm` is faked on PATH so the CHANGED branch is exercised
without a live cluster.

Run: python3 tests/cluster_ssh_trust/test_pmxcfs_repair_gate.py
"""
import os
import stat
import subprocess
import sys
import tempfile
import textwrap

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TASKS = os.path.join(REPO, "roles", "cluster_ssh_trust", "tasks", "main.yml")

ID_RSA = "/root/.ssh/id_rsa"
AUTH_KEYS = "/root/.ssh/authorized_keys"


def extract_repair_script():
    """Pull the literal `cmd: >-` block of the repair task out of the role."""
    with open(TASKS) as fh:
        lines = fh.readlines()

    start = next(
        (i for i, ln in enumerate(lines)
         if "Repair pmxcfs SSH symlinks if either has been replaced" in ln), None)
    if start is None:
        sys.exit("FAIL: no task named the pmxcfs symlink repair — the role "
                 "changed shape and this test no longer covers it")

    cmd_at = next(
        (i for i in range(start, min(start + 6, len(lines)))
         if lines[i].strip() == "cmd: >-"), None)
    if cmd_at is None:
        sys.exit("FAIL: the repair task no longer uses a `cmd: >-` block — "
                 "extraction is stale")

    indent = len(lines[cmd_at]) - len(lines[cmd_at].lstrip()) + 2
    body = []
    for ln in lines[cmd_at + 1:]:
        if ln.strip() and (len(ln) - len(ln.lstrip())) < indent:
            break
        body.append(ln[indent:] if len(ln) > indent else "\n")
    script = " ".join(l.strip() for l in body)  # >- folds to a single line

    if "pvecm updatecerts --force" not in script or ID_RSA not in script:
        sys.exit("FAIL: extracted script is missing its repair command or "
                 "identity path — extraction is wrong, or the role regressed")
    return script


SCRIPT = extract_repair_script()


def run_case(tmp, id_rsa_is_link, auth_keys_is_link):
    """Substitute the two hardcoded paths for a temp dir, seed the two files
    as either symlinks or plain files, fake `pvecm` on PATH, run the script,
    and return (stdout_last_line, pvecm_was_called)."""
    ssh_dir = os.path.join(tmp, "ssh")
    os.makedirs(ssh_dir, exist_ok=True)
    id_rsa = os.path.join(ssh_dir, "id_rsa")
    auth_keys = os.path.join(ssh_dir, "authorized_keys")
    target = os.path.join(tmp, "pmxcfs-target")
    with open(target, "w") as fh:
        fh.write("fake pmxcfs-backed content\n")

    def seed(path, is_link):
        if is_link:
            os.symlink(target, path)
        else:
            with open(path, "w") as fh:
                fh.write("plain file, not the pmxcfs symlink\n")

    seed(id_rsa, id_rsa_is_link)
    seed(auth_keys, auth_keys_is_link)

    marker = os.path.join(tmp, "pvecm-called")
    bin_dir = os.path.join(tmp, "bin")
    os.makedirs(bin_dir, exist_ok=True)
    pvecm = os.path.join(bin_dir, "pvecm")
    with open(pvecm, "w") as fh:
        fh.write("#!/bin/sh\ntouch %s\n" % marker)
    os.chmod(pvecm, os.stat(pvecm).st_mode | stat.S_IEXEC)

    body = SCRIPT.replace(ID_RSA, id_rsa).replace(AUTH_KEYS, auth_keys)
    if "/root/.ssh" in body:
        sys.exit("FAIL: unsubstituted /root/.ssh path remains: %r" % body)

    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False, dir=tmp) as fh:
        fh.write("#!/bin/bash\n" + body + "\n")
        script_path = fh.name
    os.chmod(script_path, os.stat(script_path).st_mode | stat.S_IEXEC)

    env = dict(os.environ)
    env["PATH"] = bin_dir + os.pathsep + env["PATH"]
    result = subprocess.run([script_path], capture_output=True, text=True,
                            timeout=30, env=env)
    out = result.stdout.strip().splitlines()
    last = out[-1] if out else ""
    return last, os.path.exists(marker), result.returncode


def main():
    failures = []
    cases = [
        ("both symlinks intact", True, True, "UNCHANGED", False),
        ("id_rsa replaced by a plain file", False, True, "CHANGED", True),
        ("authorized_keys replaced by a plain file", True, False, "CHANGED", True),
        ("both replaced by plain files", False, False, "CHANGED", True),
    ]
    for name, id_link, auth_link, want_status, want_called in cases:
        with tempfile.TemporaryDirectory() as tmp:
            status, called, rc = run_case(tmp, id_link, auth_link)
        ok = status == want_status and called == want_called and rc == 0
        print("%-42s -> status=%-10s pvecm_called=%-5s rc=%s  %s" %
              (name, status, called, rc, "ok" if ok else "FAIL"))
        if not ok:
            failures.append(name)

    if failures:
        sys.exit("\nFAILURES: %s" % failures)
    print("\ncluster_ssh_trust pmxcfs repair gate: all cases passed")


if __name__ == "__main__":
    main()
