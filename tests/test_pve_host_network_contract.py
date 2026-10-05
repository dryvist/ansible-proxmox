#!/usr/bin/env python3
"""Pin the host network role's inventory, .link, and bridge contract."""

from pathlib import Path
import re
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "roles/pve_host_network"
MAC_PATTERN = re.compile(r"^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")
NAME_PATTERN = re.compile(r"^nic[0-9]+$")


def read_yaml(path):
    return yaml.safe_load(path.read_text())


class PveHostNetworkContractTest(unittest.TestCase):
    def test_inventory_supplies_mac_and_stable_name_for_each_pinned_node(self):
        host_vars = [
            ROOT / "inventory/host_vars/pve-r540.yml",
            ROOT / "inventory/host_vars/pve-r710/00-core.yml",
            ROOT / "inventory/host_vars/pve-w5900.yml",
            ROOT / "inventory/host_vars/pve-w1700/00-core.yml",
        ]

        for path in host_vars:
            with self.subTest(path=path):
                values = read_yaml(path)
                self.assertRegex(values["pve_host_network_uplink"], NAME_PATTERN)
                self.assertRegex(values["pve_host_network_uplink_mac"], MAC_PATTERN)

    def test_bridge_port_uses_the_inventory_pinned_name(self):
        template = (ROLE / "templates/interfaces.j2").read_text()
        bridge_ports = re.search(r"^\s*bridge-ports\s+(.+)$", template, re.MULTILINE)

        self.assertIsNotNone(bridge_ports)
        self.assertEqual(bridge_ports.group(1), "{{ pve_host_network_uplink }}")
        self.assertNotRegex(bridge_ports.group(1), r"\b(?:eno|enp|ens|enx)[a-zA-Z0-9_.:-]*")

    def test_link_matches_permanent_ethernet_mac_and_same_name(self):
        template = (ROLE / "templates/uplink.link.j2").read_text()

        self.assertIn("MACAddress={{ pve_host_network_uplink_mac }}", template)
        self.assertIn("Type=ether", template)
        self.assertIn("Name={{ pve_host_network_uplink }}", template)

    def test_enforcement_guards_then_writes_both_files_without_reloading(self):
        tasks = read_yaml(ROLE / "tasks/main.yml")
        enforcement = next(
            task for task in tasks
            if task["name"] == "Enforce the pinned host uplink and bridge configuration"
        )
        block = enforcement["block"]
        task_names = [task["name"] for task in block]

        self.assertEqual(
            task_names[0], "Require a pinned uplink identity"
        )
        self.assertIn("Render the MAC-pinned uplink name", task_names)
        self.assertIn("Render the interfaces file", task_names)
        self.assertLess(
            task_names.index("Render the MAC-pinned uplink name"),
            task_names.index("Render the interfaces file"),
        )
        self.assertIn("Report the required controlled reboot", task_names)

        guard = block[0]["ansible.builtin.assert"]["that"]
        self.assertTrue(
            any("pve_host_network_uplink_mac is match" in condition for condition in guard)
        )
        link_task = next(
            task for task in block if task["name"] == "Render the MAC-pinned uplink name"
        )
        bridge_task = next(
            task for task in block if task["name"] == "Render the interfaces file"
        )
        self.assertEqual(link_task["ansible.builtin.template"]["src"], "uplink.link.j2")
        self.assertEqual(
            link_task["ansible.builtin.template"]["dest"],
            "/usr/local/lib/systemd/network/10-pve-host-uplink.link",
        )
        self.assertEqual(bridge_task["ansible.builtin.template"]["src"], "interfaces.j2")
        self.assertEqual(
            bridge_task["ansible.builtin.template"]["dest"], "/etc/network/interfaces"
        )
        self.assertEqual(link_task["notify"], "Rebuild initramfs for pinned interface")
        handlers = read_yaml(ROLE / "handlers/main.yml")
        self.assertEqual(handlers[0]["name"], link_task["notify"])
        self.assertEqual(
            handlers[0]["ansible.builtin.command"]["cmd"], "update-initramfs -u -k all"
        )

        serialized = yaml.safe_dump(block)
        self.assertIn("pve_host_network_uplink_mac", serialized)
        self.assertNotIn("ifreload", serialized)
        self.assertNotRegex(serialized, r"\bansible\.builtin\.reboot\b")

    def test_wake_on_lan_uses_the_same_stable_alias(self):
        for path in (
            ROOT / "inventory/host_vars/pve-w5900.yml",
            ROOT / "inventory/host_vars/pve-w1700/00-core.yml",
        ):
            with self.subTest(path=path):
                values = read_yaml(path)
                if values.get("wol_enable_enabled"):
                    self.assertEqual(
                        values["wol_enable_interface"],
                        values["pve_host_network_uplink"],
                    )
                    self.assertEqual(
                        values["wol_enable_mac"], "{{ pve_host_network_uplink_mac }}"
                    )

    def test_wake_on_lan_resolves_the_current_name_from_the_pinned_mac(self):
        tasks = read_yaml(ROOT / "roles/wol_enable/tasks/main.yml")
        serialized = yaml.safe_dump(tasks)
        template = (ROOT / "roles/wol_enable/templates/99-wol-enable.rules.j2").read_text()

        self.assertIn("cmd: ip -o link", serialized)
        self.assertIn("wol_enable_interface_resolved", serialized)
        self.assertIn('ATTR{address}=="{{ wol_enable_mac | lower }}"', template)

    def test_enforcement_resolves_network_settings_before_writing(self):
        tasks = read_yaml(ROOT / "roles/pve_host_network/tasks/main.yml")
        enforcement = next(
            task["block"]
            for task in tasks
            if task.get("name") == "Enforce the pinned host uplink and bridge configuration"
        )
        names = [task.get("name") for task in enforcement]
        self.assertLess(
            names.index("Resolve management address and gateway"),
            names.index("Render the interfaces file"),
        )
        serialized = yaml.safe_dump(enforcement)
        template = (ROOT / "roles/pve_host_network/templates/interfaces.j2").read_text()
        self.assertIn("ip", serialized)
        self.assertIn("pve_host_network_primary_iface", serialized)
        self.assertIn("ansible_facts.default_ipv4", serialized)
        self.assertIn("pve_host_network_address_resolved", template)
        self.assertIn("pve_host_network_gateway_resolved", template)


if __name__ == "__main__":
    unittest.main()
