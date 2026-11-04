"""Offline smoke coverage for the OCI app upgrade playbook's dry-run path."""

import json
import os
import re
import shlex
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROXMOX_HOST = "oci-test"
STUBBED_COMMANDS = (
    "pct",
    "ha-manager",
    "pvesr",
    "curl",
    "pvesh",
    "pveam",
    "pvecm",
    "vzdump",
)
MUTATING_COMMANDS = {
    ("pct", "create"),
    ("pct", "destroy"),
    ("pct", "move-volume"),
    ("pct", "set"),
    ("pct", "shutdown"),
    ("pct", "start"),
    ("ha-manager", "add"),
    ("ha-manager", "remove"),
    ("pvesr", "create-local-job"),
    ("pvesr", "delete"),
    ("vzdump", "123"),
}


@pytest.fixture
def oci_command_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    log_path = tmp_path / "commands.log"
    log_path.touch()
    stub = """#!/bin/sh
printf '%s' "${0##*/}" >> "$OCI_STUB_LOG"
for argument do
    printf ' %s' "$argument" >> "$OCI_STUB_LOG"
done
printf '\\n' >> "$OCI_STUB_LOG"
if [ -n "${OCI_STUB_FAIL-}" ] && [ "$OCI_STUB_FAIL" = "${1-}" ]; then
    exit 1
fi
case "${0##*/}" in
    pvesh)
        if [ "${1-}" != "get" ]; then
            exit 2
        fi
        case "${2-}" in
            /cluster/resources)
                printf '%s\\n' '[{"type":"lxc","vmid":123,"node":"pve-w1700"}]'
                ;;
            /nodes/pve-w1700/lxc/123/config)
                printf '%s\\n' '{"rootfs":"local-lvm:vm-123-disk-0,size=8G"}'
                ;;
            /nodes/pve-w1700/lxc/123/status/current)
                printf '%s\\n' '{"status":"running"}'
                ;;
            /nodes/pve-w1700/lxc/990000/config)
                printf '%s\\n' '{}'
                exit 1
                ;;
            /nodes/pve-w1700/lxc/123/snapshot)
                printf '%s\\n' '[{"name":"current"}]'
                ;;
            /storage)
                printf '%s\\n' '[{"storage":"guests","type":"pbs"}]'
                ;;
            /cluster/ha/resources|/cluster/replication)
                printf '%s\\n' '[]'
                ;;
            *)
                exit 2
                ;;
        esac
        ;;
    pveam)
        if [ "${1-} ${2-}" != "list local" ]; then
            exit 2
        fi
        printf '%s\\n' 'local:vztmpl/debian-12-standard_12.8-1_amd64.tar.zst' 'local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst'
        ;;
    pvecm)
        if [ "${1-}" != "status" ]; then
            exit 2
        fi
        printf '%s\\n' 'Quorate: Yes' 'Total votes: 1' 'Highest expected: 1'
        ;;
esac
exit 0
"""
    for command in STUBBED_COMMANDS:
        executable = stub_dir / command
        executable.write_text(stub)
        executable.chmod(0o755)

    monkeypatch.setenv("PATH", os.pathsep.join((str(stub_dir), os.environ["PATH"])))
    monkeypatch.setenv("OCI_STUB_LOG", str(log_path))
    monkeypatch.delenv("OCI_STUB_FAIL", raising=False)
    return log_path


def test_default_dry_run_does_not_call_mutating_commands(
    tmp_path: Path, oci_command_log: Path
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    local_tmp = tmp_path / "ansible-local"
    local_tmp.mkdir()
    inventory_path = tmp_path / "inventory.yml"
    inventory_path.write_text(
        """all:
  hosts:
    localhost:
      ansible_connection: local
  children:
    proxmox:
      hosts:
        oci-test:
          ansible_connection: local
          ansible_become: false
          proxmox_node_name: pve-w1700
"""
    )
    environment = {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        "ANSIBLE_CONFIG": str(ROOT / "ansible.cfg"),
        "ANSIBLE_COLLECTIONS_PATH": os.pathsep.join(
            (
                str(ROOT / ".ansible" / "collections"),
                str(Path.home() / ".ansible" / "collections"),
                "/usr/share/ansible/collections",
            )
        ),
        "ANSIBLE_LOCAL_TEMP": str(local_tmp),
        "OCI_STUB_LOG": str(oci_command_log),
        "TOFU_INVENTORY_PATH": str(ROOT / "tests" / "inventory_load" / "tofu_inventory.json"),
    }
    extra_vars = {
        "oci_app_upgrades": [
            {
                "vmid": 123,
                "image": "ghcr.io/example/app:1.2.3",
                "template": "local:vztmpl/debian-12-standard_12.8-1_amd64.tar.zst",
                "current_template": "local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst",
                "health_url": "https://example.invalid/health",
            }
        ]
    }

    result = subprocess.run(
        [
            "ansible-playbook",
            "playbooks/oci_app_upgrade.yml",
            "-i",
            str(inventory_path),
            "-e",
            json.dumps(extra_vars),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, (
        f"ansible-playbook exited with {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "no hosts matched" not in result.stdout.lower(), result.stdout
    recap = next(
        (line for line in result.stdout.splitlines() if line.startswith(PROXMOX_HOST)),
        None,
    )
    assert recap is not None, f"{PROXMOX_HOST} missing from play recap\n{result.stdout}"
    ok_count = re.search(r"\bok=(\d+)\b", recap)
    assert ok_count is not None and int(ok_count.group(1)) > 0, recap

    logged_argv = [shlex.split(line) for line in oci_command_log.read_text().splitlines()]
    read_only_pvesh_calls = [
        argv for argv in logged_argv if len(argv) >= 2 and argv[:2] == ["pvesh", "get"]
    ]
    assert read_only_pvesh_calls, f"no read-only pvesh get call reached stubs: {logged_argv}"
    mutations = [argv for argv in logged_argv if tuple(argv[:2]) in MUTATING_COMMANDS]
    assert not mutations, f"mutating commands reached stubs: {mutations}"
