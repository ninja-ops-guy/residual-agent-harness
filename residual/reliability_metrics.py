"""Paper-facing reliability metrics derived from frozen study artifacts.

The study runner intentionally preserves its historical ``success`` semantics:
``controller_success and independent_grade_pass``.  This module separates the
quantities needed by the reliability-from-unreliable-computation paper without
changing those run receipts.

No metric in this module grants verification authority.  It only summarizes
independently graded study rows that have already passed the study report's
integrity checks.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .core import ContractError, digest, strict_json


SCHEMA_VERSION = "residual.reliability-metrics.v1"


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _grade_pass(row: dict[str, Any]) -> bool:
    """Independent candidate correctness, deliberately separate from acceptance."""
    return bool(row.get("status") == "completed" and isinstance(row.get("grade"), dict)
                and row["grade"].get("pass") is True)


def summarize_reliability(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Return acceptance/correctness metrics for one comparable row group.

    Definitions:
      candidate correctness: independent grader passes the final candidate;
      accepted: controller_success is true;
      accepted correctness: accepted and independently correct;
      false acceptance: accepted and independently incorrect.

    AER and FAR are intentionally both emitted because the paper uses both names;
    under the current binary acceptance model they have the same numerator and
    denominator.  ``accepted_correctness`` is 1-AER when at least one result was
    accepted.
    """
    rows = list(rows)
    scheduled = len(rows)
    completed = sum(r.get("status") == "completed" for r in rows)
    accepted = sum(bool(r.get("controller_success")) for r in rows)
    independently_correct = sum(_grade_pass(r) for r in rows)
    accepted_correct = sum(bool(r.get("controller_success")) and _grade_pass(r) for r in rows)
    false_acceptances = sum(bool(r.get("controller_success")) and not _grade_pass(r) for r in rows)

    # System-level success keeps the existing study semantics: only accepted,
    # independently-correct work counts as successful output.
    accepted_system_successes = accepted_correct

    return {
        "scheduled": scheduled,
        "completed": completed,
        "accepted": accepted,
        "independently_correct_candidates": independently_correct,
        "accepted_correct": accepted_correct,
        "false_acceptances": false_acceptances,
        "coverage": _ratio(accepted, scheduled),                         # P(A)
        "candidate_correctness_completed": _ratio(independently_correct, completed),  # P(X) among emitted candidates
        "candidate_correctness_scheduled": _ratio(independently_correct, scheduled),
        "accepted_correctness": _ratio(accepted_correct, accepted),      # P(X|A)
        "accepted_error_rate": _ratio(false_acceptances, accepted),      # AER
        "false_acceptance_rate": _ratio(false_acceptances, accepted),    # FAR (same in binary model)
        "independent_success_rate": _ratio(independently_correct, scheduled),
        "accepted_system_success_rate": _ratio(accepted_system_successes, scheduled),
        "abstained_or_rejected": scheduled - accepted,
        "aer_far_equivalent_under_binary_acceptance": True,
    }


def fault_containment_metrics(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Summarize explicitly labelled fault-injection trials only.

    Normal failures are not retroactively treated as injected faults.  A row is a
    fault trial only when ``fault_injected`` is true.  ``fault_contained`` must be
    recorded by the injection harness; absence remains unknown rather than being
    inferred from controller rejection.
    """
    trials = [r for r in rows if r.get("fault_injected") is True]
    labelled = [r for r in trials if isinstance(r.get("fault_contained"), bool)]
    contained = sum(r["fault_contained"] for r in labelled)
    escaped_incorrect = sum(
        bool(r.get("controller_success")) and not _grade_pass(r)
        for r in trials
    )
    return {
        "known_fault_trials": len(trials),
        "containment_labelled_trials": len(labelled),
        "contained_faults": contained,
        "incorrect_faults_crossing_acceptance_boundary": escaped_incorrect,
        "failure_containment_rate": _ratio(contained, len(labelled)),
        "fcr_complete": bool(trials) and len(labelled) == len(trials),
        "note": ("FCR is undefined until fault-injection rows carry explicit fault_contained labels."
                 if not labelled else "FCR uses only explicitly labelled fault-injection trials."),
    }


def orchestration_tax_proxy(mode_summary: dict[str, Any]) -> dict[str, Any]:
    """Expose existing host-overhead timing as a proxy, not a stronger claim.

    The current study report already subtracts provider, verifier, solver and
    independent-grader time from wall-clock time.  That remainder includes some
    orchestration work but is not yet decomposed into planning/scheduling/context
    packaging/integration.  Keep the distinction explicit for publication.
    """
    value = mode_summary.get("other_host_elapsed_ms")
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        value = None
    return {
        "host_overhead_proxy_ms": value,
        "exact_orchestration_tax_available": False,
        "missing_components": ["planning", "scheduling", "context_packaging", "integration"],
        "note": "Host overhead is a broad proxy only; do not publish it as exact orchestration tax.",
    }


def derive_reliability_report(study_report: dict[str, Any]) -> dict[str, Any]:
    if study_report.get("schema_version") != "residual.study-report.v1":
        raise ContractError("unsupported study report schema")
    if not isinstance(study_report.get("runs"), list) or not isinstance(study_report.get("summary"), list):
        raise ContractError("study report lacks runs or summary")

    rows = study_report["runs"]
    by_mode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("mode"), str):
            raise ContractError("invalid study run row")
        by_mode[row["mode"]].append(row)

    summaries = {s.get("mode"): s for s in study_report["summary"] if isinstance(s, dict) and isinstance(s.get("mode"), str)}
    modes = {}
    for mode, group in sorted(by_mode.items()):
        modes[mode] = {
            "reliability": summarize_reliability(group),
            "fault_containment": fault_containment_metrics(group),
            "orchestration_tax": orchestration_tax_proxy(summaries.get(mode, {})),
        }

    result = {
        "schema_version": SCHEMA_VERSION,
        "source_report_sha256": study_report.get("sha256"),
        "simulation": bool(study_report.get("simulation")),
        "evidence_level": study_report.get("evidence_level"),
        "split": study_report.get("split"),
        "overall": {
            "reliability": summarize_reliability(rows),
            "fault_containment": fault_containment_metrics(rows),
        },
        "modes": modes,
        "publication_notes": [
            "P(X) is estimated from independent grader outcomes, not controller self-reports.",
            "P(X|A) uses only controller-accepted outputs and the independent grader.",
            "AER and FAR are numerically identical under the current binary acceptance definition.",
            "FCR is not inferred from ordinary failures; it requires explicit fault-injection labels.",
            "Exact orchestration tax is not yet instrumented; other_host_elapsed_ms is only a broad proxy.",
            "Simulation/fixture results remain development evidence and must not be presented as live-model confirmation.",
        ],
    }
    result["sha256"] = digest(result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Derive paper-ready reliability metrics from a RESIDUAL study report")
    parser.add_argument("report", help="path to residual.study-report.v1 JSON")
    parser.add_argument("--output", help="optional output JSON path")
    args = parser.parse_args(argv)
    try:
        source = strict_json(Path(args.report).read_text(encoding="utf-8"))
        result = derive_reliability_report(source)
        text = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        return 0
    except (ContractError, OSError, ValueError, TypeError, KeyError):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
