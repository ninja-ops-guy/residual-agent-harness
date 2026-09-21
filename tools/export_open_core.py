#!/usr/bin/env python3
"""Export the explicitly licensed RESIDUAL Open Core as a source archive."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "open-source" / "open-source-manifest.json"
ALWAYS = [
    "LICENSES/Apache-2.0.txt",
    "NOTICE",
    "LICENSING.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs/open-source/OPEN_SOURCE_MANIFEST.md",
    "docs/open-source/open-source-manifest.json",
    "docs/open-source/DEPENDENCY_LICENSE_REVIEW.md",
]


def iter_files(path: Path):
    if path.is_file():
        yield path
        return
    for candidate in sorted(path.rglob("*")):
        if candidate.is_file() and ".git" not in candidate.parts:
            yield candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="dist/residual-open-core.tar.gz")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    selected: dict[str, Path] = {}

    for rel in [*data["include"], *ALWAYS]:
        root = ROOT / rel
        if not root.exists():
            raise SystemExit(f"missing open-core path: {rel}")
        for src in iter_files(root):
            relative = src.relative_to(ROOT).as_posix()
            selected[relative] = src

    excluded = [p.strip("/") for p in data["exclude"]]
    leaks = [
        rel for rel in selected
        if any(rel == exc or rel.startswith(exc + "/") for exc in excluded)
    ]
    if leaks:
        raise SystemExit("reserved path leaked into open-core export: " + ", ".join(leaks[:10]))

    if args.list:
        for rel in sorted(selected):
            print(rel)
        return 0

    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:
        for rel, src in sorted(selected.items()):
            archive.add(src, arcname=f"residual-open-core/{rel}", recursive=False)

    print(f"wrote {output.relative_to(ROOT)} with {len(selected)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
