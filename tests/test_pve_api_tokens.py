"""Exercise pve_api_tokens' mint decision and read gate without a cluster."""

import json
from pathlib import Path
import unittest

from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar, trust_as_template
import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS = yaml.safe_load((ROOT / "roles/pve_api_tokens/tasks/token.yml").read_text())
TOKEN_ID = "homarr@pve!ro"


def task(name):
    return next(t for t in TASKS if t["name"].startswith(name))


def evaluate(expression, **variables):
    templar = Templar(loader=DataLoader(), variables=variables)
    return templar.template(trust_as_template(expression))


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


if __name__ == "__main__":
    unittest.main()
