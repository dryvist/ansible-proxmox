#!/usr/bin/env python3
"""Verify the upstream module keeps the Proxmox token secret masked."""

import importlib
import unittest

from ansible.plugins.loader import init_plugin_loader


def _proxmox_auth_argument_spec() -> dict[str, dict[str, object]]:
    """Load the installed collection through Ansible's configured loader."""
    init_plugin_loader()
    module = importlib.import_module(
        "ansible_collections.community.proxmox.plugins.module_utils.proxmox"
    )
    return module.proxmox_auth_argument_spec()


class ContainerStartModuleContract(unittest.TestCase):
    def test_token_secret_is_masked_but_token_id_is_diagnostic(self) -> None:
        auth_spec = _proxmox_auth_argument_spec()

        self.assertIs(auth_spec["api_token_secret"]["no_log"], True)
        self.assertIs(auth_spec["api_token_id"]["no_log"], False)


if __name__ == "__main__":
    unittest.main()
