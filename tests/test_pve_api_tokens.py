"""Exercise pve_api_tokens' mint decision and read gate without a cluster."""

import json
from pathlib import Path
import unittest

from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar, trust_as_template
import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS = yaml.safe_load((ROOT / "roles/pve_api_tokens/tasks/token.yml").read_text())
MAIN_TASKS = yaml.safe_load((ROOT / "roles/pve_api_tokens/tasks/main.yml").read_text())
DEFAULTS = yaml.safe_load((ROOT / "roles/pve_api_tokens/defaults/main.yml").read_text())
TOKEN_ID = "homarr@pve!ro"


def _walk(tasks):
    for item in tasks:
        yield item
        yield from _walk(item.get("block", []))


def task(name):
    return next(t for t in _walk(TASKS) if t.get("name", "").startswith(name))


def evaluate(expression, **variables):
    templar = Templar(loader=DataLoader(), variables=variables)
    return templar.template(trust_as_template(expression))


def render(value, variables):
    if isinstance(value, str):
        return evaluate(value, **variables)
    if isinstance(value, list):
        return [render(item, variables) for item in value]
    if isinstance(value, dict):
        return {key: render(item, variables) for key, item in value.items()}
    return value


def identity_variables(consumer, **extra):
    variables = {
        "pve_api_tokens_consumer": consumer,
        "pve_api_tokens_role": "PVEAuditor",
        "pve_api_tokens_realm": "pve",
        "pve_api_tokens_token_name": "ro",
        **extra,
    }
    for name, expression in task("Name the identity")["ansible.builtin.set_fact"].items():
        variables[name] = render(expression, variables)
    return variables


def evaluate_conditions(task_data, variables):
    return all(
        evaluate("{{ " + condition + " }}", **variables)
        for condition in task_data["when"]
    )


def hatchet_paths(containers):
    guests = evaluate(
        DEFAULTS["pve_api_tokens_hatchet_docker_ai_guests"],
        containers_from_tofu=containers,
    )
    paths = evaluate(
        DEFAULTS["pve_api_tokens_hatchet_acl_paths"],
        pve_api_tokens_hatchet_docker_ai_guests=guests,
    )
    return guests, paths


def mint(bucket, existing):
    decide = task("Decide whether")
    variables = {
        "pve_api_tokens_stored": {"secret": bucket} if bucket is not None else {"msg": "Invalid or missing path"},
        "pve_api_tokens_tokens": {"rc": 0, "stdout": json.dumps([{"tokenid": t} for t in existing])},
        "pve_api_tokens_token_name": "ro",
        "pve_api_tokens_id": TOKEN_ID,
        "pve_api_tokens_id_field": "homarr_proxmox_token_id",
        "pve_api_tokens_secret_field": "homarr_proxmox_token_secret",
    }
    for name, expression in decide["vars"].items():
        variables[name] = evaluate(expression, **variables)
    return evaluate(decide["ansible.builtin.set_fact"]["pve_api_tokens_mint"], **variables)


class MintDecision(unittest.TestCase):
    def test_published_and_present_is_left_alone(self):
        bucket = {"homarr_proxmox_token_id": TOKEN_ID, "homarr_proxmox_token_secret": "s"}
        self.assertFalse(mint(bucket, ["ro"]))

    def test_every_gap_mints(self):
        published = {"homarr_proxmox_token_id": TOKEN_ID, "homarr_proxmox_token_secret": "s"}
        for label, bucket, existing in [
            ("missing path", None, []),
            ("bucket without the fields", {"homarr_admin_password": "x"}, ["ro"]),
            ("empty secret", {**published, "homarr_proxmox_token_secret": ""}, ["ro"]),
            ("different token id", {**published, "homarr_proxmox_token_id": "other@pam!x"}, ["ro"]),
            ("token removed from the cluster", published, []),
        ]:
            with self.subTest(label):
                self.assertTrue(mint(bucket, existing))


class ReadGate(unittest.TestCase):
    def test_only_a_missing_path_permits_writing(self):
        expression = "{{ " + task("Reject a denied")["ansible.builtin.assert"]["that"][0] + " }}"
        for message, allowed in [
            ("Invalid or missing path ['apps/homarr'] with secret version 'latest'.", True),
            ("Forbidden: Permission Denied", False),
            ("Internal Server Error", False),
        ]:
            with self.subTest(message=message):
                self.assertEqual(evaluate(expression, pve_api_tokens_stored={"msg": message}), allowed)
        self.assertTrue(evaluate(expression, pve_api_tokens_stored={"secret": {}}))


