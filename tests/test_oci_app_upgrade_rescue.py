"""Offline smoke coverage for OCI app upgrade dry-run and apply paths."""

import re
import shlex
import subprocess
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from oci_app_upgrade_rescue_harness import (
    MUTATING_COMMANDS,
    PROXMOX_HOST,
    assert_no_volume_destruction,
    assert_ordered_calls,
    oci_command_log,
    oci_http,
    run_oci_app_upgrade,
)


def test_default_dry_run_does_not_call_mutating_commands(
    oci_command_log: Path,
    run_oci_app_upgrade: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    result = run_oci_app_upgrade()

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


def test_apply_happy_path_swaps_image_and_restores_membership(
    oci_command_log: Path,
    oci_http: ThreadingHTTPServer,
    run_oci_app_upgrade: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    result = run_oci_app_upgrade(dry_run=False)
    assert result.returncode == 0, (
        f"ansible-playbook exited with {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    logged_argv = [shlex.split(line) for line in oci_command_log.read_text().splitlines()]
    assert_ordered_calls(
        logged_argv,
        [
            ("ha-manager", "remove", "ct:123"),
            ("pvesr", "delete", "123-0"),
            ("pct", "create", "990000"),
            ("pct", "move-volume", "123", "mp0", "--target-vmid", "990000"),
            ("pct", "destroy", "123", "--purge"),
            ("pct", "create", "123"),
            ("pct", "move-volume", "990000", "mp0", "--target-vmid", "123"),
            ("ha-manager", "add", "ct:123"),
            ("pvesr", "create-local-job", "123-0", "pve-w1701"),
        ],
    )
    recreate = next(argv for argv in logged_argv if argv[:3] == ["pct", "create", "123"])
    rootfs = recreate[recreate.index("--rootfs") + 1]
    assert rootfs == "local-lvm:8,acl=1,mountoptions=noatime", recreate
    requests = [(method, path) for method, path, _ in oci_http.requests]
    assert ("GET", "/health") in requests, requests
    assert not any(method == "POST" for method, _ in requests), requests
    assert_no_volume_destruction(oci_command_log, logged_argv)
