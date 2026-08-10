"""Shared fixtures/helpers for the managed-volume contract tests.

These tests grep the role's actual task files for exact task names and Jinja
snippets — the role's own tasks/*.yml are the thing under test, so a change
here fails the SAME way a change to the role would, with no duplicated copy
to drift out of sync.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROLE = Path(__file__).resolve().parents[2] / "roles" / "pve_guest_evacuation_lxc_managed_volumes"


def flatten_included_tasks(path: Path) -> str:
    """Inline every top-level `include_tasks:` target referenced by *path*.

    transfer.yml is a thin dispatcher over ordered phase files (split out for
    the token budget). The contract tests below grep for task names and Jinja
    snippets that now live in those phase files, not in transfer.yml's own
    text — so this flattens exactly one level (matching transfer.yml's own
    include_tasks list) back into one string, the same content transfer.yml
    held before the split. It does NOT recurse into a phase file's own
    includes (e.g. write_evidence.yml) — those were already separate files
    before the split and the tests that care about them read them directly.

    Each dispatcher task (`- name: ...` + its `include_tasks:` line) is
    replaced by the target file's body outright, not appended after it — the
    tests slice a raw substring out of the flattened text and write it back
    out as its own YAML file, so a leftover dispatcher task pointing at a
    filename that does not exist in that throwaway directory breaks it. Each
    phase file's own leading `---` document marker is stripped the same way,
    so the flattened text reads as the single document transfer.yml used to be.
    """
    text = path.read_text()
    out = []
    pos = 0
    for match in re.finditer(
        r"- name:.*\n\s*ansible\.builtin\.include_tasks:\s*(\S+)\s*\n", text
    ):
        out.append(text[pos : match.start()])
        target = path.parent / match.group(1)
        included = re.sub(r"^---\n", "", target.read_text())
        out.append(included)
        pos = match.end()
    out.append(text[pos:])
    return "".join(out)


def run_zfs_dataset_identity_parser(
    tmp_path: Path,
    source_lines: list[str],
    target_lines: list[str],
    expected_mappings: list[dict[str, object]] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Execute the role's extracted parser tasks with fixture ZFS output."""
    ansible_playbook = shutil.which("ansible-playbook")
    if ansible_playbook is None:
        pytest.skip("ansible-playbook is required to execute the parser regression")

    transfer = flatten_included_tasks(ROLE / "tasks" / "transfer.yml")
    parser_start = transfer.index("- name: Define the ZFS filesystem record separator")
    parser_end = transfer.index("- name: Assert no ZFS snapshots exist on either evacuation node")
    parser_path = tmp_path / "zfs-parser.yml"
    parser_path.write_text(transfer[parser_start:parser_end])

    zfs_filesystems = {
        "results": [
            {"item": "pve2", "stdout_lines": source_lines},
            {"item": "pve540", "stdout_lines": target_lines},
        ]
    }
    resolved_mappings = [
        {
            "key": "mp0",
            "source_path": "/bulk/subvol-519010-disk-1",
            "target_path": "/rpool/data/subvol-519010-disk-1",
        }
    ]
    playbook_tasks = "    - ansible.builtin.include_tasks: zfs-parser.yml\n"
    if expected_mappings is not None:
        playbook_tasks += (
            "    - ansible.builtin.assert:\n"
            "        that:\n"
            "          - pve_guest_evacuation_lxc_managed_volumes_dataset_mappings == "
            "expected_dataset_mappings\n"
        )
    playbook_path = tmp_path / "playbook.yml"
    playbook_path.write_text(
        "---\n"
        "- hosts: localhost\n"
        "  connection: local\n"
        "  gather_facts: false\n"
        "  vars:\n"
        "    pve_guest_evacuation_lxc_managed_volumes_zfs_filesystems: "
        f"{json.dumps(zfs_filesystems)}\n"
        "    pve_guest_evacuation_lxc_managed_volumes_resolved_mappings: "
        f"{json.dumps(resolved_mappings)}\n"
        "    expected_dataset_mappings: "
        f"{json.dumps(expected_mappings or [])}\n"
        "  tasks:\n"
        f"{playbook_tasks}"
    )
    return subprocess.run(
        [ansible_playbook, "-i", "localhost,", str(playbook_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )


def run_canonical_endpoint_contract(
    tmp_path: Path,
    canonical_fqdn: str,
    inventory_endpoint: str,
    canonical_ipv4s: list[str],
    inventory_ipv4s: list[str],
) -> subprocess.CompletedProcess[str]:
    """Execute the role's exact canonical-endpoint assertion with fixture DNS."""
    ansible_playbook = shutil.which("ansible-playbook")
    if ansible_playbook is None:
        pytest.skip("ansible-playbook is required to execute the endpoint regression")

    contract = (ROLE / "tasks" / "preflight_contract.yml").read_text()
    task_start = contract.index("- name: Derive pve2 IPv4 resolutions")
    endpoint_tasks = tmp_path / "endpoint-contract.yml"
    endpoint_tasks.write_text(contract[task_start:])

    def getent_lines(addresses: list[str]) -> list[str]:
        return [f"{address} STREAM" for address in addresses]

    playbook = tmp_path / "playbook.yml"
    playbook.write_text(
        "---\n"
        "- hosts: localhost\n"
        "  connection: local\n"
        "  gather_facts: false\n"
        "  vars:\n"
        f"    pve_guest_evacuation_lxc_managed_volumes_target_rsync_host: {json.dumps(canonical_fqdn)}\n"
        f"    pve_guest_evacuation_lxc_managed_volumes_target_rsync_canonical_fqdn: {json.dumps(canonical_fqdn)}\n"
        "    pve_guest_evacuation_lxc_managed_volumes_target_node: pve540\n"
        "    pve_guest_evacuation_lxc_managed_volumes_canonical_fqdn_resolution:\n"
        "      rc: 0\n"
        f"      stdout_lines: {json.dumps(getent_lines(canonical_ipv4s))}\n"
        "    pve_guest_evacuation_lxc_managed_volumes_inventory_endpoint_resolution:\n"
        "      rc: 0\n"
        f"      stdout_lines: {json.dumps(getent_lines(inventory_ipv4s))}\n"
        "  tasks:\n"
        "    - ansible.builtin.add_host:\n"
        "        name: pve540\n"
        f"        ansible_host: {json.dumps(inventory_endpoint)}\n"
        "    - ansible.builtin.include_tasks: endpoint-contract.yml\n"
    )
    return subprocess.run(
        [ansible_playbook, "-i", "localhost,", str(playbook)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
