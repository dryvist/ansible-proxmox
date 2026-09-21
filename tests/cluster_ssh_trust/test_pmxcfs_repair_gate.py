#!/usr/bin/env python3
"""Exercise the pmxcfs authorized_keys membership expression in cluster_ssh_trust.

The role decides whether `pvecm updatecerts --force` needs to run (and
whether the post-repair state is acceptable) with a single Jinja expression
evaluated in a `set_fact`/`assert`, over the base64 `content` two
`ansible.builtin.slurp` tasks register -- no shell, per this repo's "no
scripts embedded in YAML" rule. It cannot be covered by molecule: the
Docker test container has no pmxcfs and the tasks are deliberately skipped
there (`ansible_virtualization_type != 'docker'`) -- so the real assertion
is this contract test.

This test does not carry a copy of the expression. It EXTRACTS the
`cluster_ssh_trust_pubkey_present` value out of
roles/cluster_ssh_trust/tasks/main.yml and renders it with `ansible-playbook`
against fixture base64 content standing in for the two slurped files, so a
change to the role that this test no longer covers fails here instead of
passing silently against a stale duplicate.

Run: python3 tests/cluster_ssh_trust/test_pmxcfs_repair_gate.py
"""
import base64
import os
import subprocess
import sys
import tempfile

import yaml

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TASKS = os.path.join(REPO, "roles", "cluster_ssh_trust", "tasks", "main.yml")
HANDLERS = os.path.join(REPO, "roles", "cluster_ssh_trust", "handlers", "main.yml")
HANDLER_NAME = "Restart pveproxy and pvedaemon"


def check_repair_notifies_handler():
    """The updatecerts repair task must notify the cert-restart handler, and
    that handler must actually exist -- a notify to a typo'd or missing
    handler name is silently a no-op, not an error."""
    with open(TASKS) as fh:
        tasks = yaml.safe_load(fh)
    repair = next(
        (t for t in tasks if "pvecm updatecerts" in str(t.get("ansible.builtin.command", {}))), None)
    if repair is None:
        sys.exit("FAIL: no task runs `pvecm updatecerts --force` — the role "
                 "changed shape and this test no longer covers it")
    notify = repair.get("notify")
    notify_list = notify if isinstance(notify, list) else [notify]
    if HANDLER_NAME not in notify_list:
        sys.exit("FAIL: the updatecerts repair task does not notify %r "
                 "(notify=%r) — pveproxy/pvedaemon won't restart after a "
                 "certificate regeneration" % (HANDLER_NAME, notify))

    with open(HANDLERS) as fh:
        handlers = yaml.safe_load(fh) or []
    if not any(h.get("name") == HANDLER_NAME for h in handlers):
        sys.exit("FAIL: no handler named %r is defined in handlers/main.yml "
                 "— the notify above is a silent no-op" % HANDLER_NAME)


def extract_expression():
    """Pull the `cluster_ssh_trust_pubkey_present: >-` block's Jinja body."""
    with open(TASKS) as fh:
        lines = fh.readlines()

    start = next(
        (i for i, ln in enumerate(lines)
         if ln.strip() == "cluster_ssh_trust_pubkey_present: >-"), None)
    if start is None:
        sys.exit("FAIL: no `cluster_ssh_trust_pubkey_present: >-` block — "
                 "the role changed shape and this test no longer covers it")

    indent = len(lines[start]) - len(lines[start].lstrip()) + 2
    body = []
    for ln in lines[start + 1:]:
        if ln.strip() and (len(ln) - len(ln.lstrip())) < indent:
            break
        body.append(ln[indent:] if len(ln) > indent else "\n")
    expr = " ".join(l.strip() for l in body)

    if "b64decode" not in expr or "cluster_ssh_trust_id_rsa_pub" not in expr:
        sys.exit("FAIL: extracted expression is missing an expected term — "
                 "extraction is wrong, or the role regressed")
    return expr


EXPR = extract_expression()

PUB_LINE = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABfakefakefakefakefakefakefake"


def run_case(tmp, pub_line, auth_keys_lines):
    """Render the extracted expression with ansible-playbook against fixture
    slurp-shaped content, and return the resulting boolean."""
    pub_b64 = base64.b64encode((pub_line + " root@node\n").encode()).decode()
    auth_b64 = base64.b64encode(("\n".join(auth_keys_lines) + "\n").encode()).decode()

    result_path = os.path.join(tmp, "result.txt")
    playbook = os.path.join(tmp, "test.yml")
    with open(playbook, "w") as fh:
        fh.write(
            "- hosts: localhost\n"
            "  gather_facts: false\n"
            "  vars:\n"
            "    cluster_ssh_trust_id_rsa_pub:\n"
            "      content: %r\n"
            "    cluster_ssh_trust_shared_authorized_keys:\n"
            "      content: %r\n"
            "  tasks:\n"
            "    - name: evaluate the extracted expression\n"
            "      ansible.builtin.set_fact:\n"
            "        cluster_ssh_trust_pubkey_present: \"%s\"\n"
            "    - name: write the result\n"
            "      ansible.builtin.copy:\n"
            "        dest: %r\n"
            "        content: \"{{ cluster_ssh_trust_pubkey_present }}\"\n"
            % (pub_b64, auth_b64, EXPR, result_path)
        )

    result = subprocess.run(
        ["ansible-playbook", "-i", "localhost,", "-c", "local", playbook],
        capture_output=True, text=True, timeout=60, cwd=tmp,
    )
    if result.returncode != 0:
        sys.exit("FAIL: ansible-playbook errored rendering the expression:\n"
                 + result.stdout + result.stderr)
    with open(result_path) as fh:
        return fh.read().strip() == "True"


def main():
    if subprocess.run(["which", "ansible-playbook"], capture_output=True).returncode != 0:
        sys.exit("FAIL: ansible-playbook not on PATH — run inside the nix devshell")

    check_repair_notifies_handler()
    print("updatecerts repair task notifies %r, and that handler exists  ok" % HANDLER_NAME)

    failures = []
    cases = [
        ("pubkey present in shared authorized_keys",
         [PUB_LINE, "ssh-ed25519 UNRELATED root@other"], True),
        ("pubkey missing from shared authorized_keys (live incident shape)",
         ["ssh-ed25519 UNRELATED root@other"], False),
        ("shared authorized_keys empty",
         [], False),
    ]
    for name, auth_lines, want in cases:
        with tempfile.TemporaryDirectory() as tmp:
            got = run_case(tmp, PUB_LINE, auth_lines)
        ok = got == want
        print("%-58s -> present=%s (want %s)  %s" %
              (name, got, want, "ok" if ok else "FAIL"))
        if not ok:
            failures.append(name)

    if failures:
        sys.exit("\nFAILURES: %s" % failures)
    print("\ncluster_ssh_trust pmxcfs authorized_keys membership expression: all cases passed")


if __name__ == "__main__":
    main()
