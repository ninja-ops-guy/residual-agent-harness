"""Aggregate controlled fault and orchestration-timing experiment receipts."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .core import ContractError, digest, strict_json
from .reliability_experiments import DEFERRED_FAULT_KINDS, FAULT_KINDS


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _percentile(values, q):
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * q
    low = int(position)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (position - low)


def summarize_fault_trials(receipts: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(receipts)
    for row in rows:
        if row.get("schema_version") != "residual.fault-trial.v1" or row.get("fault_injected") is not True:
            raise ContractError("invalid fault trial receipt")
        if row.get("injection_observed") is not True:
            raise ContractError("fault trial did not observe its scheduled injection")
        if row.get("fault_kind") not in FAULT_KINDS:
            raise ContractError("fault trial uses unsupported fault kind")
        if not isinstance(row.get("fault_contained"), bool) or not isinstance(row.get("fault_detected"), bool):
            raise ContractError("fault trial missing explicit labels")

    contained = sum(row["fault_contained"] for row in rows)
    detected = sum(row["fault_detected"] for row in rows)
    escaped = sum(bool(row.get("incorrect_fault_crossed_acceptance_boundary")) for row in rows)
    by_kind = {}
    groups = defaultdict(list)
    for row in rows:
        groups[row["fault_kind"]].append(row)
    for kind, group in sorted(groups.items()):
        by_kind[kind] = {
            "trials": len(group),
            "detected": sum(r["fault_detected"] for r in group),
            "contained": sum(r["fault_contained"] for r in group),
            "escaped_incorrect": sum(bool(r.get("incorrect_fault_crossed_acceptance_boundary")) for r in group),
            "detection_rate": _ratio(sum(r["fault_detected"] for r in group), len(group)),
            "failure_containment_rate": _ratio(sum(r["fault_contained"] for r in group), len(group)),
        }
    return {
        "trials": len(rows),
        "detected": detected,
        "contained": contained,
        "escaped_incorrect": escaped,
        "detection_rate": _ratio(detected, len(rows)),
        "failure_containment_rate": _ratio(contained, len(rows)),
        "by_fault_kind": by_kind,
    }


def summarize_timings(receipts: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(receipts)
    components = ("dispatch_scheduling_ms", "context_packaging_and_planning_ms", "integration_ms", "measured_orchestration_ms")
    values = {name: [] for name in components}
    combined_boundary = False
    for row in rows:
        timing = row.get("timing", row)
        if timing.get("schema_version") != "residual.orchestration-timing.v1":
            raise ContractError("invalid orchestration timing receipt")
        combined_boundary = combined_boundary or not bool(timing.get("planning_context_split_available"))
        for name in components:
            value = timing.get(name)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ContractError("invalid orchestration timing value")
            values[name].append(float(value))

    result = {"trials": len(rows), "planning_context_split_available": not combined_boundary}
    for name, samples in values.items():
        result[name] = {
            "median": statistics.median(samples) if samples else None,
            "p95": _percentile(samples, .95),
            "total": sum(samples),
        }
    result["note"] = ("Planning and context packaging remain a directly measured combined boundary."
                      if combined_boundary else "Planning and context packaging were measured separately.")
    return result


def build_experiment_report(fault_receipts: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(fault_receipts)
    result = {
        "schema_version": "residual.reliability-experiment-report.v1",
        "fault_catalog": {
            "executable": dict(sorted(FAULT_KINDS.items())),
            "deferred_runtime_required": dict(sorted(DEFERRED_FAULT_KINDS.items())),
            "executable_count": len(FAULT_KINDS),
            "deferred_count": len(DEFERRED_FAULT_KINDS),
        },
        "fault_containment": summarize_fault_trials(rows),
        "orchestration_timing": summarize_timings(rows),
        "claim_scope": [
            "Fault containment applies only to the explicitly injected fault kinds represented in these receipts.",
            "Detection and containment are separate outcomes; detection alone does not establish containment.",
            "Deferred fault kinds are not counted as trials and require the newer isolated worker/evidence-bus/integrator runtime.",
            "Timing data are direct measurements of instrumented boundaries, not estimates derived from residual wall time.",
            "Planning and context packaging share a boundary in the current harness and are not falsely split.",
        ],
    }
    result["sha256"] = digest(result)
    return result


def _read_jsonl(path):
    return [strict_json(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Aggregate RESIDUAL controlled reliability experiment receipts")
    parser.add_argument("receipts", help="JSONL file of residual.fault-trial.v1 receipts")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        report = build_experiment_report(_read_jsonl(args.receipts))
        text = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        return 0
    except (ContractError, OSError, ValueError, TypeError, KeyError):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
