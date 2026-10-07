#!/usr/bin/env python3
"""Exercise production HA admission against sanitized real API definitions."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads((Path(__file__).parent / "live_fixture.json").read_text())
TASKS = ROOT / "roles/pve_ha/tasks/relocation_preflight.yml"


def run(name, fixture, succeeds, disks=True, planned=None):
    vms = copy.deepcopy(fixture["published_vms"])
    if not disks:
        for vm in vms.values():
            vm["disks"] = []
    variables = {"pve_ha_resources_raw": {"stdout": json.dumps(fixture["resources"])},
                 "pve_ha_preflight_rules_raw": {"stdout": json.dumps(fixture["rules"])},
                 "pve_ha_preflight_replication_raw": {"stdout": json.dumps(fixture["jobs"])},
                 "pve_ha_preflight_resources_raw": {"stdout": json.dumps(fixture["placements"])},
                 "vms_from_tofu": vms,
                 "pve_ha_preflight_guest_configs": fixture["guest_configs"]}
    if planned is not None:
        variables["pve_ha_relocation_resources"] = fixture["resources"] + planned
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "test.yml"
        path.write_text(yaml.safe_dump([{"hosts": "localhost", "gather_facts": False,
            "vars": variables, "tasks": [{"ansible.builtin.include_tasks": str(TASKS)}]}]))
        result = subprocess.run(["ansible-playbook", "-i", "localhost,", "-c", "local", str(path)],
            env=dict(os.environ, ANSIBLE_LOCAL_TEMP=directory), capture_output=True, text=True)
        assert (result.returncode == 0) == succeeds, result.stdout + result.stderr
        assert "HA relocation admission" in result.stdout, result.stdout + result.stderr
        print("PASS:", name)


run("observed disabled replica outside strict affinity", FIXTURE, False)
repaired = copy.deepcopy(FIXTURE)
repaired["rules"] = []
for job in repaired["jobs"]:
    job["disable"] = 0
    sid = ("vm:" if any(r["sid"] == "vm:" + str(job["guest"]) for r in repaired["resources"]) else "ct:") + str(job["guest"])
    repaired["rules"].append({"type": "node-affinity", "strict": 1,
        "resources": sid, "nodes": job["source"] + "," + job["target"], "rule": "replica-" + sid})
run("enabled definitions intersect strict affinity", repaired, True)
stale = copy.deepcopy(repaired)
job = next(job for job in stale["jobs"] if "vm:" + str(job["guest"]) in {r["sid"] for r in stale["resources"]})
job["source"], job["target"] = job["target"], job["source"]
run("stored replica source disagrees with actual placement within allowed nodes", stale, False)
run("VM required disk metadata absent", repaired, False, disks=False)
without = copy.deepcopy(repaired)
without["rules"] = []
run("no strict affinity evidence", without, False)
conflict = copy.deepcopy(repaired)
relocating = {r["sid"] for r in conflict["resources"] if r.get("max_relocate", 1) > 0}
rule = next(r for r in conflict["rules"] if r["resources"] in relocating)
extra = dict(rule, rule="conflicting-rule", nodes="unrelated-node")
conflict["rules"].append(extra)
run("intersection of strict rules excludes replica", conflict, False)
run("new planned relocation without authoritative rule or replica", repaired, False,
    planned=[{"sid": "ct:99999", "max_relocate": 1}])
pinned = copy.deepcopy(repaired)
for resource in pinned["resources"]:
    resource["max_relocate"] = 0
new_limit = [{"sid": r["sid"], "max_relocate": 1} for r in FIXTURE["resources"] if r["max_relocate"] > 0]
run("planned positive limit is checked even when live limits are zero", pinned, True, planned=new_limit)
pinned["jobs"] = []
run("planned limit refuses missing replicas despite live limits zero", pinned, False, planned=new_limit)
negative = copy.deepcopy(repaired)
index = next(i for i, rule in enumerate(negative["rules"]) if rule["resources"] in relocating)
negative["rules"][index]["affinity"] = "negative"
run("negative affinity is rejected as unsupported", negative, False)
missing = copy.deepcopy(repaired)
missing["rules"][index].pop("nodes")
run("missing affinity node metadata", missing, False)
excluded = copy.deepcopy(repaired)
sid = next(sid for sid in excluded["guest_configs"] if sid.startswith("vm:"))
excluded["guest_configs"][sid]["scsi1"] = excluded["guest_configs"][sid]["scsi1"].replace("replicate=1", "replicate=0")
run("actual required data disk explicitly excludes replication", excluded, False)
empty = copy.deepcopy(repaired)
empty["guest_configs"].pop(sid)
run("actual VM disk configuration missing", empty, False)
unpublished = copy.deepcopy(repaired)
unpublished["guest_configs"][sid]["scsi2"] = unpublished["guest_configs"][sid]["scsi1"]
run("actual data disk missing from published inventory", unpublished, False)
mount = copy.deepcopy(repaired)
ct = next(sid for sid in mount["guest_configs"] if sid.startswith("ct:"))
mount["guest_configs"][ct]["mp9"] = "local-zfs:subvol-99999-disk-0,mp=/srv/application-data,replicate=0"
run("required LXC data mount explicitly excludes replication", mount, False)
bind = copy.deepcopy(repaired)
bind["guest_configs"][ct]["mp9"] = "/srv/source-data,mp=/srv/application-data"
run("required LXC bind mount cannot replicate", bind, False)
print("PASS: 16 actual Ansible HA admission cases")
