"""Exercise ECC detection and both EDAC guard paths without a Proxmox host."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARDS = ROOT / "roles/pve_full_system_stress/files/pve-full-system-stress-guards.sh"
VERIFY = ROOT / "tests/pve_full_system_stress/verify_memory_ecc.yml"
VERIFY_EDAC = ROOT / "tests/pve_full_system_stress/verify_edac_preflight.yml"

NONE = """\
Handle 0x0010, DMI type 16, 23 bytes
Physical Memory Array
\tError Correction Type: None
"""

ECC = """\
Handle 0x0010, DMI type 16, 23 bytes
Physical Memory Array
\tError Correction Type: Multi-bit ECC
"""

PARITY = """\
Handle 0x0010, DMI type 16, 23 bytes
Physical Memory Array
\tError Correction Type: Parity
"""


class MemoryEcc(unittest.TestCase):
    @staticmethod
    def install_logger(bin_dir: Path) -> None:
        logger = bin_dir / "logger"
        logger.write_text(
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "with open(os.environ['LOGGER_EVENTS'], 'a', encoding='utf-8') as log:\n"
            "    log.write(' '.join(sys.argv[1:]) + '\\n')\n",
            encoding="utf-8",
        )
        logger.chmod(0o755)

    def run_detection(
        self,
        fixture: str,
        expected: bool,
        *,
        fail_dmidecode: bool = False,
        succeeds: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp:
            tmp = Path(temp)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            dmidecode = bin_dir / "dmidecode"
            dmidecode.write_text(
                "#!/usr/bin/env python3\n"
                "import os, pathlib, sys\n"
                "if os.environ.get('DMIDECODE_FAIL'):\n"
                "    raise SystemExit(2)\n"
                "if sys.argv[1:] != ['--type', '16']:\n"
                "    raise SystemExit(2)\n"
                "sys.stdout.write(pathlib.Path(os.environ['DMIDECODE_FIXTURE']).read_text())\n",
                encoding="utf-8",
            )
            dmidecode.chmod(0o755)
            log_path = tmp / "logger-events.txt"
            self.install_logger(bin_dir)
            fixture_path = tmp / "dmidecode.txt"
            fixture_path.write_text(fixture, encoding="utf-8")
            env = os.environ.copy()
            env.update(
                {
                    "ANSIBLE_NOCOLOR": "1",
                    "ANSIBLE_LOCAL_TEMP": str(tmp / "ansible-tmp"),
                    "DMIDECODE_FIXTURE": str(fixture_path),
                    "LOGGER_EVENTS": str(log_path),
                    "PATH": f"{bin_dir}:{env['PATH']}",
                    "PVE_FULL_SYSTEM_STRESS_EXPECTED_ECC": str(expected).lower(),
                    "DMIDECODE_FAIL": "1" if fail_dmidecode else "",
                }
            )
            (tmp / "ansible-tmp").mkdir()
            command = ["ansible-playbook", str(VERIFY), "-i", "localhost,", "-c", "local"]
            result = subprocess.run(
                command,
                env=env,
                capture_output=True,
                text=True,
            )
            if succeeds:
                self.assertEqual(result.returncode, 0, f"{result.stdout}\n{result.stderr}")
            self.logger_events = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
            return result

    def run_guard_sample(
        self, memory_ecc: bool, edac_result: str
    ) -> subprocess.CompletedProcess[str]:
        edac_function = (
            "edac_counts() { return 2; }"
            if edac_result == "__return_2__"
            else f"edac_counts() {{ printf '%s\\n' '{edac_result}'; }}"
        )
        harness = f"""\
