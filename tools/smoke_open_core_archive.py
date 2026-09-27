#!/usr/bin/env python3
"""Smoke-test an exported RESIDUAL Open Core source archive in isolation."""
from __future__ import annotations

import argparse
import compileall
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile

PREFIX = PurePosixPath("residual-open-core")
IMPORTS = [
    "ai_providers.core",
    "ai_providers.registry",
    "observation_layer.core",
    "residual.core",
    "residual.goalspec",
    "residual.brakes",
    "residual.quarantine",
    "residual.verifier",
    "residual.receipts",
    "residual.extensions",
]


class SmokeError(ValueError):
    pass


def extract_regular_files(archive_path: Path, target: Path) -> Path:
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts or not name.parts or name.parts[0] != PREFIX.name:
                raise SmokeError(f"unsafe archive member: {member.name}")
            if not member.isfile():
                raise SmokeError(f"non-regular archive member: {member.name}")
            out = target.joinpath(*name.parts)
            out.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise SmokeError(f"unreadable archive member: {member.name}")
            out.write_bytes(source.read())
    return target / PREFIX.name


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    args = parser.parse_args()
    archive = Path(args.archive).resolve()
    if not archive.is_file():
        print("OPEN-CORE SMOKE: FAIL: archive not found", file=sys.stderr)
        return 1

    try:
        with tempfile.TemporaryDirectory(prefix="residual-open-core-smoke-") as td:
            root = extract_regular_files(archive, Path(td))
            if not compileall.compile_dir(root, quiet=1, force=True):
                raise SmokeError("compileall failed")

            code = "\n".join(f"import {name}" for name in IMPORTS)
            env = os.environ.copy()
            env["PYTHONPATH"] = str(root)
            proc = subprocess.run(
                [sys.executable, "-I", "-c", code],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            # -I intentionally ignores PYTHONPATH, so repeat with a controlled sys.path injection.
            if proc.returncode:
                controlled = "import sys; sys.path.insert(0, " + repr(str(root)) + "); " + "; ".join(
                    f"import {name}" for name in IMPORTS
                )
                proc = subprocess.run(
                    [sys.executable, "-I", "-c", controlled],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            if proc.returncode:
                raise SmokeError((proc.stderr or proc.stdout).strip() or "isolated import failed")

            print("OPEN-CORE SMOKE: PASS")
            print(f"imports checked: {len(IMPORTS)}")
            return 0
    except (OSError, SmokeError, subprocess.TimeoutExpired, tarfile.TarError) as error:
        print(f"OPEN-CORE SMOKE: FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
