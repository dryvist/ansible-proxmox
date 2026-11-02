"""The live hatchet-killtest probe only reads, over verified https, and proves the grant."""

import unittest

import yaml

from test_pve_api_tokens import ROOT, evaluate

PROBE = yaml.safe_load((ROOT / "tests/access_verification/hatchet_token_probe.yml").read_text())[0]
HATCHET = ["/vms/900001", "/vms/900002"]


def _task(prefix):
    return next(t for t in PROBE["tasks"] if t["name"].startswith(prefix))


class ProbeInputs(unittest.TestCase):
    def _accepts(self, url="https://pve.example.test:8006", hatchet="900001,900002", other="900003"):
        inputs = {"pve_probe_url": url, "pve_probe_token_id": "t",
                  "pve_probe_token_secret": "s", "pve_probe_node": "pve-a",
                  "pve_probe_hatchet_vmids": [v.strip() for v in hatchet.split(",")],
                  "pve_probe_other_type": "lxc", "pve_probe_other_vmid": other}
        gate = _task("Require explicit PVE probe inputs")["ansible.builtin.assert"]["that"]
        return all(evaluate("{{ " + condition + " }}", **inputs) for condition in gate)

    def test_vmids_must_be_numeric_distinct_and_cover_both_hatchet_guests(self):
        self.assertTrue(self._accepts())
        for label, kwargs in [
            ("one hatchet guest", {"hatchet": "900001"}),
            ("duplicate hatchet guest", {"hatchet": "900001,900001"}),
            ("non-numeric", {"other": "9999/../x"}),
            ("other is a hatchet guest", {"other": "900002"}),
        ]:
            with self.subTest(label):
                self.assertFalse(self._accepts(**kwargs))

    def test_only_an_https_url_is_accepted(self):
        for url in ("http://pve.example.test:8006", "pve.example.test", "https://", ""):
            with self.subTest(url=url):
                self.assertFalse(self._accepts(url=url))

    def test_every_request_is_a_verified_get(self):
        requests = [t["ansible.builtin.uri"] for t in PROBE["tasks"] if "ansible.builtin.uri" in t]
        self.assertEqual(len(requests), 3)
        for request in requests:
            self.assertEqual(request["method"], "GET")
            self.assertIs(request["validate_certs"], True)
        self.assertNotIn("nextid", yaml.safe_dump(PROBE))
        self.assertNotIn("method", "".join(map(str, PROBE["vars"]["pve_probe_denied"])))


class ProbePermissions(unittest.TestCase):
    def _holds(self, tree, vms=None, other=None):
        gate = _task("Require VM.PowerMgmt on exactly")["ansible.builtin.assert"]["that"]
        variables = {
            "pve_probe_tree": tree, "pve_probe_vms": vms or {}, "pve_probe_other": other or {},
            "pve_probe_hatchet_paths": HATCHET, "pve_probe_other_vmid": "900003",
        }
        return all(evaluate("{{ " + condition + " }}", **variables) for condition in gate)

    def test_power_on_exactly_the_two_guests_passes(self):
        tree = {"/": {}, **{path: {"VM.PowerMgmt": 0} for path in HATCHET}}
        self.assertTrue(self._holds(tree, {"/vms": {}}, {"/vms/900003": {}}))

    def test_any_wider_grant_fails(self):
        power = {"VM.PowerMgmt": 0}
        exact = {path: power for path in HATCHET}
        for label, kwargs in [
            ("one guest only", {"tree": {HATCHET[0]: power}}),
            ("extra guest", {"tree": {**exact, "/vms/900003": power}}),
            ("extra privilege", {"tree": {**exact, HATCHET[0]: {**power, "VM.Audit": 0}}}),
            ("other privilege elsewhere", {"tree": {**exact, "/": {"Sys.Audit": 1}}}),
            ("other privilege on a pool", {"tree": {**exact, "/pool/x": {"Datastore.Audit": 0}}}),
            ("power on /vms", {"tree": exact, "vms": {"/vms": power}}),
            ("power on the other guest", {"tree": exact, "other": {"/vms/900003": power}}),
        ]:
            with self.subTest(label):
                self.assertFalse(self._holds(**kwargs))


if __name__ == "__main__":
    unittest.main()
