#!/usr/bin/env python3
"""Exercise the pmxcfs authorized_keys membership check in cluster_ssh_trust.

The role runs a small shell one-liner on real PVE nodes to decide whether
this node's /root/.ssh/id_rsa.pub is present as a line in the pmxcfs-shared
/etc/pve/priv/authorized_keys -- the gate that decides whether `pvecm
updatecerts --force` runs (Ansible `when: ... .rc != 0`), and again
afterwards as a fail-closed assertion. It cannot be covered by molecule: the
Docker test container has no pmxcfs/`pvecm` and the tasks are deliberately
skipped there (`ansible_virtualization_type != 'docker'`) -- so the real
assertion is this contract test.

This test does not carry a copy of the script. It EXTRACTS it out of
roles/cluster_ssh_trust/tasks/main.yml and substitutes its two hardcoded
/root/.ssh paths for temp-dir equivalents (root's real home is neither safe
nor writable from a workstation test run), so a change to the role that this
test no longer covers fails here instead of passing silently against a stale
duplicate.

Run: python3 tests/cluster_ssh_trust/test_pmxcfs_repair_gate.py
"""
import os
import subprocess
import sys
import tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TASKS = os.path.join(REPO, "roles", "cluster_ssh_trust", "tasks", "main.yml")

ID_RSA_PUB = "/root/.ssh/id_rsa.pub"
AUTH_KEYS = "/etc/pve/priv/authorized_keys"


def extract_check_script():
    """Pull the literal `cmd: >-` block of the pubkey-membership check task."""
    with open(TASKS) as fh:
        lines = fh.readlines()

    start = next(
        (i for i, ln in enumerate(lines)
         if "Check whether this node's public key is present" in ln), None)
    if start is None:
        sys.exit("FAIL: no task checks pubkey membership in the shared "
                 "authorized_keys — the role changed shape and this test "
                 "no longer covers it")

    cmd_at = next(
        (i for i in range(start, min(start + 6, len(lines)))
         if lines[i].strip() == "cmd: >-"), None)
    if cmd_at is None:
        sys.exit("FAIL: the check task no longer uses a `cmd: >-` block — "
                 "extraction is stale")

    indent = len(lines[cmd_at]) - len(lines[cmd_at].lstrip()) + 2
    body = []
    for ln in lines[cmd_at + 1:]:
        if ln.strip() and (len(ln) - len(ln.lstrip())) < indent:
            break
        body.append(ln[indent:] if len(ln) > indent else "\n")
    script = " ".join(l.strip() for l in body)  # >- folds to a single line

    if ID_RSA_PUB not in script or AUTH_KEYS not in script:
        sys.exit("FAIL: extracted script is missing an expected path — "
                 "extraction is wrong, or the role regressed")
    return script


def extract_repair_gate():
    """Pull the `when:` list of the repair (updatecerts) task, to prove it
    is gated on the check's rc and not unconditional."""
    with open(TASKS) as fh:
        text = fh.read()
    marker = "Repair the shared authorized_keys if this node's key is missing"
    if marker not in text:
        sys.exit("FAIL: no task repairs the shared authorized_keys — the "
                 "role changed shape and this test no longer covers it")
    snippet = text[text.index(marker):text.index(marker) + 600]
    if "cluster_ssh_trust_pubkey_check.rc" not in snippet or "!= 0" not in snippet:
        sys.exit("FAIL: the repair task is not gated on the check's rc — "
                 "it would run unconditionally on every converge")


SCRIPT = extract_check_script()
extract_repair_gate()


def run_case(tmp, pub_line, present_in_authorized_keys):
    """Substitute the two hardcoded paths for a temp dir. Write pub_line (or
    nothing) to id_rsa.pub, and either that same line or an unrelated one
    into authorized_keys, then run the check and return its exit code."""
    pub_path = os.path.join(tmp, "id_rsa.pub")
    auth_path = os.path.join(tmp, "authorized_keys")

    if pub_line is not None:
        with open(pub_path, "w") as fh:
            fh.write(pub_line + " root@pve-w1700\n")

    with open(auth_path, "w") as fh:
        fh.write("ssh-ed25519 UNRELATEDKEYFORNOISE root@some-other-node\n")
        if present_in_authorized_keys and pub_line is not None:
            fh.write(pub_line + " root@pve-w1700\n")

    body = SCRIPT.replace(ID_RSA_PUB, pub_path).replace(AUTH_KEYS, auth_path)
    if "/root/.ssh" in body or "/etc/pve" in body:
        sys.exit("FAIL: unsubstituted path remains: %r" % body)

    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False, dir=tmp) as fh:
        fh.write("#!/bin/bash\n" + body + "\n")
        script_path = fh.name
    os.chmod(script_path, 0o700)

    result = subprocess.run([script_path], capture_output=True, text=True, timeout=30)
    return result.returncode


PUB = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABfakefakefakefakefakefakefake"


def main():
    failures = []
    cases = [
        ("pubkey present in shared authorized_keys", PUB, True, 0),
        ("pubkey missing from shared authorized_keys (live incident shape)", PUB, False, 1),
        ("no local id_rsa.pub at all", None, False, 1),
    ]
    for name, pub_line, present, want_rc in cases:
        with tempfile.TemporaryDirectory() as tmp:
            rc = run_case(tmp, pub_line, present)
        ok = rc == want_rc
        print("%-58s -> rc=%s (want %s)  %s" %
              (name, rc, want_rc, "ok" if ok else "FAIL"))
        if not ok:
            failures.append(name)

    if failures:
        sys.exit("\nFAILURES: %s" % failures)
    print("\ncluster_ssh_trust pmxcfs authorized_keys membership check: all cases passed")


if __name__ == "__main__":
    main()
