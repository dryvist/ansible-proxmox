"""Exercise the GPU guard's temperature-limit parsing without a GPU host."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARDS = ROOT / "roles/pve_full_system_stress/files/pve-full-system-stress-guards.sh"

QUERY = "38, 12.15, 180, 405, 0x0000000000000000"
ABSOLUTE = "    Temperature\n        GPU Max Operating Temp            : 87 C\n"
# Driver 595 reports T.Limit headroom instead of an absolute maximum.
TLIMIT = (
    "    Temperature\n"
    "        GPU Current Temp                  : 38 C\n"
    "        GPU T.Limit Temp                  : 54 C\n"
    "        GPU Max Operating T.Limit Temp    : 0 C\n"
)


class GpuSample(unittest.TestCase):
    def sample(self, details: str, headroom: str = "54") -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as temp:
            tmp = Path(temp)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            events = tmp / "events"
            (tmp / "details").write_text(details, encoding="utf-8")
            nvidia_smi = bin_dir / "nvidia-smi"
            nvidia_smi.write_text(
                "#!/usr/bin/env bash\n"
                f'case "$*" in *tlimit*) echo "{headroom}";; "-q -d TEMPERATURE") cat {tmp / "details"};; *) echo "{QUERY}";; esac\n',
                encoding="utf-8",
            )
            nvidia_smi.chmod(0o755)
            logger = bin_dir / "logger"
            logger.write_text(f'#!/usr/bin/env bash\necho "$*" >> {events}\n', encoding="utf-8")
            logger.chmod(0o755)
            result = subprocess.run(
                ["bash", "-c", f"source {GUARDS}; run_id=t stage=gpu; sample_gpu"],
                env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode, events.read_text(encoding="utf-8") if events.exists() else ""

    def test_absolute_limit(self) -> None:
        rc, events = self.sample(ABSOLUTE)
        self.assertEqual(rc, 0)
        self.assertIn("gpu_temp_limit_c=87", events)

    def test_tlimit_headroom(self) -> None:
        rc, events = self.sample(TLIMIT)
        self.assertEqual(rc, 0)
        self.assertIn("gpu_temp_limit_c=92", events)

    def test_no_headroom_fails_limit(self) -> None:
        rc, _ = self.sample(TLIMIT, headroom="0")
        self.assertEqual(rc, 1)

    def test_unreadable_headroom_is_unavailable(self) -> None:
        rc, _ = self.sample(TLIMIT, headroom="[N/A]")
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
