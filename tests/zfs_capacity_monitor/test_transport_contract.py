#!/usr/bin/env python3
"""Assert the zfs-capacity-monitor deadman delivery contract holds end to end.

Covers the /fail vs OK endpoint split, the create-on-ping requirement,
recovery clearing a latched breach, an unreadable sensor tripping the deadman
instead of reporting silence, and benign sensor stderr staying diagnostic
instead of corrupting the parsed capacity data.

See _helpers.py for why this test extracts the live template instead of
carrying its own copy of the script.

Run: python3 tests/zfs_capacity_monitor/test_transport_contract.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from _helpers import (  # noqa: E402
    DEADMAN_DEFAULT,
    band_state,
    curl_calls,
    ok_heartbeats,
    read_calls,
    run,
    write_monitor,
)

DEADMAN = DEADMAN_DEFAULT
THRESHOLDS = (50, 75, 85, 90, 94)


def check_transports():
    """The delivery contract for the single deadman path."""
    failures = []

    # 4. A breach reaches the /fail endpoint and is recorded as reported.
    with tempfile.TemporaryDirectory() as tmp:
        write_monitor(tmp, thresholds=THRESHOLDS, deadman_url=DEADMAN)

        run(tmp, 94, curl_exit=0)
        if curl_calls(tmp, containing=DEADMAN + "/fail") == 0:
            failures.append("a breach sent nothing to the /fail endpoint")
        if band_state(tmp) != "94":
            failures.append("a delivered breach did not record band 94 (got "
                            "%r), so it will not be treated as reported"
                            % band_state(tmp))

    # 5. A breach must NOT also send the OK heartbeat in the same run — that
    #    would clear the very alert it just raised.
    with tempfile.TemporaryDirectory() as tmp:
        write_monitor(tmp, thresholds=THRESHOLDS, deadman_url=DEADMAN)

        run(tmp, 94, curl_exit=0)
        calls = read_calls(tmp)
        ok_pings = ok_heartbeats(calls, deadman=DEADMAN)
        if ok_pings:
            failures.append("a breaching run also sent an OK heartbeat (%d), "
                            "which clears the alert it just raised" % len(ok_pings))

    # A clean pass, by contrast, must beat — otherwise a dead monitor and a
    # healthy pool look identical.
    #
    # Run from FRESH state, not after the breach above. Dropping from a breach
    # also emits a recovery notification, and that lands on the same OK
    # endpoint as the heartbeat — so a run with prior state cannot tell the two
    # apart, and the assertion passes whether the heartbeat exists or not.
    # Verified by deleting the heartbeat from the template: with prior state
    # the test still passed; from fresh state it fails as it must.
    with tempfile.TemporaryDirectory() as tmp:
        write_monitor(tmp, thresholds=THRESHOLDS, deadman_url=DEADMAN)

        run(tmp, 10, curl_exit=0)
        calls = read_calls(tmp)
        if not ok_heartbeats(calls, deadman=DEADMAN):
            failures.append("a clean pass sent no heartbeat, so a stopped "
                            "monitor is indistinguishable from a healthy pool")

    # 5b. Every ping must ask the destination to create itself. The deadman is
    #     addressed by slug, and an unregistered slug answers 404 — so without
    #     this the monitor runs, exits 0, and reports to nothing, which is the
    #     precise condition it exists to detect. Observed live before this
    #     guard existed.
    with tempfile.TemporaryDirectory() as tmp:
        write_monitor(tmp, thresholds=THRESHOLDS, deadman_url=DEADMAN)

        run(tmp, 94, curl_exit=0)   # breach -> /fail
        run(tmp, 10, curl_exit=0)   # recovery + heartbeat
        unprovisioned = [c for c in read_calls(tmp)
                         if DEADMAN in c and "create=1" not in c]
        if unprovisioned:
            failures.append(
                "%d ping(s) did not request creation of the destination; an "
                "unregistered endpoint answers 404 and the monitor then "
                "reports to nothing while exiting 0"
                % len(unprovisioned))

    # 6. Recovery must clear the alert, and must go to the OK endpoint rather
    #    than /fail — otherwise a pool that drained still reads as breached and
    #    the next real crossing has nothing to escalate from.
    with tempfile.TemporaryDirectory() as tmp:
        write_monitor(tmp, thresholds=THRESHOLDS, deadman_url=DEADMAN)

        run(tmp, 94, curl_exit=0)          # breach
        os.remove(os.path.join(tmp, "curl.log"))
        run(tmp, 10, curl_exit=0)          # drained

        if band_state(tmp) != "0":
            failures.append("after recovery the band is %r, expected '0' — the "
                            "pool would stay latched as breached"
                            % band_state(tmp))
        if curl_calls(tmp, containing=DEADMAN + "/fail") != 0:
            failures.append("recovery hit the /fail endpoint; it must report OK")
        if curl_calls(tmp) == 0:
            failures.append("recovery sent nothing at all")

    # 7. An unreadable sensor must trip the deadman and fail loudly. "zpool
    #    list did not answer" is not "the pool is fine".
    with tempfile.TemporaryDirectory() as tmp:
        write_monitor(tmp, thresholds=THRESHOLDS, deadman_url=DEADMAN)

        rc, err = run(tmp, 50, curl_exit=0, zpool_exit=1)
        if rc == 0:
            failures.append("a failing `zpool list` exited 0 — cron would "
                            "record a successful run against no data")
        if curl_calls(tmp, containing=DEADMAN + "/fail") == 0:
            failures.append("a failing `zpool list` did not trip the deadman, "
                            "so an unreadable sensor reports as silence")
        if "zpool list" not in err:
            failures.append("a failing `zpool list` produced no diagnostic on "
                            "stderr (got %r)" % err.strip())

    # 8. Benign sensor warnings belong on stderr, never in the tab-delimited
    #    data consumed by the capacity loops. Merging both streams makes the
    #    warning a fake pool/dataset row and produces integer-expression errors.
    with tempfile.TemporaryDirectory() as tmp:
        write_monitor(tmp, thresholds=THRESHOLDS, deadman_url=DEADMAN)

        rc, err = run(tmp, 10, curl_exit=0,
                      zpool_warning="zpool benign warning",
                      zfs_warning="zfs benign warning")
        if rc != 0:
            failures.append("benign sensor warnings aborted the monitor "
                            "(rc=%d, stderr=%r)" % (rc, err.strip()))
        if "integer expression expected" in err:
            failures.append("sensor stderr was parsed as capacity data "
                            "(stderr=%r)" % err.strip())
        for warning in ("zpool benign warning", "zfs benign warning"):
            if warning not in err:
                failures.append("sensor warning %r was hidden instead of "
                                "remaining diagnostic" % warning)

    return failures


def main():
    failures = check_transports()
    if failures:
        print("FAIL: zfs-capacity-monitor transport contract")
        for f in failures:
            print("  - %s" % f)
        return 1
    print("PASS: the deadman beats only when every pool is under threshold, "
          "recovery clears cleanly, and an unreadable sensor trips it instead "
          "of reporting silence")
    return 0


if __name__ == "__main__":
    sys.exit(main())
