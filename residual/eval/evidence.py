"""Gate B: machine-readable evidence artifact with exact source identity."""
from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path

from ..core import ContractError, digest

EVIDENCE_SCHEMA = "residual.eval-evidence.v1"


def source_identity(root: Path | None = None) -> dict[str, object]:
    """Exact commit/tree identity; falls back to tree digests when git is
    unavailable (e.g. exported source tarballs in CI)."""
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    identity: dict[str, object] = {"repo_root": str(root)}
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
            text=True, check=True, timeout=30).stdout.strip()
        tree = subprocess.run(
            ["git", "rev-parse", "HEAD^{tree}"], cwd=root, capture_output=True,
            text=True, check=True, timeout=30).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, capture_output=True,
            text=True, check=True, timeout=30).stdout.strip()
        identity.update({"commit": commit, "tree": tree,
                         "worktree_dirty": bool(dirty)})
    except Exception:  # git unavailable: bind to file digests instead
        sources = {p.relative_to(root).as_posix(): digest(p.read_bytes().hex())
                   for p in sorted((root / "residual" / "eval").rglob("*.py"))}
        identity.update({"commit": None, "tree": None,
                         "eval_source_digests": sources})
    return identity


def runtime_versions() -> dict[str, object]:
    return {
        "python": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
    }


def build_evidence_artifact(report: dict[str, object], *,
                            root: Path | None = None) -> dict[str, object]:
    """Bundle exact identity + versions + frozen inputs + raw observations."""
    if report.get("schema_version") != "residual.eval-report.v1":
        raise ContractError("invalid report for evidence artifact")
    artifact = {
        "schema_version": EVIDENCE_SCHEMA,
        "source": source_identity(root),
        "runtime": runtime_versions(),
        "frozen_inputs": {
            "workload": report["workload"],
            "configurations": report["configurations"],
            "held_constants": report["held_constants"],
        },
        "evidence_level": report["evidence_level"],
        "environment": report["environment"],
        "raw_observations": report["records"],
        "results": {
            "metrics": report["metrics"],
            "recomputed_probabilities": report["recomputed_probabilities"],
            "report_sha256": report["report_sha256"],
        },
    }
    artifact["evidence_sha256"] = digest(artifact)
    return artifact


def write_evidence_artifact(artifact: dict[str, object], path: Path) -> Path:
    if artifact.get("schema_version") != EVIDENCE_SCHEMA:
        raise ContractError("invalid evidence artifact")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False, allow_nan=False) + "\n",
                    encoding="utf-8")
    return path