class CertificateDistribution(unittest.TestCase):
    def test_homarr_requests_the_public_cluster_ca(self):
        homarr = next(item for item in DEFAULTS["pve_api_tokens_consumers"] if item["app"] == "homarr")
        self.assertEqual("homarr_proxmox_ca", homarr["certificate_field"])

        read = next(
            item
            for item in MAIN_TASKS[0]["block"]
            if item["name"].startswith("Read the cluster CA")
        )
        self.assertEqual("/etc/pve/pve-root-ca.pem", read["ansible.builtin.slurp"]["src"])
        self.assertTrue(read["no_log"])

    def test_ca_publish_merges_the_bucket_with_cas_and_is_censored(self):
        read = next(item for item in TASKS if item["name"].startswith("Read the latest credential"))
        publish = next(item for item in TASKS if item["name"].startswith("Publish the cluster CA"))

        self.assertTrue(read["no_log"])
        self.assertTrue(publish["no_log"])
        self.assertIn("metadata.version", publish["community.hashi_vault.vault_kv2_write"]["cas"])
        self.assertIn("pve_api_tokens_certificate_stored.secret", publish["community.hashi_vault.vault_kv2_write"]["data"])
        self.assertIn("pve_api_tokens_cluster_ca.content | b64decode", publish["community.hashi_vault.vault_kv2_write"]["data"])


class ConsumerCompatibility(unittest.TestCase):
    def test_existing_consumers_keep_root_auditor_and_privsep_zero_argv(self):
        root_grant = task("Grant the default role at the root")
        token_create = task("Create the token for")
        expected_apps = {
            "homarr": "homarr@pve",
            "pve-exporter": "pve-exporter@pve",
            "nautobot": "nautobot@pve",
        }

        for app, user in expected_apps.items():
            with self.subTest(app=app):
                consumer = next(
                    entry for entry in DEFAULTS["pve_api_tokens_consumers"]
                    if entry["app"] == app
                )
                variables = identity_variables(consumer)
                variables.update(
                    pve_api_tokens_role_name="PVEAuditor",
                    pve_api_tokens_user=user,
                )
                self.assertEqual(
                    render(root_grant["ansible.builtin.command"]["argv"], variables),
                    ["pveum", "acl", "modify", "/", "--users", user,
                     "--roles", "PVEAuditor"],
                )
                self.assertEqual(
                    render(token_create["ansible.builtin.command"]["argv"], variables),
                    ["pveum", "user", "token", "add", user, "ro", "--privsep", "0",
                     "--comment", f"Published to OpenBao apps/{app}",
                     "--output-format", "json"],
                )


