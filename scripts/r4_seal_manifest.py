#!/usr/bin/env python3
"""Derive and verify seal cardinality from an authoritative SHA256SUMS.

No caller-supplied expected count is accepted. The immutable manifest is the
only cardinality source; seal metadata is independently compared with it.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


LINE = re.compile(r"^([0-9a-f]{64})  (.+)$")


class ManifestError(ValueError):
    pass


@dataclasses.dataclass(frozen=True)
class ManifestEntry:
    sha256: str
    relative_path: str


def parse_authoritative_manifest(manifest: Path) -> tuple[ManifestEntry, ...]:
    """Parse every non-empty manifest line and reject ambiguity."""
    entries: list[ManifestEntry] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        match = LINE.fullmatch(raw)
        if match is None:
            raise ManifestError(f"invalid SHA256SUMS entry at line {line_number}")
        digest, name = match.groups()
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or name in {"", "."}:
            raise ManifestError(f"unsafe manifest path at line {line_number}: {name!r}")
        if name in seen:
            raise ManifestError(f"duplicate manifest path at line {line_number}: {name!r}")
        seen.add(name)
        entries.append(ManifestEntry(digest, name))
    if not entries:
        raise ManifestError("authoritative SHA256SUMS has no valid non-empty entries")
    return tuple(entries)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_authoritative_manifest(manifest: Path) -> dict[str, object]:
    """Verify all entries and return count derived directly from the manifest."""
    manifest = manifest.resolve()
    entries = parse_authoritative_manifest(manifest)
    failures: list[str] = []
    for entry in entries:
        target = manifest.parent / entry.relative_path
        if not target.is_file() or file_sha256(target) != entry.sha256:
            failures.append(entry.relative_path)
    if failures:
        raise ManifestError("authoritative manifest verification failed: " + ", ".join(failures))
    return {
        "entry_count": len(entries),
        "entries_verified": len(entries),
        "entries_failed": 0,
        "sha256sums_sha256": file_sha256(manifest),
        "verification": "PASS",
    }


def verify_seal_cardinality(manifest: Path, seal_json: Path) -> dict[str, object]:
    """Independently recompute cardinality and reject seal metadata mismatch."""
    derived = verify_authoritative_manifest(manifest)
    seal = json.loads(seal_json.read_text(encoding="utf-8"))
    recorded = seal.get("authoritative_manifest")
    keys = ("entry_count", "entries_verified")
    if not isinstance(recorded, dict):
        recorded = seal.get("authoritative_evidence", {}).get("sha256sums_verification")
        keys = ("entries_verified",)
    if not isinstance(recorded, dict):
        raise ManifestError("seal lacks authoritative manifest metadata")
    for key in keys:
        if recorded.get(key) != derived["entry_count"]:
            raise ManifestError(
                f"seal {key} mismatch: recorded={recorded.get(key)!r} "
                f"authoritative={derived['entry_count']}"
            )
    if recorded.get("entries_failed") != 0 or recorded.get("verification") != "PASS":
        raise ManifestError("seal authoritative_manifest disposition is not PASS")
    return derived


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--seal-json", type=Path)
    args = parser.parse_args()
    result = (
        verify_seal_cardinality(args.manifest, args.seal_json)
        if args.seal_json
        else verify_authoritative_manifest(args.manifest)
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
