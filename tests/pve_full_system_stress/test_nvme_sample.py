"""Exercise the NVMe guard's JSON parsing without a Proxmox host."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARDS = ROOT / "roles/pve_full_system_stress/files/pve-full-system-stress-guards.sh"


def stub(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text("#!/usr/bin/env bash\n" + body + "\n", encoding="utf-8")
    path.chmod(0o755)


class NvmeSample(unittest.TestCase):
    def sample(self, smart_json: str) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as temp:
            tmp = Path(temp)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            events = tmp / "events"
            stub(bin_dir, "zpool", "echo '  /dev/disk/by-id/nvme-test-part3 ONLINE 0 0 0'")
            stub(bin_dir, "lsblk", "echo nvme0n1")
            stub(bin_dir, "nvme", f"cat <<'EOF'\n{smart_json}\nEOF")
            stub(bin_dir, "logger", f"echo \"$*\" >> {events}")
            script = f"source {GUARDS}; rpool=rpool run_id=t stage=storage; sample_nvme"
            result = subprocess.run(
                ["bash", "-c", script],
                env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode, events.read_text(encoding="utf-8") if events.exists() else ""

    def test_kelvin_json_reports_celsius(self) -> None:
        rc, events = self.sample('{\n  "critical_warning":0,\n  "temperature":314\n}')
        self.assertEqual(rc, 0)
        self.assertIn("nvme_temp_c=41", events)

    def test_critical_warning_fails(self) -> None:
        rc, _ = self.sample('{"critical_warning":4,"temperature":320}')
        self.assertEqual(rc, 1)

    def test_missing_fields_are_unavailable(self) -> None:
        rc, _ = self.sample("{}")
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
