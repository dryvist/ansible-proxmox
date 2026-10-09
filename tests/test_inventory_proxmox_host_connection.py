#!/usr/bin/env python3
"""Pin the Proxmox host connection contract: an unset env var never means localhost."""

from pathlib import Path
import re
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_DIR = ROOT / "inventory"
HOSTS_FILE = INVENTORY_DIR / "hosts.yml"
ANSIBLE_HOST = re.compile(
    r"^\{\{ lookup\('env', '(PVE\d_VE_HOSTNAME)'\) \| default\(inventory_hostname, true\) \}\}$"
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

    def test_no_inventory_file_falls_back_to_omit_for_ansible_host(self):
        # `omit` does not remove an empty string that an unset env lookup
        # produces, so ansible_host would become "" and connect to localhost.
        for path in sorted(INVENTORY_DIR.rglob("*.yml")):
            with self.subTest(path=path.relative_to(ROOT)):
                for line in path.read_text().splitlines():
                    if re.search(r"\bansible_host\b", line):
                        self.assertNotIn("omit", line)


if __name__ == "__main__":
    unittest.main()
