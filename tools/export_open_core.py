#!/usr/bin/env python3
"""Export a manifest-scoped, immutable Git snapshot; never package local files.

This validates archive selection, not copyright ownership, grant eligibility,
secret absence, or whether the selected sources form a runnable distribution.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = "docs/open-source/open-source-manifest.json"
ALWAYS = (
    "LICENSES/Apache-2.0.txt", "NOTICE", "LICENSING.md", "CONTRIBUTING.md",
    "SECURITY.md", "docs/open-source/OPEN_SOURCE_MANIFEST.md", MANIFEST_PATH,
    "docs/open-source/DEPENDENCY_LICENSE_REVIEW.md",
)


class ExportError(ValueError):
    """The requested snapshot or archive violates the export boundary."""


def git(root: Path, *args: str) -> bytes:
    proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          check=False, timeout=60)
    if proc.returncode:
        raise ExportError("git failed: " + proc.stderr.decode("utf-8", "replace").strip())
    return proc.stdout


def safe_path(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ExportError("manifest paths must be nonempty canonical strings")
    if any(c in value for c in "\\:*?[]\x00\r\n\t") or value.startswith("/"):
        raise ExportError(f"unsafe path: {value!r}")
    if any(part in ("", ".", "..", ".git") for part in value.split("/")):
        raise ExportError(f"non-canonical path: {value!r}")
    return value


def contains(parent: str, child: str) -> bool:
    return parent == child or child.startswith(parent + "/")


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ExportError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def snapshot(root: Path, ref: str = "HEAD") -> tuple[str, dict[str, tuple[str, str]]]:
    """Return the resolved commit and selected (mode, blob) entries from it."""
    commit = git(root, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise ExportError("Git did not resolve an immutable commit")
    tree = {}
    for record in git(root, "ls-tree", "-rz", commit).split(b"\0"):
        if not record:
            continue
        metadata, path_bytes = record.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split()
        tree[path_bytes.decode("utf-8")] = (mode, kind, oid)
    entry = tree.get(MANIFEST_PATH)
    if not entry or entry[0] not in ("100644", "100755") or entry[1] != "blob":
        raise ExportError("manifest must be a committed regular file")
    data = json.loads(git(root, "cat-file", "blob", entry[2]), object_pairs_hook=unique_object)
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ExportError("unsupported manifest schema")
    if data.get("license") != "Apache-2.0" or data.get("license_file") != ALWAYS[0] or data.get("notice_file") != "NOTICE":
        raise ExportError("unexpected licensing metadata")
    groups = []
    for field in ("include", "exclude"):
        values = data.get(field)
        if not isinstance(values, list) or not values:
            raise ExportError(f"{field} must be a nonempty list")
        values = [safe_path(p) for p in values]
        if len(set(values)) != len(values):
            raise ExportError(f"duplicate {field} path")
        groups.append(values)
    include, exclude = groups
    for inc in include:
        for exc in exclude:
            if contains(inc, exc) or contains(exc, inc):
                raise ExportError(f"open/reserved overlap: {inc} / {exc}")
    selected = {}
    for prefix in [*include, *ALWAYS]:
        matches = [p for p in tree if contains(prefix, p)]
        if not matches:
            raise ExportError(f"path missing from committed snapshot: {prefix}")
        for path in matches:
            safe_path(path)
            mode, kind, oid = tree[path]
            if kind != "blob" or mode not in ("100644", "100755"):
                raise ExportError(f"links and submodules are not exportable: {path}")
            if any(contains(exc, path) for exc in exclude):
                raise ExportError(f"reserved path selected: {path}")
            selected[path] = (mode, oid)
    return commit, selected


def export(root: Path, output: Path, ref: str = "HEAD") -> tuple[str, int, str]:
    commit, selected = snapshot(root, ref)
    root = root.resolve()
    output = output if output.is_absolute() else root / output
    if output.is_symlink() or output.exists():
        raise ExportError("refusing to overwrite an existing output")
    output = output.resolve()
    if not output.is_relative_to(root):
        raise ExportError("output must stay inside the repository")
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".open-core-", dir=output.parent)
    try:
        with os.fdopen(descriptor, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
                with tarfile.open(mode="w", fileobj=zipped, format=tarfile.PAX_FORMAT) as archive:
                    for path, (mode, oid) in sorted(selected.items()):
                        content = git(root, "cat-file", "blob", oid)
                        info = tarfile.TarInfo("residual-open-core/" + path)
                        info.size = len(content)
                        info.mode = 0o755 if mode == "100755" else 0o644
                        info.mtime = info.uid = info.gid = 0
                        info.uname = info.gname = ""
                        archive.addfile(info, io.BytesIO(content))
        digest = hashlib.sha256(Path(temporary).read_bytes()).hexdigest()
        os.link(temporary, output)  # Atomic publication; fails if output appeared.
    finally:
        Path(temporary).unlink(missing_ok=True)
    return commit, len(selected), digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="dist/residual-open-core.tar.gz")
    parser.add_argument("--ref", default="HEAD", help="Commit/ref to export; local edits are ignored")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    try:
        if args.list:
            _, selected = snapshot(ROOT, args.ref)
            print("\n".join(sorted(selected)))
        else:
            commit, count, digest = export(ROOT, Path(args.output), args.ref)
            print(json.dumps({"commit": commit, "files": count, "sha256": digest,
                              "output": args.output, "scope": "source-selection-only"}, sort_keys=True))
        return 0
    except (ExportError, OSError, UnicodeError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(f"OPEN-CORE EXPORT: FAIL: {error}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
