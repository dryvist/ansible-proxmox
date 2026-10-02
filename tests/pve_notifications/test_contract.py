#!/usr/bin/env python3
"""Assert pve_notifications builds its ntfy URL from the ingress subdomain.

Molecule cannot cover this: the role's whole task block (including the URL
itself) is skipped under Docker's ansible_virtualization_type, so the Jinja
expression never renders in that scenario. Fronted services like the ntfy
hub are only published under PROXMOX_SUBDOMAIN (the ingress subdomain) --
never domain_from_tofu, the estate apex -- or the webhook target would point
at a URL that cannot reach the hub.

Run: python3 tests/pve_notifications/test_contract.py
"""
import os
import sys

ROLE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                                    "roles", "pve_notifications"))
DEFAULTS = os.path.join(ROLE, "defaults", "main.yml")
TASKS = os.path.join(ROLE, "tasks", "main.yml")


def check():
    failures = []
    with open(DEFAULTS) as fh:
        defaults = fh.read()
    with open(TASKS) as fh:
        tasks = fh.read()

    if "pve_notifications_ntfy_url:" not in defaults:
        sys.exit("FAIL: %s has no pve_notifications_ntfy_url -- the role "
                 "changed shape and this test no longer covers it" % DEFAULTS)

    url_line = next((ln for ln in defaults.splitlines()
                     if ln.strip().startswith("pve_notifications_ntfy_url:")), "")
    if "domain_from_tofu" in url_line:
        failures.append("pve_notifications_ntfy_url is still built from "
                        "domain_from_tofu (the estate apex), which a fronted "
                        "service like ntfy cannot be reached through")
    if "lookup('env', 'PROXMOX_SUBDOMAIN')" not in url_line:
        failures.append("pve_notifications_ntfy_url is not built from "
                        "PROXMOX_SUBDOMAIN (the ingress subdomain)")
    if "/proxmox" not in url_line:
        failures.append("pve_notifications_ntfy_url no longer targets the "
                        "'proxmox' topic")
    if "pve_notifications_ntfy_token:" not in defaults:
        failures.append("no optional pve_notifications_ntfy_token variable "
                        "is defined")
    if "PROXMOX_SUBDOMAIN" not in tasks:
        failures.append("the role's task block does not assert "
                        "PROXMOX_SUBDOMAIN resolved before using it")

    return failures


def main():
    failures = check()
    if failures:
        print("FAIL: pve_notifications ntfy URL contract")
        for f in failures:
            print("  - %s" % f)
        return 1
    print("PASS: pve_notifications builds its ntfy URL from the ingress "
          "subdomain, not the estate apex")
    return 0


if __name__ == "__main__":
    sys.exit(main())
