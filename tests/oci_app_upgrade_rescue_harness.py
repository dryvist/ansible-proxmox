"""Shared offline runner and stubs for OCI app upgrade tests."""

import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Iterator

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROXMOX_HOST = "oci-test"
STUBBED_COMMANDS = (
    "pct",
    "ha-manager",
    "pvesr",
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
state_value() {
    case "$1" in
        ct_exists) awk 'BEGIN { v = 1 } $1 == "pct" && $2 == "destroy" && $3 == "123" { v = 0 } $1 == "pct" && $2 == "create" && $3 == "123" { v = 1 } END { print v }' "$OCI_STUB_STATE_LOG" ;;
        holder_exists) awk 'BEGIN { v = 0 } $1 == "pct" && $2 == "create" && $3 == "990000" { v = 1 } $1 == "pct" && $2 == "destroy" && $3 == "990000" { v = 0 } END { print v }' "$OCI_STUB_STATE_LOG" ;;
        volume_owner) awk 'BEGIN { v = "123" } $1 == "pct" && $2 == "move-volume" { v = $6 } END { print v }' "$OCI_STUB_STATE_LOG" ;;
        ct_status) awk 'BEGIN { v = "running" } $1 == "pct" && $2 == "shutdown" && $3 == "123" { v = "stopped" } $1 == "pct" && $2 == "start" && $3 == "123" { v = "running" } $1 == "pct" && $2 == "create" && $3 == "123" { v = "stopped" } END { print v }' "$OCI_STUB_STATE_LOG" ;;
        ha_managed) awk 'BEGIN { v = 1 } $1 == "ha-manager" && $2 == "remove" && $3 == "ct:123" { v = 0 } $1 == "ha-manager" && $2 == "add" && $3 == "ct:123" { v = 1 } END { print v }' "$OCI_STUB_STATE_LOG" ;;
        replication_exists) awk 'BEGIN { v = 1 } $1 == "pvesr" && $2 == "delete" && $3 == "123-0" { v = 0 } $1 == "pvesr" && $2 == "create-local-job" && $3 == "123-0" { v = 1 } END { print v }' "$OCI_STUB_STATE_LOG" ;;
    esac
}
command_line="${0##*/} $*"
should_fail=0
if [ -n "${OCI_STUB_FAIL-}" ]; then
    case "$command_line" in
        *"$OCI_STUB_FAIL"*) should_fail=1 ;;
    esac
fi
# OCI_STUB_FAIL_OWNER limits the failure to calls made while that vmid owns the volume.
if [ "$should_fail" -eq 1 ] && [ -n "${OCI_STUB_FAIL_OWNER-}" ] \
    && [ "$(state_value volume_owner)" != "$OCI_STUB_FAIL_OWNER" ]; then
    should_fail=0
fi
if [ "$should_fail" -eq 1 ]; then
    case "$OCI_STUB_FAIL" in
        */health*) exit 1 ;;
    esac
    if ! grep -Fq -- "$OCI_STUB_FAIL" "$OCI_STUB_FAIL_LOG"; then
        printf '%s\\n' "$OCI_STUB_FAIL" >> "$OCI_STUB_FAIL_LOG"
        exit 1
    fi
fi
# OCI_STUB_FAIL_ALSO is a second, independent fail-once pattern, for a failure inside the rescue.
if [ -n "${OCI_STUB_FAIL_ALSO-}" ]; then
    case "$command_line" in
        *"$OCI_STUB_FAIL_ALSO"*)
            if ! grep -Fq -- "$OCI_STUB_FAIL_ALSO" "$OCI_STUB_FAIL_LOG"; then
                printf '%s\\n' "$OCI_STUB_FAIL_ALSO" >> "$OCI_STUB_FAIL_LOG"
                exit 1
            fi
            ;;
    esac
