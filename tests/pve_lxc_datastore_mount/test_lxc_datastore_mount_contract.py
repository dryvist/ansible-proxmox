"""Exercise the role's live reconciliation decisions against pct/findmnt stubs."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAYBOOK = "tests/pve_lxc_datastore_mount/verify_reconcile.yml"


def run_fixture(tmp_path: Path, mode: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["ANSIBLE_LOCAL_TEMP"] = str(tmp_path / "ansible-local")
    environment["ANSIBLE_REMOTE_TEMP"] = str(tmp_path / "ansible-remote")
    return subprocess.run(
        [
            "ansible-playbook",
            PLAYBOOK,
            "-i",
            "localhost,",
            "-c",
            "local",
            "--extra-vars",
            json.dumps(
                {
                    "pve_lxc_datastore_mount_fixture_dir": str(tmp_path),
                    "pve_lxc_datastore_mount_fixture_mode": mode,
                }
            ),
        ],
        cwd=REPO_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def test_mismatch_sets_mount_and_weight_but_restarts_only_for_running_mount_change(
    tmp_path: Path,
) -> None:
    result = run_fixture(tmp_path, "mixed")
    assert result.returncode == 0, result.stdout + result.stderr

    commands = (tmp_path / "pct.log").read_text().splitlines()
    assert "set 212000 --mp0 /backup/guests,mp=/mnt/datastore/backup,backup=0" in commands
    assert "set 212000 --cpuunits 50" in commands
    assert "set 212000 --protection 0" in commands
    assert "set 212000 --protection 1" in commands
    assert "reboot 212000" in commands

    # A matching CT is untouched; CPU-only drift and a stopped CT do not reboot.
    assert not any(line.startswith(("set 212001 ", "reboot 212001")) for line in commands)
    assert "set 212004 --cpuunits 50" in commands
    assert not any(line.startswith(("set 212004 --mp0", "reboot 212004")) for line in commands)
    assert "set 212005 --mp0 /backup/guests,mp=/mnt/datastore/backup,backup=0" in commands
    assert "reboot 212005" not in commands

    # The absent CT reports a visible skip and is not passed to pct set.
    assert "LXC 212002 is not present (`pct status` failed); skipping its datastore mount and CPU weight." in result.stdout
    assert not any(line.startswith(("set 212002 ", "reboot 212002")) for line in commands)
    assert "changed=5" in result.stdout


def test_matching_configuration_reports_no_change(tmp_path: Path) -> None:
    result = run_fixture(tmp_path, "insync")
    assert result.returncode == 0, result.stdout + result.stderr

    commands = (tmp_path / "pct.log").read_text().splitlines()
    assert not any(line.startswith(("set ", "reboot ")) for line in commands)
    assert "changed=0" in result.stdout


def test_missing_source_mountpoint_fails_loudly(tmp_path: Path) -> None:
    result = run_fixture(tmp_path, "missing_source")
    assert result.returncode != 0
    assert "/not-mounted must be an exact findmnt mountpoint" in result.stdout + result.stderr
