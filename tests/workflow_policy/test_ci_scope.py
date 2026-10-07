#!/usr/bin/env python3
"""Keep the required CI gate focused before main and complete after merge."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
GATE = (ROOT / ".github/workflows/ci-gate.yml").read_text()
MOLECULE = (ROOT / ".github/workflows/molecule.yml").read_text()


class CiScopeContract(unittest.TestCase):
    def test_develop_push_uses_shared_scenario_selection(self):
        self.assertIn("needs.ci.outputs.molecule == 'true'", GATE)
        self.assertIn("github.event_name == 'push'", GATE)
        self.assertNotRegex(GATE, r"github\.event_name == 'push'\s*\|\|")

    def test_only_main_push_requests_full_matrix(self):
        self.assertRegex(
            GATE,
            r"github\.event_name == 'push' && github\.ref == 'refs/heads/main'\s*&&\s*'FULL'",
        )
        self.assertIn("inputs.scenarios == 'FULL'", MOLECULE)
        self.assertIn("inputs.scenarios != 'FULL'", MOLECULE)

    def test_workflow_changes_have_a_caller_contract(self):
        self.assertIn("molecule_contract_filters: |", GATE)
        self.assertIn("- '.github/workflows/ci-gate.yml'", GATE)
        self.assertIn("- '.github/workflows/molecule.yml'", GATE)
        self.assertIn("tests/workflow_policy/**", GATE)


if __name__ == "__main__":
    unittest.main()
