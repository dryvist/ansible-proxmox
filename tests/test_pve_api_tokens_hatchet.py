"""The hatchet-killtest power token stays guest-scoped and power-only."""

import json
import unittest

import yaml

from test_pve_api_tokens import (
    DEFAULTS, ROOT, evaluate, evaluate_conditions, hatchet_paths, identity_variables, render, task,
)

PROBE = yaml.safe_load((ROOT / "tests/access_verification/hatchet_token_probe.yml").read_text())[0]


class HatchetPowerScope(unittest.TestCase):
    def setUp(self):
        self.consumer = next(
            entry for entry in DEFAULTS["pve_api_tokens_consumers"]
            if entry["app"] == "hatchet-killtest"
        )
        self.containers = {
            "guest-a": {"tags": ["docker-ai", "hatchet-killtest"], "ansible_pct_vmid": 900001},
            "guest-b": {"tags": ["hatchet-killtest"], "ansible_pct_vmid": 900002},
            "docker-ai-only": {"tags": ["docker-ai"], "ansible_pct_vmid": 900004},
            "unrelated": {"tags": ["other"], "ansible_pct_vmid": 900003},
        }
        self.guests, self.paths = hatchet_paths(self.containers)
        self.variables = identity_variables(self.consumer)
        self.variables["pve_api_tokens_acl_paths"] = self.paths

    def test_token_role_and_acl_argv_are_power_only_and_guest_scoped(self):
        self.assertEqual(self.consumer["privileges"], ["VM.PowerMgmt"])
        self.assertTrue(self.consumer["privsep"])
        self.assertEqual(self.paths, ["/vms/900001", "/vms/900002"])
        for forbidden in ("/", "/nodes", "/pool", "/storage"):
            self.assertNotIn(forbidden, self.paths)

        role_task = task("Reconcile the exact privileges")
        self.variables["pve_api_tokens_existing_role"] = []
        self.assertEqual(
            render(role_task["ansible.builtin.command"]["argv"], self.variables),
            ["pveum", "role", "add", "HatchetKillTestPower", "--privs",
             "VM.PowerMgmt"],
        )
        self.variables["pve_api_tokens_existing_role"] = [
            {"privs": "VM.PowerMgmt"}
        ]
        self.assertFalse(evaluate_conditions(role_task, self.variables))
        self.variables["pve_api_tokens_existing_role"] = [
            {"privs": "VM.PowerMgmt,VM.Audit"}
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

    def test_only_the_dedicated_tag_selects_guests_and_the_count_is_exact(self):
        self.assertNotIn("/vms/900004", self.paths)
        self.assertEqual(self.consumer["acl_path_count"], 2)
        for wrong_count in (["/vms/900001"], [*self.paths, "/vms/900005"]):
            with self.subTest(paths=wrong_count):
                self.assertFalse(self._validates(wrong_count))

    def test_a_tagged_guest_without_a_vmid_drops_out_so_the_count_check_fires(self):
        _, paths = hatchet_paths({**self.containers, "no-vmid": {"tags": ["hatchet-killtest"]}})
        self.assertEqual(paths, self.paths)
        _, paths = hatchet_paths({"guest-a": self.containers["guest-a"],
                                       "no-vmid": {"tags": ["hatchet-killtest"]}})
        self.assertFalse(self._validates(paths))

    def test_only_the_killtest_token_publishes_outside_apps(self):
        for consumer in DEFAULTS["pve_api_tokens_consumers"]:
            expected = "killtest/hatchet" if consumer["app"] == "hatchet-killtest" else f"apps/{consumer['app']}"
            with self.subTest(app=consumer["app"]):
                self.assertEqual(identity_variables(consumer)["pve_api_tokens_kv_path"], expected)

    def test_failure_names_the_tag_source_and_no_guest(self):
        assertion = task("Validate the role and ACL paths")
        # Ansible renders the loop item's nested acl_source template lazily; do it up front here.
        consumer = {**self.consumer, "acl_source": evaluate(
            self.consumer["acl_source"], pve_api_tokens_hatchet_tag=DEFAULTS["pve_api_tokens_hatchet_tag"])}
        message = render(assertion["ansible.builtin.assert"]["fail_msg"],
                         {**self.variables, "pve_api_tokens_consumer": consumer,
                          "pve_api_tokens_acl_paths": []})
        self.assertIn("tofu containers tagged hatchet-killtest", message)
        self.assertIn("found 0", message)
        for guest in self.containers:
            self.assertNotIn(guest, message)

    def test_a_shared_role_or_a_grouped_user_is_refused(self):
        guard = task("Refuse a shared custom role or a grouped user")
        own = {"path": "/vms/900001", "type": "token", "ugid": "hatchet-killtest@pve!ro",
               "roleid": "HatchetKillTestPower"}
        user = {"userid": "hatchet-killtest@pve", "groups": ""}

        def passes(acls, users):
            variables = {**self.variables,
                         "pve_api_tokens_acls": {"stdout": json.dumps(acls)},
                         "pve_api_tokens_users": {"stdout": json.dumps(users)}}
            return all(evaluate("{{ " + c + " }}", **variables) for c in guard["ansible.builtin.assert"]["that"])

        self.assertTrue(passes([own], [user]))
        self.assertFalse(passes([own, {**own, "path": "/", "type": "group", "ugid": "ops"}], [user]))
        self.assertFalse(passes([own], [{**user, "groups": "ops"}]))
        self.assertFalse(passes([own], [{**user, "groups": ["ops"]}]))

    def test_the_power_entry_runs_after_every_read_only_consumer(self):
        self.assertEqual(DEFAULTS["pve_api_tokens_consumers"][-1]["app"], "hatchet-killtest")

    def test_a_reminted_token_is_granted_even_when_the_old_token_held_the_acl(self):
        grant = task("Grant the custom role to a privsep token")
        held = [{"path": path, "type": "token", "ugid": "hatchet-killtest@pve!ro",
                 "roleid": "HatchetKillTestPower", "propagate": 0} for path in self.paths]
        variables = {**self.variables, "item": self.paths[0],
                     "pve_api_tokens_acls": {"stdout": json.dumps(held)}}

        self.assertFalse(evaluate_conditions(grant, {**variables, "pve_api_tokens_mint": False}))
        self.assertTrue(evaluate_conditions(grant, {**variables, "pve_api_tokens_mint": True}))



class ProbeInputs(unittest.TestCase):
    def _accepts(self, hatchet="900001,900002", other="900003", unused="999990"):
        inputs = {"pve_probe_url": "https://pve.example.test", "pve_probe_token_id": "t",
                  "pve_probe_token_secret": "s", "pve_probe_node": "pve-a",
                  "pve_probe_hatchet_vmids": [v.strip() for v in hatchet.split(",")],
                  "pve_probe_other_type": "lxc", "pve_probe_other_vmid": other,
                  "pve_probe_unused_vmid": unused}
        gate = PROBE["tasks"][0]["ansible.builtin.assert"]["that"]
        return all(evaluate("{{ " + condition + " }}", **inputs) for condition in gate)

    def test_vmids_must_be_numeric_distinct_and_cover_both_hatchet_guests(self):
        self.assertTrue(self._accepts())
        for label, kwargs in [
            ("one hatchet guest", {"hatchet": "900001"}),
            ("duplicate hatchet guest", {"hatchet": "900001,900001"}),
            ("non-numeric", {"unused": "9999/../x"}),
            ("unused is the second hatchet guest", {"unused": "900002"}),
            ("unused is the other guest", {"unused": "900003"}),
            ("other is a hatchet guest", {"other": "900002"}),
        ]:
            with self.subTest(label):
                self.assertFalse(self._accepts(**kwargs))

    def test_unused_vmid_is_proven_free_before_any_denied_request(self):
        names = [t["name"] for t in PROBE["tasks"]]
        check = names.index("Require UNUSED_VMID to be free across the cluster")
        self.assertLess(check, names.index("Require each out-of-scope request to be denied"))
        self.assertIn("cluster/nextid?vmid=", PROBE["tasks"][check]["ansible.builtin.uri"]["url"])


if __name__ == "__main__":
    unittest.main()
