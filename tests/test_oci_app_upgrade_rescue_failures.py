"""Failure injection coverage for OCI app upgrade recovery."""

import shlex
import subprocess
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Callable

import pytest

from oci_app_upgrade_rescue_harness import (
    assert_no_volume_destruction,
    oci_command_log,
    oci_http,
    run_oci_app_upgrade,
)


@pytest.mark.parametrize(
    ("failure", "ct_destroyed"),
    [
        ("pct create 990000", False),
        ("pct create 123", True),
        ("pct move-volume 123", False),
        ("pct move-volume 990000", True),
        ("/health", True),
        ("pct shutdown 123", False),
    ],
    ids=("holder-create", "ct-create", "move-out", "move-back", "health", "shutdown"),
)
def test_apply_failures_notify_and_restore_state(
    oci_command_log: Path,
    oci_http: ThreadingHTTPServer,
    run_oci_app_upgrade: Callable[..., subprocess.CompletedProcess[str]],
    failure: str,
    ct_destroyed: bool,
) -> None:
    result = run_oci_app_upgrade(dry_run=False, fail=failure)
    assert result.returncode != 0, f"injected failure did not stop apply\n{result.stdout}"
    assert "The rescue ran" in result.stdout or "The rescue ran" in result.stderr, (
        f"rescue completion not reported\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    logged_argv = [shlex.split(line) for line in oci_command_log.read_text().splitlines()]
    notify_posts = [r for r in oci_http.requests if r[:2] == ("POST", "/keystone")]
    assert notify_posts, f"no ntfy post reached the server: {oci_http.requests}"
    assert b"CT 123" in notify_posts[-1][2], notify_posts

    ct_destroys = [
        argv
        for argv in logged_argv
        if argv[:2] == ["pct", "destroy"] and len(argv) > 2 and argv[2] == "123"
    ]
    if ct_destroyed:
        assert ct_destroys, f"expected CT destroy before rescue: {logged_argv}"
        old_template_creates = [
            argv
            for argv in logged_argv
            if argv[:3] == ["pct", "create", "123"]
            and "local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst" in argv
        ]
        assert old_template_creates, f"rescue did not recreate the old template: {logged_argv}"
    else:
        assert not ct_destroys, f"CT was destroyed before failure: {ct_destroys}"

    ha_removes = [
        i for i, argv in enumerate(logged_argv) if argv[:3] == ["ha-manager", "remove", "ct:123"]
    ]
    ha_adds = [
        i for i, argv in enumerate(logged_argv) if argv[:3] == ["ha-manager", "add", "ct:123"]
    ]
    replication_deletes = [
        i for i, argv in enumerate(logged_argv) if argv[:3] == ["pvesr", "delete", "123-0"]
    ]
    replication_creates = [
        i for i, argv in enumerate(logged_argv) if argv[:3] == ["pvesr", "create-local-job", "123-0"]
    ]
    assert ha_removes and ha_adds and ha_adds[-1] > ha_removes[-1], logged_argv
    assert (
        replication_deletes
        and replication_creates
        and replication_creates[-1] > replication_deletes[-1]
    ), logged_argv
    assert_no_volume_destruction(oci_command_log, logged_argv)


def test_failure_with_volume_on_holder_moves_it_back(
    oci_command_log: Path,
    oci_http: ThreadingHTTPServer,
    run_oci_app_upgrade: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    # The first read after the move-out fails, before the destroy starts.
    result = run_oci_app_upgrade(
        dry_run=False, fail="pvesh get /nodes/pve-w1700/lxc/123/config", fail_owner="990000"
    )
    assert result.returncode != 0, result.stdout
    logged_argv = [shlex.split(line) for line in oci_command_log.read_text().splitlines()]
    assert not any(argv[:3] == ["pct", "destroy", "123"] for argv in logged_argv), logged_argv
    move_back = ["pct", "move-volume", "990000", "mp0", "--target-vmid", "123"]
    assert any(argv[:6] == move_back for argv in logged_argv), logged_argv
    assert any(argv[:3] == ["pct", "destroy", "990000"] for argv in logged_argv), logged_argv
    assert any(argv[:3] == ["ha-manager", "add", "ct:123"] for argv in logged_argv), logged_argv
    assert_no_volume_destruction(oci_command_log, logged_argv)


def test_failed_recovery_posts_a_second_notice_and_stops(
    oci_command_log: Path,
    oci_http: ThreadingHTTPServer,
    run_oci_app_upgrade: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    result = run_oci_app_upgrade(dry_run=False, fail="pct create 990000", fail_also="pct start 123")
    assert result.returncode != 0, result.stdout
    assert "the recovery also failed" in " ".join(result.stdout.split()), result.stdout
    posts = [body for method, path, body in oci_http.requests if (method, path) == ("POST", "/keystone")]
    assert len(posts) == 2, oci_http.requests
    assert b"Recovery starts now" in posts[0] and b"The recovery failed" in posts[1], posts
    logged_argv = [shlex.split(line) for line in oci_command_log.read_text().splitlines()]
    assert not any(argv[:3] == ["pct", "destroy", "123"] for argv in logged_argv), logged_argv
    assert_no_volume_destruction(oci_command_log, logged_argv)
