"""rsync target-endpoint contract: literal inventory fast path + canonical FQDN."""

from pathlib import Path

import pytest

from conftest import ROLE, flatten_included_tasks, run_canonical_endpoint_contract


def test_rsync_endpoint_keeps_the_literal_inventory_fast_path() -> None:
    contract = (ROLE / "tasks" / "preflight_contract.yml").read_text()

    assert (
        "pve_guest_evacuation_lxc_managed_volumes_target_rsync_host\n"
        "        == hostvars[pve_guest_evacuation_lxc_managed_volumes_target_node].ansible_host"
        in contract
    )
    assert "or (" in contract


def test_unequal_rsync_endpoint_requires_a_verified_canonical_fqdn() -> None:
    defaults = (ROLE / "defaults" / "main.yml").read_text()
    contract = (ROLE / "tasks" / "preflight_contract.yml").read_text()

    assert "pve_guest_evacuation_lxc_managed_volumes_target_rsync_canonical_fqdn: \"\"" in defaults
    assert "Resolve the approved pve540 canonical FQDN from pve2" in contract
    assert "Resolve the pve540 inventory endpoint from pve2" in contract
    assert "- ahostsv4" in contract
    assert "pve_guest_evacuation_lxc_managed_volumes_target_rsync_host\n              == pve_guest_evacuation_lxc_managed_volumes_target_rsync_canonical_fqdn" in contract
    assert "pve_guest_evacuation_lxc_managed_volumes_canonical_fqdn_ipv4s" in contract
    assert "pve_guest_evacuation_lxc_managed_volumes_inventory_endpoint_ipv4s" in contract
    assert "| intersect(pve_guest_evacuation_lxc_managed_volumes_inventory_endpoint_ipv4s)" in contract


def test_unequal_rsync_endpoint_rejects_aliases_and_unverified_resolution() -> None:
    contract = (ROLE / "tasks" / "preflight_contract.yml").read_text()

    assert "is match('^[A-Za-z0-9][A-Za-z0-9-]*(\\.[A-Za-z0-9][A-Za-z0-9-]*)+$')" in contract
    assert "is not match('^([0-9]{1,3}\\.){3}[0-9]{1,3}$')" in contract
    assert "pve_guest_evacuation_lxc_managed_volumes_canonical_fqdn_resolution.rc == 0" in contract
    assert "pve_guest_evacuation_lxc_managed_volumes_inventory_endpoint_resolution.rc == 0" in contract
    assert "pve_guest_evacuation_lxc_managed_volumes_canonical_fqdn_ipv4s | length > 0" in contract
    assert "pve_guest_evacuation_lxc_managed_volumes_inventory_endpoint_ipv4s | length > 0" in contract
    assert "unapproved aliases, IP literals, missing DNS results, and mismatches" in contract


def test_canonical_fqdn_endpoint_contract_accepts_a_matching_literal_inventory_ipv4(tmp_path: Path) -> None:
    result = run_canonical_endpoint_contract(
        tmp_path,
        "pve540.jacobpevans.com",
        "192.0.2.54",
        ["192.0.2.54"],
        ["192.0.2.54"],
    )

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("canonical_fqdn", "inventory_endpoint", "canonical_ipv4s", "inventory_ipv4s"),
    [
        ("pve540", "192.0.2.54", ["192.0.2.54"], ["192.0.2.54"]),
        ("192.0.2.54", "192.0.2.55", ["192.0.2.54"], ["192.0.2.55"]),
        ("pve540.jacobpevans.com", "192.0.2.54", ["192.0.2.55"], ["192.0.2.54"]),
    ],
    ids=["single-label-alias", "ip-literal", "dns-mismatch"],
)
def test_canonical_fqdn_endpoint_contract_rejects_invalid_or_mismatched_inputs(
    tmp_path: Path,
    canonical_fqdn: str,
    inventory_endpoint: str,
    canonical_ipv4s: list[str],
    inventory_ipv4s: list[str],
) -> None:
    result = run_canonical_endpoint_contract(
        tmp_path,
        canonical_fqdn,
        inventory_endpoint,
        canonical_ipv4s,
        inventory_ipv4s,
    )

    assert result.returncode != 0


def test_verified_fqdn_preserves_one_ed25519_key_and_strict_ssh() -> None:
    transfer = flatten_included_tasks(ROLE / "tasks" / "transfer.yml")

    assert "| list | length == 1" in transfer
    assert "ssh-ed25519" in transfer
    for setting in (
        "StrictHostKeyChecking=yes",
        "UserKnownHostsFile={{ pve_guest_evacuation_lxc_managed_volumes_rsync_known_hosts_file }}",
        "GlobalKnownHostsFile=/dev/null",
        "PasswordAuthentication=no",
        "KbdInteractiveAuthentication=no",
    ):
        assert setting in transfer


if __name__ == "__main__":
    test_rsync_endpoint_keeps_the_literal_inventory_fast_path()
    test_unequal_rsync_endpoint_requires_a_verified_canonical_fqdn()
    test_unequal_rsync_endpoint_rejects_aliases_and_unverified_resolution()
    test_verified_fqdn_preserves_one_ed25519_key_and_strict_ssh()
