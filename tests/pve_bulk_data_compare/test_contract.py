import re
from pathlib import Path

ROLE = Path(__file__).resolve().parents[2] / "roles" / "pve_bulk_data_compare"

def test_node_variables_are_required_and_undefaulted():
    defaults = (ROLE / "defaults" / "main.yml").read_text()
    preflight = (ROLE / "tasks" / "preflight.yml").read_text()
    # A default here is what pinned this role to one node and made it
    # unusable against any other.
    for var in ("source_node", "target_node", "evidence_host"):
        assert not re.search(rf"^pve_bulk_data_compare_{var}:", defaults, re.M)
        assert f"pve_bulk_data_compare_{var} is defined" in preflight
        assert f"pve_bulk_data_compare_{var} | default('') | length > 0" in preflight

def test_snapshot_free_frozen_comparison_contract():
    preflight = (ROLE / "tasks" / "preflight.yml").read_text()
    compare = (ROLE / "tasks" / "compare.yml").read_text()
    assert "zfs list -H -t snapshot -o name" in preflight
    assert "zpool list -H -o freeing" in preflight
    assert "scrub repaired 0B" in preflight
    # The pre-migration integrity-gate marker check is gone with the role that
    # wrote it; assert it stayed gone rather than coming back as an inert stub.
    assert "PASSED" not in preflight
    assert "evidence_manifest_dir" in preflight
    assert "manifest_export" in preflight
    assert "703040" in (ROLE / "defaults" / "main.yml").read_text()
    assert "736040" in (ROLE / "defaults" / "main.yml").read_text()
    assert "readonly=on" in compare
    assert "always:" in compare
    assert "readonly=off" in compare
    assert "restored exactly" in compare
    assert "zfs destroy" not in compare
    assert "vzdump" not in compare

if __name__ == "__main__":
    test_node_variables_are_required_and_undefaulted()
    test_snapshot_free_frozen_comparison_contract()
