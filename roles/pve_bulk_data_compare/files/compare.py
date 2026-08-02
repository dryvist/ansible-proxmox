#!/usr/bin/env python3
import json, os, sys, tempfile
from pathlib import Path
source, target, prefix = map(Path, sys.argv[1:4])
def rows(path):
    previous = None
    with path.open() as handle:
        for line in handle:
            record = json.loads(line)
            if previous is not None and record["path"] <= previous:
                raise RuntimeError(f"manifest {path} is not strictly path-sorted")
            previous = record["path"]
            yield record
def atomic(path, records):
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    os.close(descriptor)
    temp = Path(temporary_name)
    with temp.open("w") as handle:
        for record in records: handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush(); os.fsync(handle.fileno())
    os.replace(temp, path)
a, b = iter(rows(source)), iter(rows(target)); left, right = next(a, None), next(b, None)
only_target=[]; only_source=[]; metadata=[]; content=[]
while left is not None or right is not None:
    if right is None or left is not None and left["path"] < right["path"]: only_source.append(left); left=next(a,None)
    elif left is None or right["path"] < left["path"]: only_target.append(right); right=next(b,None)
    else:
        if left.get("sha256") != right.get("sha256") and left["type"] == right["type"] == "file": content.append({"path":left["path"],"pve2":left.get("sha256"),"pve540":right.get("sha256")})
        if {k:v for k,v in left.items() if k != "sha256"} != {k:v for k,v in right.items() if k != "sha256"}: metadata.append({"path":left["path"],"pve2":left,"pve540":right})
        left,right=next(a,None),next(b,None)
atomic(Path(str(prefix)+".pve2-only.jsonl"), only_source); atomic(Path(str(prefix)+".pve540-only.jsonl"), only_target); atomic(Path(str(prefix)+".metadata-differences.jsonl"), metadata); atomic(Path(str(prefix)+".content-differences.jsonl"), content)
summary={"pve2_only":len(only_source),"pve540_only":len(only_target),"metadata_differences":len(metadata),"content_differences":len(content)}
atomic(Path(str(prefix)+".summary.jsonl"), [summary]); print(json.dumps(summary, sort_keys=True)); sys.exit(0 if not any(summary.values()) else 1)
