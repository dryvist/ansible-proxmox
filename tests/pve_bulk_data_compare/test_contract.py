from pathlib import Path

ROLE = Path(__file__).resolve().parents[2] / "roles" / "pve_bulk_data_compare"

def test_snapshot_free_frozen_comparison_contract():
    preflight = (ROLE / "tasks" / "preflight.yml").read_text()
    compare = (ROLE / "tasks" / "compare.yml").read_text()
    assert "zfs list -H -t snapshot -o name" in preflight
    assert "zpool list -H -o freeing" in preflight
    assert "scrub repaired 0B" in preflight
    assert "PASSED.phase" in preflight
    assert "pve3_manifest_dir" in preflight
    assert "manifest_export" in preflight
    assert "703040" in (ROLE / "defaults" / "main.yml").read_text()
    assert "736040" in (ROLE / "defaults" / "main.yml").read_text()
    assert "readonly=on" in compare
    assert "always:" in compare
    assert "readonly=off" in compare
    assert "restored exactly" in compare
    assert "zfs destroy" not in compare
    assert "vzdump" not in compare

if __name__ == "__main__": test_snapshot_free_frozen_comparison_contract()
