#!/usr/bin/env python3
"""Keep the required CI gate focused before main and complete after merge."""

import fnmatch
import json
import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
GATE_SOURCE = (ROOT / ".github/workflows/ci-gate.yml").read_text()
CENTRAL_MOLECULE_REF = "JacobPEvans/.github/.github/workflows/_molecule.yml@v1"
GATE_NODE = yaml.compose(GATE_SOURCE)
GATE = yaml.safe_load(GATE_SOURCE)
PROMOTION_PATHS = json.loads(
    (ROOT / "tests/workflow_policy/fixtures/promotion-unmapped-paths.json").read_text()
)

CONTRACT_FILTERS = yaml.safe_load(
    GATE["jobs"]["ci"]["with"]["molecule_contract_filters"]
)["contract_only"]
SCENARIO_FILTERS = yaml.safe_load(
    GATE["jobs"]["ci"]["with"]["molecule_scenario_filters"]
)
SCENARIO_PATTERNS = [
    pattern for filters in SCENARIO_FILTERS.values() for pattern in filters
]


def mapping_value(node, key):
    return next(value for key_node, value in node.value if key_node.value == key)


class CiScopeContract(unittest.TestCase):
    def test_develop_push_uses_shared_scenario_selection(self):
        molecule = GATE["jobs"]["molecule"]
        self.assertEqual(molecule["needs"], "changes")
        self.assertEqual(molecule["uses"], CENTRAL_MOLECULE_REF)
        self.assertEqual(
            {clause.strip() for clause in molecule["if"].split("||")},
            {"needs.changes.outputs.molecule == 'true'", "github.event_name == 'push'"},
        )
        self.assertIn(
            "needs.changes.outputs.molecule_scenarios", molecule["with"]["scenarios"]
        )
        self.assertEqual(molecule["with"]["scenario_discovery"], "directories")
        self.assertIs(molecule["with"]["scenario_require_molecule_yml"], True)
        self.assertEqual(molecule["with"]["molecule_roles_path"], "roles")

        jobs = GATE["jobs"]
        self.assertEqual(set(jobs["gate"]["needs"]), set(jobs) - {"gate"})
        allowed_skips = next(
            step["with"]["allowed-skips"]
            for step in jobs["gate"]["steps"]
            if step["name"] == "Check all results"
        )
        match = re.fullmatch(
            r"\$\{\{\s*github\.event_name\s*==\s*'pull_request'\s*"
            r"&&\s*'([^']+)'\s*\|\|\s*''\s*\}\}",
            allowed_skips,
        )
        self.assertIsNotNone(match)
        self.assertEqual(match[1], "molecule,static-contracts")

    def test_only_main_push_requests_full_matrix(self):
        self.assertRegex(
            GATE["jobs"]["molecule"]["with"]["full_suite"],
            r"github\.event_name == 'push'\s*&&\s*github\.ref == 'refs/heads/main'",
        )
        manual = yaml.safe_load((ROOT / ".github/workflows/molecule-dispatch.yml").read_text())
        self.assertEqual(manual["jobs"]["molecule"]["uses"], CENTRAL_MOLECULE_REF)
        self.assertIs(manual["jobs"]["molecule"]["with"]["full_suite"], True)
        upstream = yaml.safe_load((ROOT / ".github/workflows/upstream-revalidate.yml").read_text())
        self.assertEqual(upstream["jobs"]["revalidate"]["uses"], CENTRAL_MOLECULE_REF)
        self.assertIs(upstream["jobs"]["revalidate"]["with"]["full_suite"], True)

    def test_workflow_changes_have_a_caller_contract(self):
        jobs = GATE["jobs"]
        ci_inputs = jobs["ci"]["with"]
        changes_inputs = jobs["changes"]["with"]
        self.assertIn("_ansible-ci.yml", jobs["ci"]["uses"])
        self.assertIn("_ansible-changes.yml", jobs["changes"]["uses"])
        for filter_name in ("molecule_contract_filters", "molecule_scenario_filters"):
            self.assertEqual(ci_inputs[filter_name], changes_inputs[filter_name])

        jobs_node = mapping_value(mapping_value(GATE_NODE, "jobs"), "ci")
        ci_with_node = mapping_value(jobs_node, "with")
        changes_node = mapping_value(mapping_value(GATE_NODE, "jobs"), "changes")
        changes_with_node = mapping_value(changes_node, "with")
        for filter_name in ("molecule_contract_filters", "molecule_scenario_filters"):
            self.assertIs(
                mapping_value(ci_with_node, filter_name),
                mapping_value(changes_with_node, filter_name),
            )

        for pattern in (
            "roles/bmc_console_user/**",
            "tests/test_bmc_console_user_contract.py",
            ".github/workflows/ci-gate.yml",
            ".github/workflows/molecule.yml",
            ".github/workflows/_static-contracts.yml",
            ".github/workflows/molecule-dispatch.yml",
            ".github/workflows/upstream-revalidate.yml",
            ".github/workflows/_role-contracts.yml",
            "tests/workflow_policy/**",
        ):
            self.assertIn(pattern, CONTRACT_FILTERS)

    def test_guest_recovery_and_shared_test_paths_have_contract_checks(self):
        covered_paths = [
            "playbooks/guest-recovery.yml",
            "tests/guest_recovery/hosts.yml",
            "tests/test_guest_recovery_contract.py",
            "tests/test_zfs_nfs_export_permissions.py",
            "tests/pve_bulk_data_compare/__init__.py",
            "tests/pve_notifications/__init__.py",
            "tests/zfs_capacity_monitor/__init__.py",
            "tests/zfs_fault_alert/__init__.py",
            "roles/pve_syslog_forwarder/templates/10-forward-cribl.conf.j2",
            "tests/pve_syslog_forwarder/verify_task_logs.yml",
        ]

        for changed_path in covered_paths:
            self.assertTrue(
                any(
                    fnmatch.fnmatchcase(changed_path, pattern)
                    for pattern in CONTRACT_FILTERS
                ),
                f"contract-tested path is not mapped: {changed_path}",
            )

        self.assertFalse(
            any(
                fnmatch.fnmatchcase("tests/unclassified/test_new.py", pattern)
                for pattern in CONTRACT_FILTERS
                + SCENARIO_PATTERNS
            ),
            "unmapped test paths must keep the shared full-matrix fallback",
        )

    def test_paths_from_promotion_failure_are_covered_by_scenarios_or_contracts(self):
        for changed_path in PROMOTION_PATHS["unmapped_paths"]:
            patterns = CONTRACT_FILTERS + SCENARIO_PATTERNS
            covered = any(
                fnmatch.fnmatchcase(changed_path, pattern) for pattern in patterns
            )
            self.assertTrue(
                covered, f"promotion path has no focused CI mapping: {changed_path}"
            )

        self.assertTrue(
            any(
                fnmatch.fnmatchcase("roles/lxc_features/tasks/main.yml", pattern)
                for pattern in SCENARIO_FILTERS["lxc_features"]
            )
        )

    def test_redacted_host_path_keeps_shared_full_matrix_classification(self):
        path = PROMOTION_PATHS["redacted_full_matrix_path"].replace(
            "<redacted>", "fixture-node"
        )
        self.assertTrue(fnmatch.fnmatchcase(path, "inventory/host_vars/**"))


if __name__ == "__main__":
    unittest.main()