fi
if [ "${0##*/}" = pct ] && [ "${1-}" = destroy ]; then
    volume_owner=$(awk '
        BEGIN { owner = "123" }
        $1 == "pct" && $2 == "move-volume" { owner = $6 }
        END { print owner }
    ' "$OCI_STUB_STATE_LOG")
    if [ "$volume_owner" = "${2-}" ]; then
        printf 'pct destroy %s while it owns mp0\\n' "${2-}" >> "$OCI_STUB_UNSAFE_LOG"
        exit 97
    fi
fi
printf '%s\\n' "$command_line" >> "$OCI_STUB_STATE_LOG"
case "${0##*/}" in
    pct)
        ;;
    ha-manager|pvesr|vzdump)
        ;;
    pvesh)
        if [ "${1-}" != "get" ]; then
            exit 2
        fi
        case "${2-}" in
            /cluster/resources)
                printf '%s\\n' '[{"type":"lxc","vmid":123,"node":"pve-w1700"}]'
                ;;
            /nodes/pve-w1700/lxc/123/config)
                if [ "$(state_value ct_exists)" != 1 ]; then
                    printf '%s\\n' "Configuration file 'nodes/pve-w1700/lxc/123.conf' does not exist" >&2
                    exit 2
                elif [ "$(state_value volume_owner)" = 123 ]; then
                    printf '%s\\n' '{"rootfs":"local-lvm:vm-123-disk-0,acl=1,size=8G,mountoptions=noatime","mp0":"local-zfs:vm-123-disk-1,mp=/data,backup=1","hostname":"oci-app","ostype":"debian","unprivileged":1,"digest":"test"}'
                else
                    printf '%s\\n' '{"rootfs":"local-lvm:vm-123-disk-0,acl=1,size=8G,mountoptions=noatime","hostname":"oci-app","ostype":"debian","unprivileged":1,"digest":"test"}'
                fi
                ;;
            /nodes/pve-w1700/lxc/123/status/current)
                if [ "$(state_value ct_exists)" != 1 ]; then
                    printf '%s\\n' "Configuration file 'nodes/pve-w1700/lxc/123.conf' does not exist" >&2
                    exit 2
                fi
                printf '{"status":"%s"}\\n' "$(state_value ct_status)"
                ;;
            /nodes/pve-w1700/lxc/990000/config)
                if [ "$(state_value holder_exists)" != 1 ]; then
                    printf '%s\\n' "Configuration file 'nodes/pve-w1700/lxc/990000.conf' does not exist" >&2
                    exit 2
                elif [ "$(state_value volume_owner)" = 990000 ]; then
                    printf '%s\\n' '{"rootfs":"local-lvm:vm-990000-disk-0,size=8G","mp0":"local-zfs:vm-123-disk-1,mp=/data,backup=1"}'
                else
                    printf '%s\\n' '{"rootfs":"local-lvm:vm-990000-disk-0,size=8G"}'
                fi
                ;;
            /nodes/pve-w1700/lxc/123/snapshot)
                printf '%s\\n' '[{"name":"current"}]'
                ;;
            /storage)
                printf '%s\\n' '[{"storage":"guests","type":"pbs"}]'
                ;;
            /cluster/ha/resources)
                if [ "$(state_value ha_managed)" = 1 ]; then
                    printf '%s\\n' '[{"sid":"ct:123"}]'
                else
                    printf '%s\\n' '[]'
                fi
                ;;
            /cluster/replication)
                if [ "$(state_value replication_exists)" = 1 ]; then
                    printf '%s\\n' '[{"id":"123-0","source":"pve-w1700","target":"pve-w1701","enabled":1}]'
                else
                    printf '%s\\n' '[]'
                fi
                ;;
            /cluster/ha/rules|/nodes/pve-w1700/replication)
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

    role_tasks = tmp_path / "stub-roles" / "pve_ha" / "tasks"
    role_tasks.mkdir(parents=True)
    (role_tasks / "tier0_resources.yml").write_text(
        """- name: Restore the test HA resource from desired state
  ansible.builtin.command: ha-manager add ct:123 --state started
  changed_when: true
"""
    )
    (role_tasks / "replication_jobs.yml").write_text(
        """- name: Resolve the test replication job from desired state
  ansible.builtin.set_fact:
    pve_ha_test_replication_job: 123-0
"""
    )
    (role_tasks / "replication_apply.yml").write_text(
        """- name: Restore the test replication job from desired state
  ansible.builtin.command: pvesr create-local-job 123-0 pve-w1701
  changed_when: true
"""
    )

    monkeypatch.setenv("PATH", os.pathsep.join((str(stub_dir), os.environ["PATH"])))
    monkeypatch.setenv("OCI_STUB_LOG", str(log_path))
    monkeypatch.setenv("OCI_STUB_STATE_LOG", str(tmp_path / "state.log"))
    monkeypatch.setenv("OCI_STUB_FAIL_LOG", str(tmp_path / "failure.log"))
    monkeypatch.setenv("OCI_STUB_UNSAFE_LOG", str(tmp_path / "unsafe.log"))
    for log_file in ("state.log", "failure.log", "unsafe.log"):
        (tmp_path / log_file).touch()
    monkeypatch.setenv(
        "ANSIBLE_ROLES_PATH",
        os.pathsep.join((str(tmp_path / "stub-roles"), str(ROOT / "roles"))),
    )
    monkeypatch.delenv("OCI_STUB_FAIL", raising=False)
    return log_path


