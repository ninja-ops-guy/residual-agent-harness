#!/usr/bin/env python3
"""Fail-closed Factory ownership gate (rebuilt on post-#63-closure main).

Verifies that every protected Factory/M2/M3/M4 trust-surface path is present
at HEAD with the exact git blob SHA pinned in
``verifier/v3/factory_ownership_baseline.json``.

Fail-closed semantics: a missing or invalid manifest, a core protected path
missing from the manifest, a protected file missing from the tree, any
blob-SHA mismatch, or any git error is a FAILURE. The check never treats
unavailable evidence as "no change".

Authorized change procedure: edit protected files and the manifest in the
same reviewed commit, updating ``justification`` to name the authorizing
review/PR. Do not weaken CORE_PROTECTED to make the gate green.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "verifier" / "v3" / "factory_ownership_baseline.json"

# Minimal trust surface that the manifest MUST cover. The manifest may
# protect more (tests, status tooling), but never less than this core set.
CORE_PROTECTED = frozenset({
    "residual/factory/__init__.py",
    "residual/factory/_isolated_child.py",
    "residual/factory/_sandbox_child.py",
    "residual/factory/evidence_bus.py",
    "residual/factory/evidence_receipts.py",
    "residual/factory/m4_evidence.py",
    "residual/factory/m4_git_evidence.py",
    "residual/factory/m4_integrator.py",
    "residual/factory/m4_protocol.py",
    "residual/factory/m4_safety.py",
    "residual/factory/m4_sandbox.py",
    "residual/factory/m4_scheduler.py",
    "residual/factory/runtime.py",
    "residual/factory/runtime_journal.py",
    "residual/factory/runtime_workspace.py",
    "residual/factory/station_issuer.py",
    "residual/factory/termination_provenance.py",
    "residual/factory/worker_contract.py",
})

_SHA_HEX = frozenset("0123456789abcdef")


class OwnershipError(RuntimeError):
    """Evidence unavailable; never means the tree is unchanged."""


def _blob_sha(root: Path, path: str) -> str:
    """Return the committed blob SHA of ``path`` at HEAD, or raise."""
    try:
        result = subprocess.run(
            ["git", "--no-replace-objects", "-C", str(root),
             "rev-parse", "--verify", "--end-of-options", f"HEAD:{path}"],
            capture_output=True, text=True, errors="surrogateescape",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OwnershipError(f"git unavailable for {path}: {exc}") from exc
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-500:]
        raise OwnershipError(
            f"protected file missing or unreadable at HEAD: {path} ({detail})")
    sha = result.stdout.strip()
    if len(sha) != 40 or not set(sha) <= _SHA_HEX:
        raise OwnershipError(f"invalid blob SHA resolved for {path}: {sha!r}")
    return sha


def _load_manifest(manifest_path: Path) -> dict:
    if not manifest_path.is_file():
        raise OwnershipError(f"baseline manifest missing: {manifest_path}")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OwnershipError(
            f"baseline manifest unreadable/invalid: {exc}") from exc
    if not isinstance(data, dict):
        raise OwnershipError("baseline manifest must be a JSON object")
    files = data.get("files")
    if not isinstance(files, dict) or not files:
        raise OwnershipError(
            "baseline manifest 'files' must be a non-empty object")
    for path, sha in files.items():
        if not isinstance(path, str) or not path:
            raise OwnershipError(
                "baseline manifest contains an invalid path entry")
        if (not isinstance(sha, str) or len(sha) != 40
                or not set(sha) <= _SHA_HEX):
            raise OwnershipError(
                f"baseline manifest entry for {path} is not a valid blob SHA")
    pinned = data.get("pinned_at")
    if (not isinstance(pinned, str) or len(pinned) != 40
            or not set(pinned) <= _SHA_HEX):
        raise OwnershipError(
            "baseline manifest 'pinned_at' must be a commit SHA")
    justification = data.get("justification")
    if not isinstance(justification, str) or not justification.strip():
        raise OwnershipError(
            "baseline manifest 'justification' must name the authorizing "
            "review/PR for the current pin")
    return data


def evaluate_ownership(
    root: Path = ROOT, manifest_path: Path = MANIFEST,
) -> tuple[dict, list[str]]:
    """Compare protected paths against pinned blob SHAs. Fails closed."""
    report: dict = {
        "scope": "factory-ownership-blob-pin",
        "manifest": str(manifest_path),
        "pinned_at": None,
        "protected_files": None,
        "checked": 0,
        "mismatches": [],
    }
    failures: list[str] = []
    try:
        manifest = _load_manifest(manifest_path)
    except OwnershipError as exc:
        return report, [f"ownership baseline unavailable: {exc}"]

    files: dict = manifest["files"]
    report["pinned_at"] = manifest["pinned_at"]
    report["protected_files"] = len(files)

    missing_core = sorted(CORE_PROTECTED - files.keys())
    if missing_core:
        failures.append(
            "core protected paths missing from baseline manifest: "
            + ", ".join(missing_core))

    for path in sorted(files):
        try:
            actual = _blob_sha(root, path)
        except OwnershipError as exc:
            failures.append(str(exc))
            continue
        report["checked"] += 1
        if actual != files[path]:
            report["mismatches"].append(path)
            failures.append(
                f"protected path modified without baseline advance: {path} "
                f"(pinned {files[path]}, actual {actual})")
    return report, failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT),
                        help="repository root (default: inferred from script)")
    parser.add_argument("--manifest", default=None,
                        help="override baseline manifest path")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    manifest_path = (
        Path(args.manifest).resolve() if args.manifest
        else root / "verifier" / "v3" / "factory_ownership_baseline.json")
    report, failures = evaluate_ownership(root, manifest_path)
    report["passed"] = not failures
    print(json.dumps(report, indent=2))
    if failures:
        print("FAIL:\n - " + "\n - ".join(failures))
        return 1
    print("PASS: Factory ownership gate green (blob pins match committed HEAD)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
