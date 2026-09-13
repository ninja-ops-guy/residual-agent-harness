#!/usr/bin/env python3
"""Export a committed, reproducible source bundle with history and file checksums."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path


def build(destination):
    root = Path(__file__).resolve().parents[1]
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args])
    if git("status", "--porcelain").strip():
        raise SystemExit("Commit tracked source changes before packaging; the archive must match its history.")
    files = git("ls-files", "-z").decode().split("\0")[:-1]
    commit = git("rev-parse", "HEAD").decode().strip()
    stamp = int(git("show", "-s", "--format=%ct", "HEAD").decode())
    import datetime
    date = datetime.datetime.fromtimestamp(stamp, datetime.timezone.utc).timetuple()[:6]
    destination = Path(destination).resolve(); destination.parent.mkdir(parents=True, exist_ok=True)
    prefix = "residual-command-station/"
    checksums = []
    with tempfile.TemporaryDirectory() as d:
        bundle = Path(d) / "history.bundle"
        git("bundle", "create", str(bundle), "--all")
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            def add(name, data, mode=0o100644):
                info = zipfile.ZipInfo(prefix + name, date_time=date)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3; info.external_attr = mode << 16
                z.writestr(info, data)
                checksums.append(hashlib.sha256(data).hexdigest() + "  " + name)
            for name in files:
                p = root / name
                if p.is_symlink():
                    raise SystemExit("Unexpected source symlink: " + name)
                add(name, p.read_bytes(), p.stat().st_mode)
            add("history.bundle", bundle.read_bytes())
            add("BUNDLE.json", json.dumps({"version": "0.3.0", "commit": commit, "files": len(files),
                "contains_model_weights": False, "entrypoint": "START-HERE.md"}, indent=2).encode())
            add("SHA256SUMS", ("\n".join(checksums) + "\n").encode())
    value = {"file": str(destination), "commit": commit, "size": destination.stat().st_size,
             "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}
    print(json.dumps(value, indent=2))
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="dist/residual-command-station-0.3.0.zip")
    build(parser.parse_args().output)
