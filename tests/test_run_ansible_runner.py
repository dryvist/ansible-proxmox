"""Contract tests for the pinned shared Ansible runner shim."""

import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run-ansible.sh"
SHARED_RUNNER = "github:dryvist/homelab-contracts/v5.31.0#run-ansible"


class RunAnsibleShimContract(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.bin_path = self.temp_path / "bin"
        self.bin_path.mkdir()
        self.args_log = self.temp_path / "nix-args.log"
        self.env_log = self.temp_path / "runner-env.log"
        fake_nix = self.bin_path / "nix"
        fake_nix.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                printf '%s\\n' "$@" > "$NIX_ARGS_LOG"
                printf '%s\\n' \
                  "$RUN_ANSIBLE_IDENTITIES" \
                  "$RUN_ANSIBLE_FALLBACK_ON_ERROR" \
                  "$RUN_ANSIBLE_SSH_AGENT" \
                  "$RUN_ANSIBLE_LIMIT_LOCALHOST" \
                  "${NIX_SHELL-unset}" > "$NIX_ENV_LOG"
                exit "${FAKE_NIX_STATUS:-0}"
                """
            ),
            encoding="utf-8",
        )
        fake_nix.chmod(0o700)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _run(self, *args, extra_env=None, status=0):
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{self.bin_path}{os.pathsep}{env['PATH']}",
                "NIX_ARGS_LOG": str(self.args_log),
                "NIX_ENV_LOG": str(self.env_log),
                "FAKE_NIX_STATUS": str(status),
            }
        )
        env.pop("RUN_ANSIBLE_IDENTITIES", None)
        env.pop("RUN_ANSIBLE_FALLBACK_ON_ERROR", None)
        env.pop("RUN_ANSIBLE_SSH_AGENT", None)
        env.pop("RUN_ANSIBLE_LIMIT_LOCALHOST", None)
        env.pop("NIX_SHELL", None)
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [str(RUNNER), *args],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_pins_shared_runner_sets_repo_defaults_and_forwards_args(self):
        result = self._run(
            "playbooks/site.yml",
            "--limit",
            "pve hosts",
            "--check",
            status=37,
        )

        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertEqual(
            self.args_log.read_text(encoding="utf-8").splitlines(),
            [
                "run",
                SHARED_RUNNER,
                "--",
                "playbooks/site.yml",
                "--limit",
                "pve hosts",
                "--check",
            ],
        )
        self.assertEqual(
            self.env_log.read_text(encoding="utf-8").splitlines(),
            ["semaphore?,ansible", "1", "1", "1", "unset"],
        )

    def test_preserves_environment_overrides_including_nix_shell(self):
        nix_shell = "github:dryvist/ansible-proxmox#default"
        result = self._run(
            "playbooks/site.yml",
            extra_env={
                "RUN_ANSIBLE_IDENTITIES": "ansible",
                "RUN_ANSIBLE_FALLBACK_ON_ERROR": "0",
                "RUN_ANSIBLE_SSH_AGENT": "enabled",
                "RUN_ANSIBLE_LIMIT_LOCALHOST": "1",
                "NIX_SHELL": nix_shell,
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.args_log.read_text(encoding="utf-8").splitlines(),
            ["run", SHARED_RUNNER, "--", "playbooks/site.yml"],
        )
        self.assertEqual(
            self.env_log.read_text(encoding="utf-8").splitlines(),
            ["ansible", "0", "enabled", "1", nix_shell],
        )


if __name__ == "__main__":
    unittest.main()
