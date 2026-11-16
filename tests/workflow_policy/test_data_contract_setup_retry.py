#!/usr/bin/env python3
"""Galaxy install steps in data-contract setup retry through the pinned retry action."""

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
ACTION = yaml.safe_load(
    (ROOT / ".github/actions/data-contract-setup/action.yml").read_text()
)
STEPS = ACTION["runs"]["steps"]
RETRY_REF = "nick-fields/retry@ad984534de44a9489a53aefd81eb77f87c70dc60"
INSTALL_COMMAND = "ansible-galaxy install -r requirements.yml --force"
INSTALL_STEP_NAMES = (
    "Install Ansible dependencies",
    "Refresh Ansible dependencies from requirements.yml",
)


class DataContractSetupRetryContract(unittest.TestCase):
    def test_galaxy_install_steps_use_the_pinned_retry_action(self):
        for name in INSTALL_STEP_NAMES:
            with self.subTest(step=name):
                step = next(s for s in STEPS if s["name"] == name)
                self.assertEqual(step["uses"], RETRY_REF)

    def test_galaxy_install_steps_run_the_install_with_retries(self):
        for name in INSTALL_STEP_NAMES:
            with self.subTest(step=name):
                step = next(s for s in STEPS if s["name"] == name)
                self.assertEqual(step["with"]["command"], INSTALL_COMMAND)
                self.assertGreaterEqual(step["with"]["max_attempts"], 2)

    def test_no_run_step_installs_from_galaxy(self):
        for step in STEPS:
            if "run" in step:
                self.assertNotIn(
                    "ansible-galaxy install",
                    step["run"],
                    f"unguarded galaxy install in step {step['name']!r}",
                )


if __name__ == "__main__":
    unittest.main()
