#!/usr/bin/env python3
"""Keep the required CI gate focused before main and complete after merge."""

import fnmatch
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GATE = (ROOT / ".github/workflows/ci-gate.yml").read_text()
MOLECULE = (ROOT / ".github/workflows/molecule.yml").read_text()
PROMOTION_PATHS = json.loads(
    (ROOT / "tests/workflow_policy/fixtures/promotion-unmapped-paths.json").read_text()
)


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

    def test_paths_from_promotion_failure_are_covered_by_scenarios_or_contracts(self):
        contract_section = GATE.split("molecule_contract_filters: |", 1)[1].split(
            "molecule_scenario_filters: |", 1
        )[0]
        scenario_section = GATE.split("molecule_scenario_filters: |", 1)[1].split(
            "# Opt in to the shared Renovate-annotation gate", 1
        )[0]
        contract_patterns = re.findall(r"^\s+- '([^']+)'$", contract_section, re.MULTILINE)
        scenario_patterns = re.findall(r"^\s+- '([^']+)'$", scenario_section, re.MULTILINE)

        for changed_path in PROMOTION_PATHS["unmapped_paths"]:
            patterns = contract_patterns + scenario_patterns
            covered = any(
                fnmatch.fnmatchcase(changed_path, pattern) for pattern in patterns
            )
            self.assertTrue(
                covered, f"promotion path has no focused CI mapping: {changed_path}"
            )

        self.assertTrue(
            any(
                fnmatch.fnmatchcase("roles/lxc_features/tasks/main.yml", pattern)
                for pattern in scenario_patterns
            )
        )

    def test_redacted_host_path_keeps_shared_full_matrix_classification(self):
        path = PROMOTION_PATHS["redacted_full_matrix_path"].replace(
            "<redacted>", "fixture-node"
        )
        self.assertTrue(fnmatch.fnmatchcase(path, "inventory/host_vars/**"))


if __name__ == "__main__":
    unittest.main()