class HatchetPowerScope(unittest.TestCase):
    def setUp(self):
        self.consumer = next(
            entry for entry in DEFAULTS["pve_api_tokens_consumers"]
            if entry["app"] == "hatchet-killtest"
        )
        self.containers = {
            "hatchet-a": {"tags": ["docker-ai"], "ansible_pct_vmid": 900001},
            "hatchet-b": {"tags": ["docker-ai"], "ansible_pct_vmid": 900002},
            "unrelated": {"tags": ["other"], "ansible_pct_vmid": 900003},
        }
        self.guests, self.paths = hatchet_paths(self.containers)
        self.variables = identity_variables(self.consumer)
        self.variables["pve_api_tokens_acl_paths"] = self.paths

    def test_token_role_and_acl_argv_are_power_only_and_guest_scoped(self):
        self.assertEqual(self.consumer["privileges"], ["VM.PowerMgmt", "VM.Audit"])
        self.assertTrue(self.consumer["privsep"])
        self.assertEqual(self.paths, ["/vms/900001", "/vms/900002"])
        for forbidden in ("/", "/nodes", "/pool", "/storage"):
            self.assertNotIn(forbidden, self.paths)

        role_task = task("Reconcile the exact privileges")
        self.variables["pve_api_tokens_existing_role"] = []
        self.assertEqual(
            render(role_task["ansible.builtin.command"]["argv"], self.variables),
            ["pveum", "role", "add", "HatchetKillTestPower", "--privs",
             "VM.PowerMgmt VM.Audit"],
        )
        self.variables["pve_api_tokens_existing_role"] = [
            {"privs": "VM.Audit,VM.PowerMgmt"}
        ]
        self.assertFalse(evaluate_conditions(role_task, self.variables))
        self.variables["pve_api_tokens_existing_role"] = [
            {"privs": "VM.Audit,VM.PowerMgmt,VM.Console"}
        ]
        self.assertTrue(evaluate_conditions(role_task, self.variables))
        self.assertEqual(
            render(role_task["ansible.builtin.command"]["argv"], self.variables)[2],
            "modify",
        )

        user_grant = task("Grant the custom role on each declared path")
        token_grant = task("Grant the custom role to a privsep token")
        for path in self.paths:
            with self.subTest(path=path):
                variables = {**self.variables, "item": path}
                self.assertEqual(
                    render(user_grant["ansible.builtin.command"]["argv"], variables),
                    ["pveum", "acl", "modify", path, "--users", "hatchet-killtest@pve",
                     "--roles", "HatchetKillTestPower", "--propagate", "0"],
                )
                self.assertEqual(
                    render(token_grant["ansible.builtin.command"]["argv"], variables),
                    ["pveum", "acl", "modify", path, "--tokens",
                     "hatchet-killtest@pve!ro", "--roles", "HatchetKillTestPower",
                     "--propagate", "0"],
                )
        token_argv = render(task("Create the token for")["ansible.builtin.command"]["argv"], self.variables)
        self.assertEqual(token_argv[6:8], ["--privsep", "1"])

    def test_stale_token_path_is_deleted_and_allowed_paths_are_kept(self):
        stale = {
            "path": "/vms/900099", "type": "token",
            "ugid": "hatchet-killtest@pve!ro", "roleid": "HatchetKillTestPower",
            "propagate": 0,
        }
        allowed = {
            "path": self.paths[0], "type": "token",
            "ugid": "hatchet-killtest@pve!ro", "roleid": "HatchetKillTestPower",
            "propagate": 0,
        }
        self.variables["pve_api_tokens_acls"] = {
            "stdout": json.dumps([stale, allowed])
        }
        cleanup = task("Remove stale token ACLs")
        candidates = evaluate(cleanup["loop"], **self.variables)
        stale_matches = [
            entry for entry in candidates
            if evaluate_conditions(cleanup, {**self.variables, "item": entry})
        ]

        self.assertIn(stale, stale_matches)
        self.assertNotIn(allowed, stale_matches)
        self.assertEqual(
            render(cleanup["ansible.builtin.command"]["argv"],
                   {**self.variables, "item": stale}),
            ["pveum", "acl", "delete", "/vms/900099", "--tokens",
             "hatchet-killtest@pve!ro", "--roles", "HatchetKillTestPower"],
        )

    def _validates(self, paths):
        assertion = task("Validate the role and ACL paths")
        variables = {**self.variables, "pve_api_tokens_acl_paths": paths}
        return all(
            evaluate("{{ " + condition + " }}", **variables)
            for condition in assertion["ansible.builtin.assert"]["that"]
        )

    def test_guest_paths_validate_and_empty_or_wider_paths_fail(self):
        self.assertTrue(self._validates(self.paths))
        guests, paths = hatchet_paths({})
        self.assertEqual(guests, [])
        self.assertFalse(self._validates(paths))
        for wider in (["/"], ["/vms"], ["/pool/hatchet"], ["/vms/900001", "/nodes/pve-a"]):
            with self.subTest(paths=wider):
                self.assertFalse(self._validates(wider))

    def test_a_reminted_token_is_granted_even_when_the_old_token_held_the_acl(self):
        grant = task("Grant the custom role to a privsep token")
        held = [{"path": path, "type": "token", "ugid": "hatchet-killtest@pve!ro",
                 "roleid": "HatchetKillTestPower", "propagate": 0} for path in self.paths]
        variables = {**self.variables, "item": self.paths[0],
                     "pve_api_tokens_acls": {"stdout": json.dumps(held)}}

        self.assertFalse(evaluate_conditions(grant, {**variables, "pve_api_tokens_mint": False}))
        self.assertTrue(evaluate_conditions(grant, {**variables, "pve_api_tokens_mint": True}))


if __name__ == "__main__":
    unittest.main()
