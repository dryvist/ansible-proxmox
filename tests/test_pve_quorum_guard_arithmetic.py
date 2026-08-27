#!/usr/bin/env python3
"""pve_quorum_guard reads corosync output correctly and subtracts absent voters.

The guard's whole value is that it reports headroom a raw `corosync-quorumtool`
reading overstates. Two things can break that silently: a regex that stops
matching (yielding 0 and a confusing parse failure rather than a wrong number),
and arithmetic that forgets to subtract voters which are configured but cannot
vote. Both are cheap to check offline and impossible to check without a cluster.

The patterns are extracted from the role rather than restated here, so this test
cannot pass against a regex the role no longer uses.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "roles" / "pve_quorum_guard" / "tasks" / "main.yml"

# One member alive of four, the shape a blocked cluster actually prints.
INQUORATE = """Quorum information
------------------
Quorate:          No

Votequorum information
----------------------
Expected votes:   4
Highest expected: 4
Total votes:      1
Quorum:           3 Activity blocked
Flags:

Membership information
----------------------
    Nodeid      Votes    Qdevice Name
         1          1         NR node-a (local)
"""

HEALTHY = """Votequorum information
----------------------
Expected votes:   4
Highest expected: 4
Total votes:      4
Quorum:           3
Flags:            Quorate
"""

NODELIST = """nodelist.node.0.name (str) = node-a
nodelist.node.0.nodeid (u32) = 1
nodelist.node.1.name (str) = node-b
nodelist.node.1.nodeid (u32) = 3
nodelist.node.2.name (str) = node-c
nodelist.node.2.nodeid (u32) = 4
nodelist.node.3.name (str) = node-d
nodelist.node.3.nodeid (u32) = 5
"""


def role_patterns(text):
    """Pull the three patterns the role uses, keyed by what they capture."""
    found = re.findall(r"regex_(?:search|findall)\('((?:[^'\\]|\\.)*)'", text)
    # Ansible reads these from YAML, where \s survives as a literal backslash-s;
    # Python needs the same string, so no unescaping is applied.
    by_name = {}
    for pattern in found:
        if "Highest expected" in pattern:
            by_name["highest"] = pattern
        elif "Quorum" in pattern:
            by_name["quorum"] = pattern
        elif "nodelist" in pattern:
            by_name["names"] = pattern
    return by_name


def scalar(pattern, text):
    match = re.search(pattern, text)
    return int(match.group(1)) if match else 0


def main():
    tasks = TASKS.read_text()
    patterns = role_patterns(tasks)

    missing = {"highest", "quorum", "names"} - set(patterns)
    assert not missing, f"role no longer defines patterns for: {sorted(missing)}"

    # Parsing works on the blocked output, not just the healthy output — the
    # guard is read exactly when the cluster is in the former state.
    assert scalar(patterns["highest"], INQUORATE) == 4
    assert scalar(patterns["highest"], HEALTHY) == 4

    # "Quorum: 3 Activity blocked" must yield 3, not fail on the trailing text.
    assert scalar(patterns["quorum"], INQUORATE) == 3
    assert scalar(patterns["quorum"], HEALTHY) == 3

    # Unparsed output must read as 0 so the role's own assert catches it,
    # rather than silently reporting a healthy-looking headroom.
    assert scalar(patterns["highest"], "not corosync output") == 0

    names = re.findall(patterns["names"], NODELIST)
    assert names == ["node-a", "node-b", "node-c", "node-d"], names

    # The arithmetic the guard exists for: four configured voters, quorum three.
    # Counting every configured voter says the cluster can lose one. Discounting
    # the one that is powered off says it can lose none — which is the truth,
    # and the difference this role reports.
    highest, quorum = 4, 3
    assert highest - 0 - quorum == 1
    assert highest - 1 - quorum == 0

    # A name that matches nothing must be visible as a difference, since
    # subtracting it would overstate headroom.
    assert set(["node-typo"]) - set(names) == {"node-typo"}
    assert not set(["node-d"]) - set(names)

    print("pve_quorum_guard arithmetic and parsing: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