@pytest.fixture
def oci_http() -> Iterator[ThreadingHTTPServer]:
    """Loopback server for the role's uri health check and ntfy post."""

    class Handler(BaseHTTPRequestHandler):
        def _reply(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            self.server.requests.append((self.command, self.path, self.rfile.read(length)))
            failing = self.path == "/health" and self.server.fail_health
            self.send_response(503 if failing else 200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        do_GET = do_POST = _reply

        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.requests = []
    server.fail_health = False
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()
    server.server_close()


@pytest.fixture
def run_oci_app_upgrade(
    tmp_path: Path, oci_command_log: Path, oci_http: ThreadingHTTPServer
) -> Callable[..., subprocess.CompletedProcess[str]]:
    def run(
        *, dry_run: bool = True, fail: str = "", fail_owner: str = "", fail_also: str = ""
    ) -> subprocess.CompletedProcess[str]:
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
            "ANSIBLE_ASYNC_DIR": str(tmp_path / "ansible-async"),
            "OCI_STUB_LOG": str(oci_command_log),
            "OCI_STUB_STATE_LOG": str(tmp_path / "state.log"),
            "OCI_STUB_FAIL_LOG": str(tmp_path / "failure.log"),
            "OCI_STUB_UNSAFE_LOG": str(tmp_path / "unsafe.log"),
            "ANSIBLE_ROLES_PATH": os.environ["ANSIBLE_ROLES_PATH"],
            "TOFU_INVENTORY_PATH": str(ROOT / "tests" / "inventory_load" / "tofu_inventory.json"),
        }
        if not dry_run:
            environment["PROXMOX_SUBDOMAIN"] = "example.invalid"
        if fail == "/health":
            oci_http.fail_health = True
        elif fail:
            environment["OCI_STUB_FAIL"] = fail
            if fail_owner:
                environment["OCI_STUB_FAIL_OWNER"] = fail_owner
        if fail_also:
            environment["OCI_STUB_FAIL_ALSO"] = fail_also
        base_url = f"http://127.0.0.1:{oci_http.server_address[1]}"
        extra_vars = {
            "oci_app_upgrade_dry_run": dry_run,
            "oci_app_upgrade_ntfy_url": f"{base_url}/keystone",
            "oci_app_upgrades": [
                {
                    "vmid": 123,
                    "image": "ghcr.io/example/app:1.2.3",
                    "template": "local:vztmpl/debian-12-standard_12.8-1_amd64.tar.zst",
                    "current_template": "local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst",
                    "health_url": f"{base_url}/health",
                }
            ],
        }
        if not dry_run:
            extra_vars.update(
                {
                    "oci_app_upgrade_health_retries": 1,
                    "oci_app_upgrade_health_delay": 0,
                    "pve_ha_enabled": True,
                    "pve_ha_config_host": PROXMOX_HOST,
                    "ansible_virtualization_type": "kvm",
                }
            )

        return subprocess.run(
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
            timeout=180,
        )
    return run


def assert_ordered_calls(logged_argv: list[list[str]], expected: list[tuple[str, ...]]) -> None:
    position = 0
    for call in expected:
        position = next(
            (
                index
                for index in range(position, len(logged_argv))
                if tuple(logged_argv[index][: len(call)]) == call
            ),
            -1,
        )
        assert position >= 0, f"missing or out-of-order call {call}: {logged_argv}"
        position += 1


def assert_no_volume_destruction(oci_command_log: Path, logged_argv: list[list[str]]) -> None:
    unsafe_log = oci_command_log.with_name("unsafe.log")
    assert not unsafe_log.read_text(), unsafe_log.read_text()
    volume_deletes = [
        argv
        for argv in logged_argv
        if tuple(argv[:2]) in {("pct", "destroy-volume"), ("pvesm", "free")}
    ]
    assert not volume_deletes, f"volume deletion commands reached stubs: {volume_deletes}"
