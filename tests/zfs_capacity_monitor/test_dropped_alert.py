#!/usr/bin/env python3
"""Assert the ZFS capacity monitor cannot silence itself by failing to notify.

The monitor alerts on a band CHANGE, tracked in a per-pool state file. That
makes the state write the safety-critical line: if the band advances while the
notification did not actually go out, the next run sees no change and stays
quiet — the pool then fills through every remaining band in silence. The alert
that never arrives is indistinguishable from a healthy pool.

See _helpers.py for why this test extracts the live template instead of
carrying its own copy of the script.

Run: python3 tests/zfs_capacity_monitor/test_dropped_alert.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from _helpers import band_state, curl_calls, run, write_monitor  # noqa: E402


def check_dropped_alert():
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        write_monitor(tmp)

        # 1. Notification fails at 90%: the band must NOT be recorded, or the
        #    pool goes silent from here to ENOSPC.
        rc, err = run(tmp, 90, curl_exit=7)
        if band_state(tmp) is not None:
            failures.append(
                "band %r was recorded even though the notification failed — a "
                "single dropped push now silences that band permanently"
                % band_state(tmp))
        if rc != 0:
            failures.append("a failed notification aborted the run (rc=%d); it "
                            "must keep checking the remaining pools\n"
                            "      stderr: %s" % (rc, err.strip() or "(empty)"))
        # Assert on the fact reported, not the phrasing: the operator has to be
        # able to tell an undelivered alert from a quiet pool.
        if "not recorded" not in err:
            failures.append("a failed notification produced no stderr warning, "
                            "so nothing distinguishes it from a quiet pool "
                            "(stderr: %r)" % err.strip())

        # 2. Next run, endpoint healthy: the missed alert must be retried.
        before = curl_calls(tmp)
        rc, _ = run(tmp, 90, curl_exit=0)
        if curl_calls(tmp) <= before:
            failures.append("the retry run sent no notification — the alert "
                            "missed while the endpoint was down is lost")
        if band_state(tmp) != "90":
            failures.append("band is %r after a successful push, expected '90'"
                            % band_state(tmp))

        # 3. Still at 90%, endpoint healthy: no repeat. The alert fires on a
        #    band CHANGE, and a monitor that re-pushes every interval gets muted
        #    by whoever receives it.
        # An unchanged band must send NOTHING: no repeat alert (which trains the
        # recipient to ignore it) and no OK heartbeat either, because a pool
        # still sitting above its threshold must not clear its own alert.
        before = curl_calls(tmp)
        run(tmp, 90, curl_exit=0)
        if curl_calls(tmp) != before:
            failures.append("an unchanged band above threshold sent %d more "
                            "call(s); a repeat alert is noise and an OK "
                            "heartbeat would clear a live breach"
                            % (curl_calls(tmp) - before))
    return failures


def main():
    failures = check_dropped_alert()
    if failures:
        print("FAIL: zfs-capacity-monitor dropped-alert contract")
        for f in failures:
            print("  - %s" % f)
        return 1
    print("PASS: band state survives a dropped alert, retries once the "
          "endpoint recovers, and an unchanged band above threshold sends "
          "nothing more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
