"""Adapters from Residual execution evidence into reliability observations.

These adapters do not run models, change accepted state, or infer correctness from
worker self-reports. They translate already-recorded controller/independent-grader
outcomes into the normalized Experimental Release 1 observation schema.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ..core import digest, strict_json
from .reliability import TrialObservation


class EvidenceAdapterError(ValueError):
    """Source evidence is incomplete, contradictory, or unsupported."""


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise EvidenceAdapterError(f"missing evidence file: {path.name}")
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = strict_json(line)
        if not isinstance(value, dict):
            raise EvidenceAdapterError(f"{path.name}:{number} must contain an object")
        rows.append(value)
    return rows


def study_observations(
    run_dir: str | Path,
    *,
    mode_map: Mapping[str, str] | None = None,
    degradation_level: str = "nominal",
) -> tuple[TrialObservation, ...]:
    """Translate a frozen Study run directory into reliability observations.

    Semantics are deliberately strict:
    * accepted := controller_success
    * independently_correct := independent grader pass
    * incomplete/error/not-run rows remain scheduled failures (not silently dropped)
    * worker_correct remains UNKNOWN because Study does not expose a separately graded
      pre-acceptance worker candidate for every policy.
    """
    root = Path(run_dir)
    protocol_path = root / "protocol.json"
    if not protocol_path.exists():
        raise EvidenceAdapterError("study protocol.json is required")
    protocol = strict_json(protocol_path.read_text(encoding="utf-8"))
    if not isinstance(protocol, dict) or protocol.get("schema_version") != "residual.study-protocol.v1":
        raise EvidenceAdapterError("unsupported study protocol")
    modes = protocol.get("modes")
    if not isinstance(modes, list) or not all(isinstance(x, str) and x for x in modes):
        raise EvidenceAdapterError("study protocol modes are invalid")

    mapping = dict(mode_map or {})
    unknown = set(mapping) - set(modes)
    if unknown:
        raise EvidenceAdapterError(f"mode_map contains modes absent from protocol: {sorted(unknown)}")

    rows = _jsonl(root / "runs.jsonl")
    scheduled = protocol.get("cases", [])
    family_by_case = {
        item.get("id"): item.get("family")
        for item in scheduled
        if isinstance(item, dict)
    }
    expected_count = len(scheduled) * int(protocol.get("repeats", 0)) * len(modes)
    if len(rows) != expected_count:
        raise EvidenceAdapterError(
            f"study run evidence is incomplete: expected {expected_count} rows, found {len(rows)}"
        )

    observations: list[TrialObservation] = []
    seen: set[tuple[str, int, str]] = set()
    for row in rows:
        case_id = row.get("case_id")
        mode = row.get("mode")
        repeat = row.get("repeat")
        family = row.get("family") or family_by_case.get(case_id)
        if not isinstance(case_id, str) or not isinstance(mode, str) or not isinstance(family, str):
            raise EvidenceAdapterError("study row identity is incomplete")
        if type(repeat) is not int or repeat < 0:
            raise EvidenceAdapterError("study repeat must be a non-negative integer")
        key = (case_id, repeat, mode)
        if key in seen:
            raise EvidenceAdapterError(f"duplicate study row: {key}")
        seen.add(key)

        status = row.get("status")
        completed = status == "completed"
        controller_success = row.get("controller_success") is True
        grade = row.get("grade") if completed else None
        if completed:
            if not isinstance(grade, dict) or type(grade.get("pass")) is not bool:
                raise EvidenceAdapterError(f"completed study row lacks independent grade: {key}")
            independent = bool(grade["pass"])
        else:
            # Scheduled failures remain failures in acceptance/task-success denominators.
            independent = False
            controller_success = False

        evidence_payload = {
            "protocol_sha256": protocol.get("sha256"),
            "run_id": row.get("run_id"),
            "result_sha256": row.get("result_sha256"),
            "status": status,
        }
        observations.append(TrialObservation(
            case_id=case_id,
            family=family,
            trial=repeat + 1,
            configuration=mapping.get(mode, mode),
            accepted=controller_success,
            independently_correct=independent,
            worker_correct=None,
            degradation_level=degradation_level,
            cost_usd=None,
            latency_ms=float(row["elapsed_ms"]) if type(row.get("elapsed_ms")) in (int, float) else None,
            evidence_hash=digest(evidence_payload),
        ))
    return tuple(observations)


def external_market_observations(
    report: Mapping[str, Any],
    *,
    configuration: str = "verified_compute_market",
    family: str = "external_assurance",
    degradation_level: str = "nominal",
) -> tuple[TrialObservation, ...]:
    """Translate market-selected evaluation rows from external assurance evidence.

    The external runner's market path emits one selected result per evaluation case,
    so selection is treated as acceptance. This adapter intentionally does not invent
    fixed-engine per-case observations when the upstream report only contains aggregate
    fixed-engine statistics.
    """
    if report.get("schema_version") != "residual.external-evidence.v2":
        raise EvidenceAdapterError("unsupported external evidence report")
    rows = report.get("evaluation_rows")
    if not isinstance(rows, list):
        raise EvidenceAdapterError("external evidence evaluation_rows are required")
    report_hash = report.get("sha256")
    observations: list[TrialObservation] = []
    seen: set[tuple[str, int]] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise EvidenceAdapterError("external evaluation row must be an object")
        case_id, trial = row.get("case_id"), row.get("trial")
        if not isinstance(case_id, str) or type(trial) is not int or trial < 1:
            raise EvidenceAdapterError("external evaluation row identity is invalid")
        key = (case_id, trial)
        if key in seen:
            raise EvidenceAdapterError(f"duplicate external evaluation row: {key}")
        seen.add(key)
        if type(row.get("passed")) is not bool:
            raise EvidenceAdapterError("external evaluation row passed must be boolean")
        evidence_hash = digest({
            "report_sha256": report_hash,
            "trial": trial,
            "case_id": case_id,
            "engine_id": row.get("engine_id"),
        })
        observations.append(TrialObservation(
            case_id=case_id,
            family=family,
            trial=trial,
            configuration=configuration,
            accepted=True,
            independently_correct=bool(row["passed"]),
            worker_correct=bool(row["passed"]),
            degradation_level=degradation_level,
            cost_usd=None,
            latency_ms=float(row["latency_ms"]) if type(row.get("latency_ms")) in (int, float) else None,
            evidence_hash=evidence_hash,
        ))
    return tuple(observations)


def factory_result_observation(
    result: Any,
    *,
    case_id: str,
    family: str,
    trial: int,
    configuration: str,
    independently_correct: bool,
    accepted: bool,
    degradation_level: str = "nominal",
    fault_injected: bool = False,
    fault_contained: bool | None = None,
    cost_usd: float | None = None,
    latency_ms: float | None = None,
) -> TrialObservation:
    """Bind an externally graded Factory RuntimeResult to one observation.

    Factory intentionally produces quarantined candidates rather than acceptance
    decisions, so callers MUST supply the independent grade and final acceptance
    decision. The adapter refuses to infer either from RuntimeResult.status.
    """
    required = ("attempt_id", "status", "contract_hash", "execution_plan_hash")
    if any(not hasattr(result, name) for name in required):
        raise EvidenceAdapterError("invalid Factory RuntimeResult")
    evidence_hash = digest({
        "attempt_id": result.attempt_id,
        "status": result.status,
        "contract_hash": result.contract_hash,
        "execution_plan_hash": result.execution_plan_hash,
        "candidate": result.candidate.to_dict() if getattr(result, "candidate", None) is not None else None,
        "reason": getattr(result, "reason", None),
    })
    return TrialObservation(
        case_id=case_id,
        family=family,
        trial=trial,
        configuration=configuration,
        accepted=accepted,
        independently_correct=independently_correct,
        worker_correct=None,
        fault_injected=fault_injected,
        fault_contained=fault_contained,
        degradation_level=degradation_level,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        evidence_hash=evidence_hash,
    )
