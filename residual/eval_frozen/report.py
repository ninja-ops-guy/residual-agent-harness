"""EVAL-R8/R9: hash-bound aggregate report, CSV/JSON, and plotting inputs."""
from __future__ import annotations

import math

from ..core import ContractError, digest
from .configs import CONFIGURATIONS, constants_agree
from .metrics import SliceMetrics, compute_slice_metrics
from .runner import RunRecord, recompute_from_records
from .workload import FrozenWorkload

REPORT_SCHEMA = "residual.eval-report.v1"


def _clean(value):
    """JSON-safe value (no NaN/Inf so digests are stable)."""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    return value


def build_report(workload: FrozenWorkload, records: list[RunRecord], *,
                 evidence_level: str = "development_fixture",
                 environment: dict[str, object] | None = None) -> dict[str, object]:
    """Aggregate all retained run records (failed/aborted included, EVAL-R8)."""
    if not records:
        raise ContractError("report requires run records")
    if not constants_agree():
        raise ContractError("configuration constants diverged across R0-R5")
    for record in records:
        if record.workload_sha256 != workload.sha256:
            raise ContractError("run record bound to a different workload hash")

    per_config: dict[str, list[RunRecord]] = {}
    for record in records:
        per_config.setdefault(record.config_id, []).append(record)

    metrics: list[dict[str, object]] = []
    for config in CONFIGURATIONS:
        rows = per_config.get(config.config_id, [])
        if not rows:
            raise ContractError(f"missing runs for configuration {config.config_id}")
        by_slice: dict[str, list[RunRecord]] = {}
        for record in rows:
            by_slice.setdefault(record.slice, []).append(record)
        for slice_name in sorted(by_slice):
            m: SliceMetrics = compute_slice_metrics(config.config_id, slice_name,
                                                    by_slice[slice_name])
            entry = _clean(m.payload())
            entry["label"] = config.label
            metrics.append(entry)

    recomputed = _clean(recompute_from_records(records))
    raw_records = [_clean(record.payload()) for record in records]
    report_body = {
        "schema_version": REPORT_SCHEMA,
        "evidence_level": evidence_level,
        "workload": {
            "name": workload.name,
            "schema_version": workload.schema_version,
            "sha256": workload.sha256,
            "seed": workload.seed,
            "slices": list(workload.slices),
        },
        "configurations": [
            {"config_id": c.config_id, "label": c.label,
             "control_layers": list(c.control_layers), "sha256": c.sha256}
            for c in CONFIGURATIONS
        ],
        "held_constants": _clean(CONFIGURATIONS[0].constants),
        "environment": _clean(environment or {}),
        "metrics": metrics,
        "recomputed_probabilities": recomputed,
        "records": raw_records,
    }
    report_body["report_sha256"] = digest(report_body)
    return report_body


CSV_COLUMNS = (
    "config_id", "slice", "runs", "PASS", "FAIL", "REJECTED", "UNKNOWN",
    "P_X", "P_A", "P_X_given_A", "aer_far", "isr", "assr",
    "acceptance_coverage", "false_rejection_rate", "fcr",
    "throughput_runs_per_sec", "latency_ms_mean", "latency_ms_p50",
    "latency_ms_p95", "rework_per_run", "conflicts_total", "conflict_rate",
    "verifier_rejection_rate", "input_tokens", "output_tokens",
    "cost_usd_total", "cost_per_accepted_correct_usd", "missing_grades",
)


def report_csv_rows(report: dict[str, object]) -> str:
    """Paper-ready CSV (EVAL-R9): one row per config x slice."""
    if report.get("schema_version") != REPORT_SCHEMA:
        raise ContractError("invalid report document")
    lines = [",".join(CSV_COLUMNS)]
    for entry in report["metrics"]:
        states = entry["state_counts"]
        row = []
        for column in CSV_COLUMNS:
            value = states.get(column, 0) if column in ("PASS", "FAIL", "REJECTED", "UNKNOWN") \
                else entry.get(column)
            row.append("" if value is None else str(value))
        lines.append(",".join(row))
    return "\n".join(lines) + "\n"


def plotting_inputs(report: dict[str, object]) -> dict[str, object]:
    """Reproducible plotting inputs (EVAL-R9); rendering is downstream."""
    if report.get("schema_version") != REPORT_SCHEMA:
        raise ContractError("invalid report document")
    reliability_vs_cost = []
    reliability_vs_latency = []
    state_distributions = []
    for entry in report["metrics"]:
        reliability_vs_cost.append({
            "config_id": entry["config_id"],
            "assr": entry["assr"],
            "cost_usd_total": entry["cost_usd_total"],
        })
        reliability_vs_latency.append({
            "config_id": entry["config_id"],
            "assr": entry["assr"],
            "latency_ms_p50": entry["latency_ms_p50"],
        })
        state_distributions.append({
            "config_id": entry["config_id"],
            "slice": entry["slice"],
            **{state: entry["state_counts"][state]
               for state in ("PASS", "FAIL", "REJECTED", "UNKNOWN")},
        })
    return {
        "schema_version": "residual.eval-plot-inputs.v1",
        "source_report_sha256": report["report_sha256"],
        "workload_sha256": report["workload"]["sha256"],
        "reliability_vs_cost": reliability_vs_cost,
        "reliability_vs_latency": reliability_vs_latency,
        "state_distributions": state_distributions,
    }
