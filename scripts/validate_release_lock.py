#!/usr/bin/env python3
"""Validate the complete, deliberately narrow v1 release-lock grammar.

Validation only: no resolution, download, installation or artifact authority.
Versions use explicit public-version spellings, optionally with local labels;
this is not a general pip requirements parser. See the PR-G28 handoff.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


NUMBER = r"(?:0|[1-9][0-9]*)"
VERSION = (
    rf"(?:{NUMBER}!)?{NUMBER}(?:\.{NUMBER})*"
    rf"(?:(?:a|b|rc){NUMBER})?(?:\.post{NUMBER})?(?:\.dev{NUMBER})?"
    r"(?:\+[a-z0-9]+(?:\.[a-z0-9]+)*)?"
)
NAME = r"[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?"
PIN = re.compile(rf"({NAME})==({VERSION})", re.ASCII)
HASH = re.compile(r"--hash=sha256:([0-9a-f]{64})", re.ASCII)


class LockContractError(ValueError):
    pass


def _logical_lines(text: str) -> list[str]:
    """Join only complete-token continuations; reject ambiguous input."""
    logical: list[str] = []
    pending: list[str] = []
    for line_number, raw in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        stripped = raw.strip(" \t")
        if not stripped or stripped.startswith("#"):
            if pending:
                raise LockContractError(f"interrupted continuation at line {line_number}")
            continue
        if any(c != "\t" and not " " <= c <= "~" for c in raw):
            raise LockContractError(f"unsupported character at line {line_number}")
        continued = stripped.endswith("\\")
        if continued:
            if len(stripped) < 2 or stripped[-2] not in " \t":
                raise LockContractError(f"continuation splits a token at line {line_number}")
            stripped = stripped[:-1].rstrip(" \t")
        if "\\" in stripped:
            raise LockContractError(f"unsupported escape at line {line_number}")
        pending.append(stripped)
        if not continued:
            logical.append(" ".join(pending))
            pending = []
    if pending:
        raise LockContractError("unterminated continuation")
    return logical


def validate_lock(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise LockContractError(f"lock file is missing or not regular: {path}")
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise LockContractError("lock file cannot be read as UTF-8") from error
    lines = _logical_lines(text)
    if not lines:
        raise LockContractError("lock file has no dependency entries")

    names: set[str] = set()
    hashes: set[str] = set()
    for index, line in enumerate(lines, 1):
        tokens = line.split()
        match = PIN.fullmatch(tokens[0])
        if match is None:
            raise LockContractError(f"entry {index} is not a supported exact name==version pin")
        name = re.sub(r"[-_.]+", "-", match.group(1)).lower()
        if name in names:
            raise LockContractError(f"duplicate locked project: {name}")
        names.add(name)
        if len(tokens) < 2:
            raise LockContractError(f"entry {index} has no sha256 hash")
        for token in tokens[1:]:
            hash_match = HASH.fullmatch(token)
            if hash_match is None:
                raise LockContractError(f"entry {index} contains an unsupported token or hash")
            hashes.add(hash_match.group(1))

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
    try:
        result = validate_lock(args.lock)
    except LockContractError as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 2
    print(
        f"PASS entries={result['entries']} projects={result['projects']} "
        f"unique_sha256_hashes={result['unique_sha256_hashes']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
