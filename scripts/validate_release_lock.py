#!/usr/bin/env python3
"""Fail-closed validator for a future RESIDUAL release dependency lock.

This tool validates lock *structure* only. It never resolves, downloads, or
installs dependencies and cannot create authoritative lock bytes.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


HASH = re.compile(r"--hash=sha256:([0-9a-f]{64})(?:\s|$)")
PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)==([^\s;\\]+)")


class LockContractError(ValueError):
    pass


def _logical_lines(text: str) -> list[str]:
    logical: list[str] = []
    pending = ""
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        pending = f"{pending} {stripped}".strip() if pending else stripped
        if pending.endswith("\\"):
            pending = pending[:-1].rstrip()
            continue
        logical.append(pending)
        pending = ""
    if pending:
        logical.append(pending)
    return logical


def validate_lock(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise LockContractError(f"lock file is missing: {path}")
    lines = _logical_lines(path.read_text(encoding="utf-8"))
    if not lines:
        raise LockContractError("lock file has no dependency entries")

    names: set[str] = set()
    hashes: set[str] = set()
    for index, line in enumerate(lines, 1):
        if line.startswith(("-e ", "--editable", "git+", "http://", "https://")):
            raise LockContractError(f"entry {index} uses an unapproved mutable/direct source")
        match = PIN.match(line)
        if match is None:
            raise LockContractError(f"entry {index} is not exact-pinned with ==")
        name = match.group(1).lower().replace("_", "-")
        if name in names:
            raise LockContractError(f"duplicate locked project: {name}")
        names.add(name)
        entry_hashes = HASH.findall(line)
        if not entry_hashes:
            raise LockContractError(f"entry {index} has no sha256 hash")
        hashes.update(entry_hashes)
        remainder = HASH.sub("", line)
        if " --hash=" in remainder or "--hash=" in remainder:
            raise LockContractError(f"entry {index} contains an unsupported hash algorithm")

    return {
        "status": "PASS",
        "entries": len(lines),
        "projects": len(names),
        "unique_sha256_hashes": len(hashes),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("lock", type=Path)
    args = parser.parse_args()
    result = validate_lock(args.lock)
    print(
        f"PASS entries={result['entries']} projects={result['projects']} "
        f"unique_sha256_hashes={result['unique_sha256_hashes']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
