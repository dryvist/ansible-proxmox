#!/usr/bin/env python3
import hashlib, json, os, stat, sys, tempfile
from pathlib import Path

root, destination = map(Path, sys.argv[1:3])
temporary = destination.with_name(destination.name + ".tmp")
def record(path):
    info = path.lstat(); relative = "." if path == root else str(path.relative_to(root))
    mode = info.st_mode
    kind = "file" if stat.S_ISREG(mode) else "directory" if stat.S_ISDIR(mode) else "symlink" if stat.S_ISLNK(mode) else "block_device" if stat.S_ISBLK(mode) else "char_device" if stat.S_ISCHR(mode) else "fifo" if stat.S_ISFIFO(mode) else "socket" if stat.S_ISSOCK(mode) else "other"
    item = {"path": relative, "type": kind, "size": info.st_size, "mode": stat.S_IMODE(mode), "uid": info.st_uid, "gid": info.st_gid, "mtime_ns": info.st_mtime_ns, "link_target": os.readlink(path) if kind == "symlink" else None}
    if kind == "file":
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(8 * 1024 * 1024), b""): digest.update(block)
        item["sha256"] = digest.hexdigest()
    return item
descriptor, temporary_name = tempfile.mkstemp(prefix=destination.name + ".", dir=destination.parent)
os.close(descriptor)
temporary = Path(temporary_name)
with temporary.open("w", encoding="utf-8") as output:
    stack = [root]
    while stack:
        current = stack.pop(); output.write(json.dumps(record(current), sort_keys=True, separators=(",", ":")) + "\n")
        if current.is_dir() and not current.is_symlink():
            entries = sorted(current.iterdir(), key=lambda entry: os.fsencode(entry.name), reverse=True)
            stack.extend(entries)
    output.flush(); os.fsync(output.fileno())
os.replace(temporary, destination)
