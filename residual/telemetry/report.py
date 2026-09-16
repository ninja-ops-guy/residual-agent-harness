"""Reliability report generation (OBS-R4, OBS-R5, OBS-R6, OBS-R7).

Reports recompute every aggregate from raw observations alone. Incomplete
or corrupt evidence causes the whole report build to be rejected — partial
aggregates over broken evidence are never emitted. Every aggregate carries
evidence-completeness and missing-data counts alongside it.
"""
from __future__ import annotations

from .schema import (
    ALL_KINDS,
    ALL_PHASES,
    EvidenceError,
    REPORT_SCHEMA_VERSION,
    hash_object,
    hash_observations,
    validate_observation,
)
from .metric_families import _tracked_optional


def _aggregate_with_evidence(value, complete: int, missing: int) -> dict:
    """Attach evidence completeness + missing-data counts to an aggregate."""
    total = complete + missing
    return {
        "value": value,
        "evidence": {
            "complete_observations": complete,
            "observations_with_missing_fields": missing,
            "completeness": (complete / total) if total else 1.0,
        },
    }


def build_reliability_report(observations, *, experiment_id: str = "fixture",
                             source_identity: dict | None = None) -> dict:
    """Recompute all paper-facing aggregates from raw observations alone.

    Raises EvidenceError if any observation is incomplete or corrupt (OBS-R4).
    Deterministic: identical inputs produce identical report_hash (Gate C).
    """
    if not isinstance(observations, (list, tuple)) or not observations:
        raise EvidenceError("observation set must be a non-empty sequence")
    validated = [validate_observation(o) for o in observations]

    # Evidence accounting (OBS-R6): per kind, complete vs missing-field counts.
    evidence_by_kind = {k: {"complete": 0, "missing": 0} for k in ALL_KINDS}
    for obs in validated:
        kind = obs["kind"]
        missing_fields = [f for f in _tracked_optional(kind) if f not in obs]
        if missing_fields:
            evidence_by_kind[kind]["missing"] += 1
        else:
            evidence_by_kind[kind]["complete"] += 1

    def ev(kind):
        return evidence_by_kind[kind]["complete"], evidence_by_kind[kind]["missing"]

    # --- execution family ---
    executions = [o for o in validated if o["kind"] == "execution"]
    exec_outcomes = {}
    for o in executions:
        exec_outcomes[o["outcome"]] = exec_outcomes.get(o["outcome"], 0) + 1

    # --- acceptance / rejection ---
    acceptances = [o for o in validated if o["kind"] == "acceptance"]
    rejections = [o for o in validated if o["kind"] == "rejection"]
    n_decisions = len(acceptances) + len(rejections)
    acceptance_rate = (len(acceptances) / n_decisions) if n_decisions else None
    rejection_rate = (len(rejections) / n_decisions) if n_decisions else None

    # P(X): independent correctness, tracked separately from acceptance (EVAL-R5).
    correct_labeled = [o for o in executions + acceptances if "correct" in o]
    n_correct = sum(1 for o in correct_labeled if o["correct"] is True)
    p_x = (n_correct / len(correct_labeled)) if correct_labeled else None
    # P(X|A): correctness among accepted.
    accepted_labeled = [o for o in acceptances if "correct" in o]
    n_acc_correct = sum(1 for o in accepted_labeled if o["correct"] is True)
    p_x_given_a = (n_acc_correct / len(accepted_labeled)) if accepted_labeled else None

    # --- verification ---
    verifications = [o for o in validated if o["kind"] == "verification"]
    verdicts = {}
    for o in verifications:
        verdicts[o["verdict"]] = verdicts.get(o["verdict"], 0) + 1

    # --- integration ---
    integrations = [o for o in validated if o["kind"] == "integration"]
    integration_results = {}
    for o in integrations:
        integration_results[o["result"]] = integration_results.get(o["result"], 0) + 1

    # --- conflicts / retries / resource ---
    conflicts = [o for o in validated if o["kind"] == "conflict"]
    retries = [o for o in validated if o["kind"] == "retry"]
    retry_attempts = sum(o["attempt"] for o in retries)
    resources = [o for o in validated if o["kind"] == "resource"]
    resource_totals = {}
    for o in resources:
        resource_totals[o["resource"]] = resource_totals.get(o["resource"], 0.0) + o["amount"]

    # --- orchestration timing: separate per phase (OBS-R5) ---
    timings = [o for o in validated if o["kind"] == "orchestration_timing"]
    phase_stats = {}
    for phase in ALL_PHASES:
        samples = sorted(o["seconds"] for o in timings if o["phase"] == phase)
        phase_stats[phase] = {
            "count": len(samples),
            "total_seconds": sum(samples),
            "mean_seconds": (sum(samples) / len(samples)) if samples else None,
            "max_seconds": samples[-1] if samples else None,
        }
    # Timing observations carry no tracked optional fields; evidence for the
    # timing aggregate is based on phase coverage (phases with zero samples
    # are missing data).
    phases_present = sum(1 for p in ALL_PHASES if phase_stats[p]["count"] > 0)
    timing_missing = len(ALL_PHASES) - phases_present

    # Overall missing-data counts across the whole observation set.
    total_complete = sum(v["complete"] for v in evidence_by_kind.values())
    total_missing = sum(v["missing"] for v in evidence_by_kind.values())

    report_body = {
        "experiment_id": experiment_id,
        "source_identity": dict(source_identity or {}),
        "observation_count": len(validated),
        "observation_hash": hash_observations(validated),
        "aggregates": {
            "execution": _aggregate_with_evidence(
                {"total": len(executions), "by_outcome": exec_outcomes}, *ev("execution")),
            "acceptance": _aggregate_with_evidence(
                {"accepted": len(acceptances), "rejected": len(rejections),
                 "decisions": n_decisions,
                 "acceptance_rate": acceptance_rate,
                 "rejection_rate": rejection_rate},
                *ev("acceptance")),
            "rejection": _aggregate_with_evidence(
                {"total": len(rejections),
                 "by_reason": _counts(o["reason"] for o in rejections)},
                *ev("rejection")),
            "correctness": _aggregate_with_evidence(
                {"labeled": len(correct_labeled), "correct": n_correct, "p_x": p_x,
                 "p_x_given_acceptance": p_x_given_a},
                *ev("execution")),
            "verification": _aggregate_with_evidence(
                {"total": len(verifications), "by_verdict": verdicts},
                *ev("verification")),
            "integration": _aggregate_with_evidence(
                {"total": len(integrations), "by_result": integration_results},
                *ev("integration")),
            "conflicts": _aggregate_with_evidence(
                {"total": len(conflicts),
                 "by_kind": _counts(o["conflict_kind"] for o in conflicts)},
                *ev("conflict")),
            "retries": _aggregate_with_evidence(
                {"total": len(retries), "total_attempts": retry_attempts},
                *ev("retry")),
            "resource_consumption": _aggregate_with_evidence(
                {"totals": resource_totals}, *ev("resource")),
            "orchestration_timing": {
                "phases": phase_stats,
                "evidence": {
                    "phases_observed": phases_present,
                    "phases_missing": timing_missing,
                    "completeness": phases_present / len(ALL_PHASES),
                },
            },
        },
        "evidence_completeness": {
            "by_kind": {k: dict(v) for k, v in evidence_by_kind.items()},
            "complete_observations": total_complete,
            "observations_with_missing_fields": total_missing,
            "missing_data_counts": {
                "observations": total_missing,
                "timing_phases": timing_missing,
            },
        },
    }
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_hash": hash_object(report_body),
        "report": report_body,
    }


def _counts(items) -> dict:
    out = {}
    for item in sorted(items):
        out[item] = out.get(item, 0) + 1
    return out
