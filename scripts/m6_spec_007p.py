from __future__ import annotations

import argparse
import json
from pathlib import Path

from residual.discovery_metrics import (
    MetricDefinition,
    MetricDefinitionProposal,
    ProposalDisposition,
    load_metric_registry,
)


SNAPSHOT_HASH = "7a239febb03972fcc6e89d205cfa83276fd484e24d2e70b46b4229115addcd2a"


def wrap(definition: MetricDefinition) -> MetricDefinitionProposal:
    return MetricDefinitionProposal(
        definition=definition,
        evidence_snapshot_hash=SNAPSHOT_HASH,
        observed_metric="mean_wall_clock_s",
        observed_value=696.4382,
        reason_existing_registry_insufficient=(
            "The current registered evidence does not establish whether this proposed "
            "measurement is a distinct axis needed to resolve the wall-clock uncertainty."
        ),
        preserve_invariants=("M4", "evidence_integrity", "verification_integrity", "promotion_authority"),
        human_approval_required=True,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default="residual/discovery_metric_registry.json")
    ap.add_argument("--output", default="runs/m6-spec-007p/evidence.json")
    args = ap.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    registry = load_metric_registry(args.registry)
    cases = [
        (
            "007o_replay_typo_ambiguous_baseline",
            MetricDefinition(
                metric_id="mean_wall_clock_s_basline",
                description="Mean wall-clock duration under a proposed normal baseline.",
                unit="seconds",
                aggregation="arithmetic_mean(wall_clock_s)",
                population="Runs under normal operating conditions.",
                valid_domain="x >= 0",
                directionality="lower_is_better",
                collection_method="Collect wall_clock_s for the proposed normal baseline population.",
                implementation_ref="proposed:m6.baseline_wall_clock",
                revision="1",
            ),
            ProposalDisposition.UNKNOWN,
        ),
        (
            "exact_semantic_alias",
            MetricDefinition(
                metric_id="wall_clock_mean_seconds",
                description="Alias of the existing all-run wall-clock mean.",
                unit="seconds",
                aggregation="arithmetic_mean(wall_clock_s)",
                population="All retained M6 self-development/shipping runs in the bound EvidenceSnapshot.",
                valid_domain="x >= 0",
                directionality="contextual",
                collection_method="Arithmetic mean of retained per-run wall_clock_s.",
                implementation_ref="proposed:m6.alias",
                revision="1",
            ),
            ProposalDisposition.REJECT,
        ),
        (
            "well_defined_new_axis",
            MetricDefinition(
                metric_id="first_call_elapsed_ms_mean",
                description="Arithmetic mean elapsed duration of the first provider call.",
                unit="milliseconds",
                aggregation="arithmetic_mean(first_call_elapsed_ms)",
                population="All retained M6 self-development/shipping runs in the bound EvidenceSnapshot.",
                valid_domain="x >= 0",
                directionality="lower_is_better",
                collection_method="Arithmetic mean of retained per-run first_call_elapsed_ms.",
                implementation_ref="proposed:m6.aggregate_metrics.first_call_elapsed_ms_mean",
                revision="1",
            ),
            ProposalDisposition.SEMANTIC_REVIEW,
        ),
    ]

    results = []
    passed = True
    for case_id, definition, expected in cases:
        assessment = registry.assess_proposal(wrap(definition))
        ok = assessment.disposition == expected
        passed = passed and ok
        results.append(
            {
                "case_id": case_id,
                "definition": definition.to_dict(),
                "expected": expected.value,
                "observed": assessment.disposition.value,
                "findings": list(assessment.findings),
                "similar_metric_ids": list(assessment.similar_metric_ids),
                "pass": ok,
            }
        )

    evidence = {
        "schema_version": 1,
        "experiment": "M6-SPEC-007P",
        "purpose": "deterministic metric-identity negative/positive controls",
        "registry_revision": registry.revision,
        "registry_sha256": registry.registry_sha256,
        "source_snapshot_hash": SNAPSHOT_HASH,
        "cases": results,
        "pass": passed,
        "authority": {
            "register_metric": False,
            "implement_candidate": False,
            "promote": False,
        },
    }
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("M6_SPEC_007P_EVIDENCE=" + json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
