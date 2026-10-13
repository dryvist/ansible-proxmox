"""Pin check-mode guards on writes into the temporary boot mount."""

from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS = yaml.safe_load((ROOT / "roles/crash_diagnostics/tasks/main.yml").read_text())
WRITE_TASKS = (
    "Copy memtest86+ to boot partition",
    "Deploy custom GRUB config with memtest entry to boot partition",
)


class MemtestCheckMode(unittest.TestCase):
    def test_boot_partition_writes_skip_check_mode(self):
        guarded_tasks = [
            task["name"]
            for task in TASKS
            if task.get("name") in WRITE_TASKS
            and "not ansible_check_mode" in task.get("when", [])
        ]

        self.assertEqual(guarded_tasks, list(WRITE_TASKS))


if __name__ == "__main__":
    unittest.main()
