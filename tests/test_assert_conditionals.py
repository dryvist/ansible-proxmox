#!/usr/bin/env python3
"""Every `that:` element must be a string.

A conditional containing ": " unquoted YAML-parses as a MAPPING, so the assert
errors at run time instead of evaluating. ansible-lint's production profile
does not catch it, and two instances sat green in this repo until they were
found by a probe. A gate that always errors looks like an unhealthy
environment, not a broken task, so this class is expensive to debug.
"""

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
# Derived, never hand-listed: a fixed list of roles omits the next one silently.
TREES = ("roles", "playbooks", "molecule")

BAD_FIXTURE = """
- name: Known-bad and known-good conditionals
  ansible.builtin.assert:
    that:
      - item.stdout == 'status: stopped'
      - item.rc == 0
"""


def scan(text):
    """Return (non-string `that:` elements, count examined) for one document."""
    bad, seen = [], 0

    def walk(node):
        nonlocal seen
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "that":
                    for element in value if isinstance(value, list) else [value]:
                        seen += 1
                        if not isinstance(element, str):
                            bad.append(element)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(yaml.safe_load(text))
    return bad, seen


def test_detector_flags_the_known_bad_form():
    """Self-check: a test that cannot demonstrate a catch proves nothing."""
    bad, seen = scan(BAD_FIXTURE)
    assert seen == 2, f"fixture should offer 2 conditionals, saw {seen}"
    assert bad == [{"item.stdout == 'status": "stopped'"}], bad


def test_every_assert_conditional_is_a_string():
    findings, seen, files = [], 0, 0
    for tree in TREES:
        for path in sorted((ROOT / tree).rglob("*.yml")):
            bad, count = scan(path.read_text())
            seen += count
            files += 1
            findings += [f"{path.relative_to(ROOT)}: {element}" for element in bad]

    # Zero examined means the walk found nothing to check — that is a failure,
    # not a pass.
    assert seen > 0, f"examined no conditionals across {files} files"
    assert not findings, "conditionals that parse as mappings:\n" + "\n".join(findings)
    print(f"examined {seen} `that:` elements across {files} files")


if __name__ == "__main__":
    test_detector_flags_the_known_bad_form()
    test_every_assert_conditional_is_a_string()
    sys.exit(0)
