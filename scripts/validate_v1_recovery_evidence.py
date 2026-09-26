#!/usr/bin/env python3
"""Validate RESIDUAL v1 backup/restore/rollback qualification evidence.

This validator is intentionally stdlib-only and non-operational. It never
creates backups, restores data, changes traffic, deploys artifacts, or grants
release authority. It validates retained evidence supplied after separately
authorized exercises.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "residual.v1-recovery-evidence.v1"
RESULT_SCHEMA = "residual.v1-recovery-evidence-validation.v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT40 = re.compile(r"^[0-9a-f]{40}$")
_SECRET_TOKENS = ("secret", "password", "passwd", "token", "credential", "private_key", "api_key")


class EvidenceError(ValueError):
    pass


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError(f"{name} must be an object")
    return value


def _require_bool(obj: dict[str, Any], key: str, name: str) -> bool:
    if key not in obj or not isinstance(obj[key], bool):
        raise EvidenceError(f"{name}.{key} must be boolean")
    return obj[key]


def _require_str(obj: dict[str, Any], key: str, name: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{name}.{key} must be a non-empty string")
    return value


def _require_sha256(value: str, name: str) -> None:
    if not _SHA256.fullmatch(value):
        raise EvidenceError(f"{name} must be lowercase sha256 hex")


def _require_git40(value: str, name: str) -> None:
    if not _GIT40.fullmatch(value):
        raise EvidenceError(f"{name} must be lowercase 40-hex git identity")


def _require_utc_z(value: str, name: str) -> datetime:
    if not value.endswith("Z"):
        raise EvidenceError(f"{name} must be UTC and end in Z")
    try:
        dt = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise EvidenceError(f"{name} must be ISO-8601 UTC") from exc
    if dt.utcoffset() != timezone.utc.utcoffset(dt):
        raise EvidenceError(f"{name} must be UTC")
    return dt


def _reject_secret_bearing_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(token in lowered for token in _SECRET_TOKENS):
                if lowered not in {"key_reference"}:
                    raise EvidenceError(f"secret-bearing field forbidden: {path}.{key}")
            _reject_secret_bearing_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            _reject_secret_bearing_keys(child, f"{path}[{idx}]")


def _num(obj: dict[str, Any], key: str, name: str) -> int | float:
    value = obj.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise EvidenceError(f"{name}.{key} must be a non-negative number")
    if isinstance(value, float) and not math.isfinite(value):
        raise EvidenceError(f"{name}.{key} must be finite")
    # Preserve integers: float conversion can erase an objective breach.
    return value


def _failed(reason: str, commit: str, artifact_sha: str) -> dict[str, Any]:
    return {
        "schema": RESULT_SCHEMA,
        "status": "FAIL",
        "reason": reason,
        "execution_claim": "VALIDATION_ONLY",
        "rc_commit": commit,
        "artifact_sha256": artifact_sha,
    }


def validate_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    evidence = _require_dict(evidence, "top-level evidence")
    _reject_secret_bearing_keys(evidence)
    if evidence.get("schema") != SCHEMA:
        raise EvidenceError(f"schema must be {SCHEMA}")
    if evidence.get("execution_claim") != "OBSERVED":
        raise EvidenceError("execution_claim must be OBSERVED for qualification evidence")

    rc = _require_dict(evidence.get("rc"), "rc")
    commit = _require_str(rc, "commit", "rc")
    tree = _require_str(rc, "tree", "rc")
    artifact_sha = _require_str(rc, "artifact_sha256", "rc")
    _require_git40(commit, "rc.commit")
    _require_git40(tree, "rc.tree")
    _require_sha256(artifact_sha, "rc.artifact_sha256")

    profile = _require_dict(evidence.get("deployment_profile"), "deployment_profile")
    profile_sha = _require_str(profile, "sha256", "deployment_profile")
    _require_sha256(profile_sha, "deployment_profile.sha256")
    if not _require_bool(profile, "approved", "deployment_profile"):
        raise EvidenceError("deployment_profile.approved must be true")

    objectives = _require_dict(evidence.get("objectives"), "objectives")
    rpo_target = _num(objectives, "rpo_seconds", "objectives")
    rto_target = _num(objectives, "rto_seconds", "objectives")

    backup = _require_dict(evidence.get("backup"), "backup")
    backup_id = _require_str(backup, "backup_id", "backup")
    manifest_sha = _require_str(backup, "manifest_sha256", "backup")
    _require_sha256(manifest_sha, "backup.manifest_sha256")
    if not _require_bool(backup, "encrypted", "backup"):
        return _failed("backup is not encrypted", commit, artifact_sha)
    if not _require_bool(backup, "readable_before_traffic_change", "backup"):
        return _failed("backup readability was not proven before traffic change", commit, artifact_sha)
    _require_str(backup, "key_reference", "backup")
    backup_created = _require_utc_z(_require_str(backup, "created_at_utc", "backup"), "backup.created_at_utc")
    components = backup.get("components")
    if not isinstance(components, list) or not all(isinstance(x, str) and x for x in components):
        raise EvidenceError("backup.components must be a list of non-empty strings")
    required_components = {
        "database",
        "durable_outbox_journal",
        "evidence_receipt_store",
        "configuration_references",
    }
    missing_components = sorted(required_components - set(components))
    if missing_components:
        return _failed("backup missing required components: " + ", ".join(missing_components), commit, artifact_sha)

    restore = _require_dict(evidence.get("restore"), "restore")
    if _require_str(restore, "backup_id", "restore") != backup_id:
        return _failed("restore is not bound to the declared backup", commit, artifact_sha)
    restore_start = _require_utc_z(_require_str(restore, "started_at_utc", "restore"), "restore.started_at_utc")
    restore_done = _require_utc_z(_require_str(restore, "completed_at_utc", "restore"), "restore.completed_at_utc")
    if restore_done < restore_start or restore_start < backup_created:
        return _failed("restore timestamps are inconsistent with backup creation", commit, artifact_sha)
    for key in ("integrity_verified", "receipt_chain_verified", "startup_verified", "critical_reads_verified"):
        if not _require_bool(restore, key, "restore"):
            return _failed(f"restore.{key} is false", commit, artifact_sha)
    observed_rpo = _num(restore, "observed_rpo_seconds", "restore")
    observed_rto = _num(restore, "observed_rto_seconds", "restore")
    if observed_rpo > rpo_target:
        return _failed(f"observed RPO {observed_rpo}s exceeds target {rpo_target}s", commit, artifact_sha)
    if observed_rto > rto_target:
        return _failed(f"observed RTO {observed_rto}s exceeds target {rto_target}s", commit, artifact_sha)

    rollback = _require_dict(evidence.get("rollback"), "rollback")
    previous_artifact = _require_str(rollback, "previous_artifact_sha256", "rollback")
    _require_sha256(previous_artifact, "rollback.previous_artifact_sha256")
    if previous_artifact == artifact_sha:
        return _failed("rollback target equals RC artifact", commit, artifact_sha)
    for key in ("procedure_verified", "data_integrity_verified", "authority_integrity_verified", "in_flight_policy_verified"):
        if not _require_bool(rollback, key, "rollback"):
            return _failed(f"rollback.{key} is false", commit, artifact_sha)

    index = _require_dict(evidence.get("evidence_index"), "evidence_index")
    index_sha = _require_str(index, "sha256", "evidence_index")
    _require_sha256(index_sha, "evidence_index.sha256")
    if not _require_bool(index, "immutable_copy_verified", "evidence_index"):
        return _failed("immutable evidence copy not verified", commit, artifact_sha)

    approval = _require_dict(evidence.get("approval"), "approval")
    _require_str(approval, "qualification_lead", "approval")
    if not _require_bool(approval, "approved", "approval"):
        raise EvidenceError("approval.approved must be true")
    _require_utc_z(_require_str(approval, "approved_at_utc", "approval"), "approval.approved_at_utc")

    return {
        "schema": RESULT_SCHEMA,
        "status": "PASS",
        "reason": "recovery evidence satisfies declared v1 qualification contract",
        "execution_claim": "VALIDATION_ONLY",
        "rc_commit": commit,
        "artifact_sha256": artifact_sha,
        "deployment_profile_sha256": profile_sha,
        "backup_id": backup_id,
        "evidence_index_sha256": index_sha,
    }


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            # Do not echo an untrusted member name into retained diagnostics.
            raise EvidenceError("duplicate JSON object member in recovery evidence")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise EvidenceError("nonstandard JSON numeric constant in recovery evidence")


def _finite_json_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise EvidenceError("non-finite JSON number in recovery evidence")
    return number


def load_evidence(path: Path) -> dict[str, Any]:
    """Read one unambiguous UTF-8 JSON object without trusting parser defaults."""
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
            parse_float=_finite_json_float,
        )
    except EvidenceError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise EvidenceError("recovery evidence must be readable valid UTF-8 JSON") from exc
    return _require_dict(value, "top-level evidence")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        evidence = load_evidence(args.evidence)
        result = validate_evidence(evidence)
        code = 0 if result["status"] == "PASS" else 1
    except (OSError, json.JSONDecodeError, EvidenceError) as exc:
        result = {
            "schema": RESULT_SCHEMA,
            "status": "BLOCKED",
            "reason": str(exc),
            "execution_claim": "VALIDATION_ONLY",
        }
        code = 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
