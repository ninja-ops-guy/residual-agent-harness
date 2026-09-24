#!/usr/bin/env python3
"""Fail closed if the declared RESIDUAL open-core boundary is malformed."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "open-source" / "open-source-manifest.json"


def norm(value: str) -> str:
    return value.strip().strip("/")


def contains(parent: str, child: str) -> bool:
    parent = norm(parent)
    child = norm(child)
    return child == parent or child.startswith(parent + "/")


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    include = [norm(p) for p in data["include"]]
    exclude = [norm(p) for p in data["exclude"]]

    errors: list[str] = []

    for required in (data["license_file"], data["notice_file"], "LICENSING.md"):
        if not (ROOT / required).exists():
            errors.append(f"required licensing artifact missing: {required}")

    for path in include:
        if not (ROOT / path).exists():
            errors.append(f"included path does not exist: {path}")

    for path in exclude:
        if not (ROOT / path).exists():
            errors.append(f"reserved path does not exist: {path}")

    for inc in include:
        for exc in exclude:
            if contains(inc, exc) or contains(exc, inc):
                errors.append(f"open/reserved overlap: include={inc} exclude={exc}")

    if data.get("license") != "Apache-2.0":
        errors.append("unexpected open-core license identifier")

    if errors:
        print("OPEN-CORE BOUNDARY: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("OPEN-CORE BOUNDARY: PASS")
    print(f"licensed roots/files: {len(include)}")
    print(f"reserved roots: {len(exclude)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
