#!/usr/bin/env python3
"""Derive and verify seal cardinality from an authoritative SHA256SUMS.

No caller-supplied expected count is accepted. The immutable manifest is the
only cardinality source; seal metadata is independently compared with it.
"""

from __future__ import annotations

import argparse
import dataclasses
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat


LINE = re.compile(r"^([0-9a-f]{64})  (.+)$")
_SECURE_OPEN = os.open in os.supports_dir_fd and all(
    hasattr(os, flag) for flag in ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK")
)


class ManifestError(ValueError):
    pass


@dataclasses.dataclass(frozen=True)
class ManifestEntry:
    sha256: str
    relative_path: str


def _parse_manifest(raw_bytes: bytes) -> tuple[ManifestEntry, ...]:
    """Parse the same manifest bytes that are bound into the result digest."""
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeError as error:
        raise ManifestError("manifest is not UTF-8") from error
    entries: list[ManifestEntry] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        match = LINE.fullmatch(raw)
        if match is None:
            raise ManifestError(f"invalid SHA256SUMS entry at line {line_number}")
        digest, name = match.groups()
        path = PurePosixPath(name)
        if (path.is_absolute() or ".." in path.parts or name in {"", "."}
                or path.as_posix() != name or "\x00" in name or "\\" in name):
            raise ManifestError(f"unsafe manifest path at line {line_number}: {name!r}")
        if name in seen:
            raise ManifestError(f"duplicate manifest path at line {line_number}: {name!r}")
        seen.add(name)
        entries.append(ManifestEntry(digest, name))
    if not entries:
        raise ManifestError("authoritative SHA256SUMS has no valid non-empty entries")
    return tuple(entries)


@contextmanager
def _package_root(path: Path):
    """Anchor the caller-selected, stable package directory once.

    Root selection is trusted. This is not a mount/hard-link isolation or a
    concurrent-content-mutation proof. Unsupported platforms fail closed.
    """
    if not _SECURE_OPEN:
        raise ManifestError("secure no-follow verification is unavailable on this platform")
    try:
        root = path.parent.resolve(strict=True)
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except (OSError, RuntimeError) as error:
        raise ManifestError("cannot open package root") from error
    try:
        yield descriptor
    finally:
        os.close(descriptor)


@contextmanager
def _regular_file(root_fd: int, name: str):
    """Walk from an anchored descriptor; never reopen a checked pathname.

    O_NOFOLLOW applies at every component, including the leaf. O_NONBLOCK
    prevents a FIFO from hanging before fstat rejects non-regular files.
    """
    parts = PurePosixPath(name).parts
    if not parts or PurePosixPath(name).is_absolute() or ".." in parts:
        raise ManifestError(f"unsafe file path: {name!r}")
    parent_fd = os.dup(root_fd)
    file_fd = None
    try:
        for part in parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                          dir_fd=parent_fd)
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise ManifestError(f"not a regular file: {name!r}")
        source = os.fdopen(file_fd, "rb")
        file_fd = None  # ownership transferred to source
        with source:
            yield source
    except (OSError, ValueError) as error:
        if isinstance(error, ManifestError):
            raise
        raise ManifestError(f"cannot read regular file without symlinks: {name!r}") from error
    finally:
        if file_fd is not None:
            os.close(file_fd)
        os.close(parent_fd)


def parse_authoritative_manifest(manifest: Path) -> tuple[ManifestEntry, ...]:
    """Parse a regular, non-symlink manifest without following its leaf."""
    with _package_root(manifest) as root_fd:
        with _regular_file(root_fd, manifest.name) as source:
            return _parse_manifest(source.read())


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with _package_root(path) as root_fd:
        with _regular_file(root_fd, path.name) as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def verify_authoritative_manifest(manifest: Path) -> dict[str, object]:
    """Verify regular, non-symlink entries below one anchored package root."""
    failures: list[str] = []
    with _package_root(manifest) as root_fd:
        with _regular_file(root_fd, manifest.name) as source:
            raw_manifest = source.read()
        entries = _parse_manifest(raw_manifest)
        for entry in entries:
            try:
                digest = hashlib.sha256()
                with _regular_file(root_fd, entry.relative_path) as source:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(block)
                if digest.hexdigest() != entry.sha256:
                    failures.append(entry.relative_path)
            except ManifestError:
                failures.append(entry.relative_path)
    if failures:
        raise ManifestError("authoritative manifest verification failed: " + ", ".join(failures))
    return {
        "entry_count": len(entries),
        "entries_verified": len(entries),
        "entries_failed": 0,
        "sha256sums_sha256": hashlib.sha256(raw_manifest).hexdigest(),
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