set -Eeuo pipefail
source "$1"
memory_ecc={str(memory_ecc).lower()}
run_id=test
stage=memory
watch_gpu=false
campaign_started_at=now
logger() {{ printf 'logger %s\\n' "$*"; }}
log() {{ printf 'log %s\\n' "$*"; }}
abort() {{ printf 'abort=%s\\n' "$1" >&2; exit 70; }}
kernel_counts() {{ mce_count=0; xid_count=0; }}
serving_guard() {{ return 0; }}
sample_cpu() {{ return 0; }}
{edac_function}
guard_sample
"""
        return subprocess.run(
            ["bash", "-c", harness, "guard-sample", str(GUARDS)],
            capture_output=True,
            text=True,
        )

    def run_edac_preflight(
        self, memory_ecc: bool, counter: str | None, *, succeeds: bool = True
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp:
            tmp = Path(temp)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            log_path = tmp / "logger-events.txt"
            self.install_logger(bin_dir)
            counter_path = tmp / "mc0" / "ue_count"
            if counter is not None:
                counter_path.parent.mkdir()
                counter_path.write_text(counter, encoding="utf-8")
            env = os.environ.copy()
            env.update(
                {
                    "ANSIBLE_NOCOLOR": "1",
                    "ANSIBLE_LOCAL_TEMP": str(tmp / "ansible-tmp"),
                    "PVE_FULL_SYSTEM_STRESS_MEMORY_ECC": str(memory_ecc).lower(),
                    "PVE_FULL_SYSTEM_STRESS_UE_COUNT_FILES": str(counter_path),
                    "LOGGER_EVENTS": str(log_path),
                    "PATH": f"{bin_dir}:{os.environ['PATH']}",
                }
            )
            (tmp / "ansible-tmp").mkdir()
            result = subprocess.run(
                ["ansible-playbook", str(VERIFY_EDAC), "-i", "localhost,", "-c", "local"],
                env=env,
                capture_output=True,
                text=True,
            )
            if succeeds:
                self.assertEqual(result.returncode, 0, f"{result.stdout}\n{result.stderr}")
            self.logger_events = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
            return result

    def test_smbios_none_selects_non_ecc_path(self) -> None:
        self.run_detection(NONE, False)

    def test_smbios_ecc_selects_ecc_path(self) -> None:
        self.run_detection(ECC, True)

    def test_smbios_parity_selects_non_ecc_path(self) -> None:
        self.run_detection(PARITY, False)

    def test_unavailable_smbios_fails_closed(self) -> None:
        result = self.run_detection("", False, fail_dmidecode=True, succeeds=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("event=memory_capability decision=rejected", self.logger_events)

    def test_unrecognized_smbios_capability_fails_closed(self) -> None:
        result = self.run_detection(
            "Error Correction Type: Unknown\n", False, succeeds=False
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("event=memory_capability decision=rejected", self.logger_events)

    def test_non_ecc_sampling_does_not_require_edac_counters(self) -> None:
        result = self.run_guard_sample(False, "not_applicable")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("memory_ecc=false", result.stdout)
        self.assertIn("edac=not_applicable", result.stdout)
        self.assertNotIn("edac_counters_unavailable", result.stderr)

    def test_ecc_sampling_still_aborts_on_uncorrected_edac_count(self) -> None:
        result = self.run_guard_sample(True, "0 1")
        self.assertEqual(result.returncode, 70)
        self.assertIn("abort=edac_ue", result.stderr)

    def test_ecc_sampling_still_requires_edac_counters(self) -> None:
        result = self.run_guard_sample(True, "__return_2__")
        self.assertEqual(result.returncode, 70)
        self.assertIn("abort=edac_counters_unavailable", result.stderr)

    def test_non_ecc_preflight_skips_missing_edac_counters(self) -> None:
        self.run_edac_preflight(False, None)
        self.assertIn(
            "event=edac_guard memory_ecc=false decision=not_applicable",
            self.logger_events,
        )

    def test_ecc_preflight_requires_and_accepts_zero_counter(self) -> None:
        result = self.run_edac_preflight(True, "0")
        self.assertIn("Read aggregate EDAC uncorrected-error counters", result.stdout)

    def test_ecc_preflight_refuses_missing_counter(self) -> None:
        result = self.run_edac_preflight(True, None, succeeds=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reason=edac_counters_unavailable", self.logger_events)

    def test_ecc_preflight_refuses_uncorrected_counter(self) -> None:
        result = self.run_edac_preflight(True, "1", succeeds=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("EDAC reports an uncorrected memory error", result.stdout)

    def test_ecc_counter_reader_aggregates_corrected_and_uncorrected_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            counts = (("mc0", "2", "0"), ("mc1", "3", "0"))
            for controller, corrected, uncorrected in counts:
                path = root / controller
                path.mkdir()
                (path / "ce_count").write_text(corrected, encoding="utf-8")
                (path / "ue_count").write_text(uncorrected, encoding="utf-8")
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    'set -e; source "$1"; edac_counts true "$2"',
                    "edac-counts",
                    str(GUARDS),
                    temp,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.stdout.strip(), "5 0")


if __name__ == "__main__":
    unittest.main()
