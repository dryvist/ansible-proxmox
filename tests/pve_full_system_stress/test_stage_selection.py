"""Exercise stage validation and real scheduling tasks without host changes."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFY_SELECTION = ROOT / "tests/pve_full_system_stress/verify_stage_selection.yml"
VERIFY_SCHEDULE = ROOT / "tests/pve_full_system_stress/verify_schedule.yml"
VERIFY_STATUS = ROOT / "tests/pve_full_system_stress/verify_status.yml"
STATUS_FIXTURE = ROOT / "tests/pve_full_system_stress/fixtures/absent-stage-unit-status.txt"
RUN_ID = "01234567-89ab-cdef-0123-456789abcdef"
ALL_STAGES = ["memory", "cpu", "storage", "gpu", "combined"]


class StageSelection(unittest.TestCase):
    def run_playbook(self, playbook: Path, extra_vars: dict[str, object] | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        command = ["ansible-playbook", str(playbook), "-i", "localhost,", "-c", "local"]
        if playbook in (VERIFY_SCHEDULE, VERIFY_STATUS):
            command.extend(["--tags", "pve_full_system_stress"])
        if extra_vars:
            command.extend(["-e", json.dumps(extra_vars)])
        return subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=False)

    def test_default_subset_and_minimum_duration(self) -> None:
        result = self.run_playbook(VERIFY_SELECTION)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_schedule_uses_only_selected_stages(self) -> None:
        for stages in (ALL_STAGES, ["gpu", "combined"]):
            with self.subTest(stages=stages), tempfile.TemporaryDirectory() as temp:
                temp_path = Path(temp)
                bin_dir = temp_path / "bin"
                bin_dir.mkdir()
                log = temp_path / "systemd-run.log"
                for command, body in {
                    "date": '#!/bin/sh\nprintf "1000\\n"\n',
                    "logger": "#!/bin/sh\nexit 0\n",
                    "systemd-run": '#!/bin/sh\nprintf "%s\\n" "$*" >> "$MOCK_SYSTEMD_RUN_LOG"\n',
                }.items():
                    executable = bin_dir / command
                    executable.write_text(body, encoding="utf-8")
                    executable.chmod(0o755)

                result = self.run_playbook(
                    VERIFY_SCHEDULE,
                    {"pve_full_system_stress_stages": stages},
                    {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "MOCK_SYSTEMD_RUN_LOG": str(log)},
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                scheduled = log.read_text(encoding="utf-8").splitlines()
                self.assertEqual(len(scheduled), len(stages))
                self.assertEqual(
                    [next(stage for stage in ALL_STAGES if f"-{RUN_ID}-{stage}" in line) for line in scheduled],
                    stages,
                )

    def test_status_reports_selected_and_skipped_stages_from_target_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            bin_dir = temp_path / "bin"
            bin_dir.mkdir()
            fixture_text = STATUS_FIXTURE.read_text(encoding="utf-8").splitlines()[-1]
            for command, body in {
                "systemctl": f"#!/bin/sh\nprintf '%s\\n' '{fixture_text}'\n",
                "journalctl": "#!/bin/sh\nexit 0\n",
            }.items():
                executable = bin_dir / command
                executable.write_text(body, encoding="utf-8")
                executable.chmod(0o755)
            result = self.run_playbook(
                VERIFY_STATUS,
                {
                    "pve_full_system_stress_stages": ["gpu", "combined"],
                    "pve_full_system_stress_run_id": RUN_ID,
                },
                {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("selected_stages=gpu,combined", result.stdout)
            self.assertIn("skipped_stages=memory,cpu,storage", result.stdout)
            self.assertIn("unit_gpu_timer=success,not-found,inactive,dead", result.stdout)
            self.assertNotIn("unit_storage_timer=", result.stdout)


if __name__ == "__main__":
    unittest.main()
