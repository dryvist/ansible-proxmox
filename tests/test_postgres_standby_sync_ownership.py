"""Contract check: the standby mirror must not copy the source's owner or group."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYNC = (ROOT / "roles/postgres_standby/templates/postgres-standby-sync.sh.j2").read_text()


def test_mirror_rsync_does_not_copy_the_source_owner_or_group():
    # -a implies --owner and --group, which copy the source's uid/gid onto the
    # archive directory and flip the declared root:root 0750 on every run.
    invocation = SYNC.split("if ! rsync ", 1)[1].split(">>", 1)[0]
    assert "--no-owner" in invocation
    assert "--no-group" in invocation
