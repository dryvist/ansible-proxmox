"""Exercise the role's real gates and resume conditions without a cluster."""

from pathlib import Path
import unittest

from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar, trust_as_template
import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS = yaml.safe_load((ROOT / "roles/pve_proxman_operator/tasks/main.yml").read_text())


def task(name):
    return next(t for t in TASKS if t["name"] == name)


def evaluate(expression, **variables):
    templar = Templar(loader=DataLoader(), variables=variables)
    return templar.template(trust_as_template("{{ " + expression + " }}"))


class OperatorProvisioning(unittest.TestCase):
    def test_capabilities_gate_accepts_both_native_response_shapes(self):
        block = task("Preflight and retain the credential on the controller")["block"]
        gate = next(t for t in block if t["name"] == "Require the complete exact-path publication grant")
        expression = gate["ansible.builtin.assert"]["that"][0]
        path = "secret/data/proxmox/main/proxman"
        for capabilities, allowed in [(["read", "create", "update"], True), (["read"], False), (["deny"], False)]:
            for body in [{path: capabilities}, {"data": {path: capabilities}}]:
                with self.subTest(body=body):
                    self.assertEqual(evaluate(expression, pve_proxman_operator_capabilities={"data": body}, pve_proxman_operator_mount="secret", pve_proxman_operator_path="proxmox/main/proxman"), allowed)

    def test_private_node_variable_controls_selection_and_gate(self):
        play = yaml.safe_load((ROOT / "playbooks/proxman.yml").read_text())[1]
        templar = Templar(loader=DataLoader(), variables={"pve_proxman_operator_provision_node": "example-node"})
        self.assertEqual(templar.template(trust_as_template(play["hosts"])), "example-node")
        assertions = task("Validate private provisioning inputs and single cluster writer")["ansible.builtin.assert"]["that"]
        variables = {"pve_proxman_operator_provision_node": "example-node", "inventory_hostname": "example-node", "ansible_play_hosts_all": ["example-node"]}
        for condition in assertions[:3]:
            self.assertTrue(evaluate(condition, **variables))
        self.assertFalse(evaluate(assertions[1], **{**variables, "pve_proxman_operator_provision_node": ""}))
        self.assertFalse(evaluate(assertions[2], **{**variables, "inventory_hostname": "another-node"}))

    def test_denied_and_server_failures_cannot_generate(self):
        block = task("Preflight and retain the credential on the controller")["block"]
        gate = next(t for t in block if t["name"] == "Reject denied or unavailable reads")
        expression = gate["ansible.builtin.assert"]["that"][0]
        for message, allowed in [
            ("Invalid or missing path ['new'] with secret version 'latest'.", True),
            ("Forbidden: Permission Denied", False),
            ("Internal Server Error", False),
        ]:
            with self.subTest(message=message):
                self.assertEqual(evaluate(expression, pve_proxman_operator_existing={"msg": message}), allowed)
        self.assertTrue(evaluate(expression, pve_proxman_operator_existing={"secret": {}}))

    def test_enabled_identity_never_resets_password(self):
        expressions = task("Initialize the disabled operator password without command-line exposure")["when"]
        condition = expressions[1]
        for users, expected in [([], True), ([{"enable": 0}], True), ([{"enable": 1}], False)]:
            self.assertEqual(evaluate(condition, pve_proxman_operator_user=users), expected)

    def test_existing_unknown_credential_cannot_be_replaced(self):
        expression = task("Refuse to replace an existing identity whose credential is unknown")["ansible.builtin.assert"]["that"][0]
        self.assertFalse(evaluate(expression, pve_proxman_operator_user=[{"enable": 1}], pve_proxman_operator_existing={}))
        self.assertTrue(evaluate(expression, pve_proxman_operator_user=[], pve_proxman_operator_existing={}))

    def test_publication_is_create_only_and_precedes_cluster_mutations(self):
        publication = task("Publish a new credential before cluster mutation using create-only CAS")
        self.assertEqual(publication["community.hashi_vault.vault_kv2_write"]["cas"], 0)
        self.assertIn("'/dev/null'", publication["community.hashi_vault.vault_kv2_write"]["data"]["password"])
        self.assertLess(TASKS.index(publication), TASKS.index(task("Create the dedicated group")))
        self.assertLess(TASKS.index(task("Initialize the disabled operator password without command-line exposure")), TASKS.index(task("Enable the initialized operator")))
        self.assertTrue(task("Initialize the disabled operator password without command-line exposure")["no_log"])
        self.assertNotIn("password", " ".join(task("Initialize the disabled operator password without command-line exposure")["ansible.builtin.command"]["argv"]))

    def test_only_declared_privileges_are_present(self):
        defaults = yaml.safe_load((ROOT / "roles/pve_proxman_operator/defaults/main.yml").read_text())
        roles = defaults["pve_proxman_operator_roles"]
        self.assertEqual({r["path"] for r in roles}, {"/", "/vms"})
        self.assertEqual({p for r in roles for p in r["privileges"]}, {"Sys.Audit", "Datastore.Audit", "Pool.Audit", "VM.Audit", "VM.PowerMgmt", "VM.Console"})

    def test_role_and_acl_convergence_are_idempotent(self):
        roles = yaml.safe_load((ROOT / "roles/pve_proxman_operator/tasks/role.yml").read_text())
        role = {"name": "ExampleGuest", "path": "/vms", "privileges": ["VM.Console", "VM.Audit"]}
        condition = next(t for t in roles if t["name"] == "Reconcile only the declared privileges")["when"]
        self.assertFalse(evaluate(condition, pve_proxman_operator_role=role, pve_proxman_operator_existing_role=[{"privs": "VM.Audit,VM.Console"}]))
        self.assertTrue(evaluate(condition, pve_proxman_operator_role=role, pve_proxman_operator_existing_role=[{"privs": "VM.Audit,Sys.Console"}]))
        acl_condition = next(t for t in roles if t["name"] == "Grant the role at its bounded path")["when"]
        existing = '[{"type":"group","ugid":"example","path":"/vms","roleid":"ExampleGuest","propagate":1}]'
        self.assertFalse(evaluate(acl_condition, pve_proxman_operator_role=role, pve_proxman_operator_group="example", pve_proxman_operator_acls={"stdout": existing}))
        self.assertTrue(evaluate(acl_condition, pve_proxman_operator_role=role, pve_proxman_operator_group="example", pve_proxman_operator_acls={"stdout": "[]"}))


if __name__ == "__main__":
    unittest.main()
