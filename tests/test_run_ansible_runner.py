"""Behavioral contracts for the OpenBao-aware Ansible runner."""

import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run-ansible.sh"
MINTED_TOKEN = "test-runner-owned-token"
CALLER_TOKEN = "test-caller-owned-token"
APPROLE_ROLE_ID = "test-role-id"
APPROLE_SECRET = "test-approle-secret"


class RunAnsibleTokenContract(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.bin_path = self.temp_path / "bin"
        self.bin_path.mkdir()
        self.event_log = self.temp_path / "events.log"
        self.jq_argv_log = self.temp_path / "jq-argv.log"
        self.tmp_path = self.temp_path / "tmp"
        self.tmp_path.mkdir()
        self._write_executable(
            "jq",
            f"""
            #!/usr/bin/env bash
            set -euo pipefail
            filter=""
            for arg in "$@"; do
              [[ $arg != "$EXPECTED_APPROLE_ROLE_ID" ]]
              [[ $arg != "$EXPECTED_APPROLE_SECRET" ]]
              printf '%s\\n' "$arg" >> "$FAKE_JQ_ARGV_LOG"
              filter=$arg
            done
            case "$filter" in
              .auth.client_token)
                cat >/dev/null
                printf '%s\\n' '{MINTED_TOKEN}'
                ;;
              .data.signed_key)
                cat >/dev/null
                printf '%s\\n' 'test-certificate'
                ;;
              *)
                printf '%s\\n' '{{}}'
                ;;
            esac
            """,
        )
        self._write_executable(
            "curl",
            f"""
            #!/usr/bin/env bash
            set -euo pipefail
            url="" header_arg="" next_is_header=false
            for arg in "$@"; do
              if $next_is_header; then
                header_arg=$arg
                next_is_header=false
                continue
              fi
              case "$arg" in
                -H|--header) next_is_header=true ;;
                http://*|https://*) url=$arg ;;
              esac
            done
            auth=""
            if [[ $header_arg == @/dev/fd/* ]]; then
              IFS= read -r auth_header < "${{header_arg#@}}"
              [[ $auth_header == "X-Vault-Token: $EXPECTED_MINTED_TOKEN" ]]
              auth=" runner-auth"
            fi
            printf 'curl %s%s\n' "$url" "$auth" >> "$FAKE_EVENT_LOG"
            case "$url" in
              */auth/approle/login)
                cat >/dev/null
                printf '%s\n' '{{"auth":{{"client_token":"{MINTED_TOKEN}"}}}}'
                ;;
              */sign/automation-ansible)
                cat >/dev/null
                [[ ${{FAKE_SIGN_FAILURE:-0}} == 0 ]] || exit 22
                printf '%s\n' '{{"data":{{"signed_key":"test-certificate"}}}}'
                ;;
              */auth/token/revoke-self)
                if [[ ${{FAKE_REVOKE_FIRST_FAILURE:-0}} == 1 ]] &&
                  [[ $(grep -c '/auth/token/revoke-self' "$FAKE_EVENT_LOG") == 1 ]]; then
                  exit 22
                fi
                ;;
              *)
                exit 2
                ;;
            esac
            """,
        )
    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_executable(self, name: str, body: str):
        path = self.bin_path / name
        path.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
        path.chmod(0o700)

    def _run(
        self,
        caller_token=None,
        sign_failure=False,
        revoke_first_failure=False,
        ansible_rc=0,
    ):
        self._write_executable(
            "ansible-playbook",
            f"""
            #!/usr/bin/env bash
            set -euo pipefail
            printf 'ansible\n' >> "$FAKE_EVENT_LOG"
            [[ ${{BAO_TOKEN:-}} == "$EXPECTED_CHILD_BAO_TOKEN" ]]
            printf 'child received expected token\n'
            exit {ansible_rc}
            """,
        )
        env = os.environ.copy()
        env.pop("NIX_SHELL", None)
        env.update(
            {
                "BAO_ADDR": "https://openbao.test",
                "OPENBAO_APPROLE_ANSIBLE_ROLE_ID": APPROLE_ROLE_ID,
                "OPENBAO_APPROLE_ANSIBLE_SECRET_ID": APPROLE_SECRET,
                "EXPECTED_APPROLE_ROLE_ID": APPROLE_ROLE_ID,
                "EXPECTED_APPROLE_SECRET": APPROLE_SECRET,
                "EXPECTED_CHILD_BAO_TOKEN": caller_token or MINTED_TOKEN,
                "EXPECTED_MINTED_TOKEN": MINTED_TOKEN,
                "FAKE_EVENT_LOG": str(self.event_log),
                "FAKE_JQ_ARGV_LOG": str(self.jq_argv_log),
                "FAKE_SIGN_FAILURE": "1" if sign_failure else "0",
                "FAKE_REVOKE_FIRST_FAILURE": "1" if revoke_first_failure else "0",
                "PATH": f"{self.bin_path}{os.pathsep}{env['PATH']}",
                "TMPDIR": str(self.tmp_path),
            }
        )
        if caller_token is None:
            env.pop("BAO_TOKEN", None)
        else:
            env["BAO_TOKEN"] = caller_token

        return subprocess.run(
            [str(RUNNER), "playbooks/site.yml", "--limit", "localhost"],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

    def _assert_no_secret_leak(self, result):
        output = result.stdout + result.stderr
        events = self.event_log.read_text(encoding="utf-8")
        jq_argv = self.jq_argv_log.read_text(encoding="utf-8")
        for secret in (MINTED_TOKEN, CALLER_TOKEN, APPROLE_ROLE_ID, APPROLE_SECRET):
            self.assertNotIn(secret, output)
            self.assertNotIn(secret, events)
            self.assertNotIn(secret, jq_argv)

    def _assert_cert_cleanup(self):
        self.assertEqual(list(self.tmp_path.glob("ansible-sshcert.*")), [])

    def test_minted_token_reaches_child_then_is_revoked(self):
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.event_log.read_text(encoding="utf-8").splitlines(),
            [
                "curl https://openbao.test/v1/auth/approle/login",
                "curl https://openbao.test/v1/ssh-client-ca/sign/automation-ansible runner-auth",
                "ansible",
                "curl https://openbao.test/v1/auth/token/revoke-self runner-auth",
            ],
        )
        self._assert_no_secret_leak(result)
        self._assert_cert_cleanup()

    def test_caller_token_is_preserved_and_runner_token_revoked_before_child(self):
        result = self._run(caller_token=CALLER_TOKEN)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.event_log.read_text(encoding="utf-8").splitlines(),
            [
                "curl https://openbao.test/v1/auth/approle/login",
                "curl https://openbao.test/v1/ssh-client-ca/sign/automation-ansible runner-auth",
                "curl https://openbao.test/v1/auth/token/revoke-self runner-auth",
                "ansible",
            ],
        )
        self._assert_no_secret_leak(result)
        self._assert_cert_cleanup()

    def test_sign_failure_is_loud_and_revokes_minted_token(self):
        result = self._run(sign_failure=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OpenBao SSH cert mint FAILED", result.stderr)
        self.assertEqual(
            self.event_log.read_text(encoding="utf-8").splitlines(),
            [
                "curl https://openbao.test/v1/auth/approle/login",
                "curl https://openbao.test/v1/ssh-client-ca/sign/automation-ansible runner-auth",
                "curl https://openbao.test/v1/auth/token/revoke-self runner-auth",
            ],
        )
        self._assert_no_secret_leak(result)
        self._assert_cert_cleanup()

    def test_failed_immediate_revoke_retries_only_runner_token_at_exit(self):
        result = self._run(
            caller_token=CALLER_TOKEN,
            revoke_first_failure=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.event_log.read_text(encoding="utf-8").splitlines(),
            [
                "curl https://openbao.test/v1/auth/approle/login",
                "curl https://openbao.test/v1/ssh-client-ca/sign/automation-ansible runner-auth",
                "curl https://openbao.test/v1/auth/token/revoke-self runner-auth",
                "ansible",
                "curl https://openbao.test/v1/auth/token/revoke-self runner-auth",
            ],
        )
        self._assert_no_secret_leak(result)
        self._assert_cert_cleanup()

    def test_ansible_failure_status_is_preserved_and_runner_token_is_revoked(self):
        result = self._run(ansible_rc=42)

        self.assertEqual(result.returncode, 42, result.stderr)
        self.assertEqual(
            self.event_log.read_text(encoding="utf-8").splitlines(),
            [
                "curl https://openbao.test/v1/auth/approle/login",
                "curl https://openbao.test/v1/ssh-client-ca/sign/automation-ansible runner-auth",
                "ansible",
                "curl https://openbao.test/v1/auth/token/revoke-self runner-auth",
            ],
        )
        self._assert_no_secret_leak(result)
        self._assert_cert_cleanup()

if __name__ == "__main__":
    unittest.main()
