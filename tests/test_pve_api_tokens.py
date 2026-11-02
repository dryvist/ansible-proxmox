"""Exercise pve_api_tokens' mint decision and read gate without a cluster."""

import json
from pathlib import Path
import unittest

from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar, trust_as_template
import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS = [t for f in ("token.yml", "custom_role.yml")
         for t in yaml.safe_load((ROOT / "roles/pve_api_tokens/tasks" / f).read_text())]
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
        DEFAULTS["pve_api_tokens_hatchet_guests"],
        containers_from_tofu=containers,
        pve_api_tokens_hatchet_tag=DEFAULTS["pve_api_tokens_hatchet_tag"],
    )
    paths = evaluate(
        DEFAULTS["pve_api_tokens_hatchet_acl_paths"],
        pve_api_tokens_hatchet_guests=guests,
    )
    return guests, paths


def mint(bucket, existing, privsep=False, existing_privsep=0, fact="pve_api_tokens_mint"):
    decide = task("Decide whether")
    variables = {
        "pve_api_tokens_stored": {"secret": bucket} if bucket is not None else {"msg": "Invalid or missing path"},
        "pve_api_tokens_tokens": {"rc": 0, "stdout": json.dumps(
            [{"tokenid": t, "privsep": existing_privsep} for t in existing])},
        "pve_api_tokens_privsep": privsep,
        "pve_api_tokens_token_name": "ro",
        "pve_api_tokens_id": TOKEN_ID,
        "pve_api_tokens_id_field": "homarr_proxmox_token_id",
        "pve_api_tokens_secret_field": "homarr_proxmox_token_secret",
    }
    for name, expression in decide["vars"].items():
        variables[name] = evaluate(expression, **variables)
    return evaluate(decide["ansible.builtin.set_fact"][fact], **variables)


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

    def test_a_published_token_with_the_wrong_privsep_is_modified_in_place(self):
        published = {"homarr_proxmox_token_id": TOKEN_ID, "homarr_proxmox_token_secret": "s"}
        for privsep, existing, drift in [(True, 0, True), (False, 1, True), (True, 1, False), (False, 0, False)]:
            with self.subTest(privsep=privsep, existing=existing):
                self.assertFalse(mint(published, ["ro"], privsep=privsep, existing_privsep=existing))
                self.assertEqual(mint(published, ["ro"], privsep, existing, "pve_api_tokens_privsep_drift"), drift)
        align = task("Align privilege separation")
        self.assertEqual(align["ansible.builtin.command"]["argv"][:4], ["pveum", "user", "token", "modify"])
        self.assertIn("not pve_api_tokens_mint | bool", align["when"])


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

    def test_existing_consumers_root_grant_condition_is_unchanged(self):
        root_grant = task("Grant the default role at the root")
        for app in ("homarr", "pve-exporter", "nautobot"):
            consumer = next(e for e in DEFAULTS["pve_api_tokens_consumers"] if e["app"] == app)
            variables = identity_variables(consumer)
            variables["pve_api_tokens_role_name"] = "PVEAuditor"
            user = variables["pve_api_tokens_user"]
            granted = {"path": "/", "type": "user", "ugid": user, "roleid": "PVEAuditor"}
            for label, acls, expected in (
                ("no ACL yet", [], True),
                ("root auditor already granted", [granted], False),
                ("only another user's root ACL", [{**granted, "ugid": "other@pve"}], True),
                ("own ACL on a narrower path", [{**granted, "path": "/vms/900001"}], True),
            ):
                with self.subTest(app=app, case=label):
                    condition = root_grant["when"]
                    rendered = evaluate("{{ " + condition + " }}",
                                        **{**variables, "pve_api_tokens_acls": {"stdout": json.dumps(acls)}})
                    self.assertEqual(rendered, expected)


if __name__ == "__main__":
    unittest.main()
