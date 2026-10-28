#!/usr/bin/env python3
"""Pin the Proxmox host connection contract: an unset env var never means localhost."""

from pathlib import Path
import re
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_DIR = ROOT / "inventory"
HOSTS_FILE = INVENTORY_DIR / "hosts.yml"
HARDWARE_FACTS_PLAYBOOK = ROOT / "playbooks/hardware-facts.yml"
ANSIBLE_HOST = re.compile(
    r"^\{\{ lookup\('env', '(PVE\d_VE_HOSTNAME)'\) \| default\(proxmox_node_name, true\) \}\}$"
)


class ProxmoxHostConnectionTest(unittest.TestCase):
    def proxmox_hosts(self):
        inventory = yaml.safe_load(HOSTS_FILE.read_text())
        return inventory["all"]["children"]["proxmox"]["hosts"]

    def test_every_proxmox_host_falls_back_to_its_own_name(self):
        hosts = self.proxmox_hosts()
        self.assertGreater(len(hosts), 0)

        for name, values in hosts.items():
            with self.subTest(host=name):
                ansible_host = values.get("ansible_host")
                self.assertIsInstance(ansible_host, str)
                self.assertRegex(ansible_host, ANSIBLE_HOST)
                self.assertEqual(values.get("proxmox_node_name"), name)

    def test_no_inventory_file_falls_back_to_omit_for_ansible_host(self):
        # `omit` does not remove an empty string that an unset env lookup
        # produces, so ansible_host would become "" and connect to localhost.
        for path in sorted(INVENTORY_DIR.rglob("*.yml")):
            with self.subTest(path=path.relative_to(ROOT)):
                for line in path.read_text().splitlines():
                    if re.search(r"\bansible_host\b", line):
                        self.assertNotIn("omit", line)

    def test_hardware_facts_loads_tofu_before_its_proxmox_hosts(self):
        # ansible_user for every proxmox host is proxmox_user, which resolves from
        # proxmox_user_from_tofu. Only load_tofu.yml sets that, so it must run first.
        plays = yaml.safe_load(HARDWARE_FACTS_PLAYBOOK.read_text())
        loads = [
            index
            for index, play in enumerate(plays)
            if play.get("ansible.builtin.import_playbook", play.get("import_playbook")) == "load_tofu.yml"
        ]
        targets = [
            index
            for index, play in enumerate(plays)
            if "hardware_facts_hosts" in str(play.get("hosts", ""))
        ]
        self.assertEqual(len(loads), 1)
        self.assertEqual(len(targets), 1)
        self.assertLess(loads[0], targets[0])


if __name__ == "__main__":
    unittest.main()
