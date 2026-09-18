from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from residual.core import ContractError
from residual.discovery_metrics import (
    MetricDefinition,
    MetricDefinitionProposal,
    MetricRegistry,
    ProposalDisposition,
    admission_binding,
    load_metric_registry,
)


REGISTRY_PATH = Path(__file__).parents[1] / "residual" / "discovery_metric_registry.json"
SNAPSHOT_HASH = "0" * 64


def proposal(definition: MetricDefinition, **overrides) -> MetricDefinitionProposal:
    values = {
        "definition": definition,
        "evidence_snapshot_hash": SNAPSHOT_HASH,
        "observed_metric": "mean_wall_clock_s",
        "observed_value": 696.4382,
        "reason_existing_registry_insufficient": (
            "The inspected evidence cannot distinguish the proposed measurable axis "
            "from the currently registered aggregate."
        ),
        "preserve_invariants": ("M4", "evidence_integrity", "promotion_authority"),
        "human_approval_required": True,
    }
    values.update(overrides)
    return MetricDefinitionProposal(**values)


class DiscoveryMetricRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = load_metric_registry(REGISTRY_PATH)

    def test_seed_registry_loads_and_is_content_addressed(self):
        self.assertEqual(self.registry.revision, "m6-discovery-v1")
        self.assertEqual(len(self.registry.definitions), 11)
        self.assertRegex(self.registry.registry_sha256, r"^[0-9a-f]{64}$")
        self.assertEqual(
            self.registry.resolve("context_bytes_non_success_max").unit,
            "bytes",
        )

    def test_definition_hashes_are_stable_and_wire_verified(self):
        first = self.registry.definitions[0]
        self.assertEqual(first.to_dict()["definition_sha256"], first.definition_sha256)
        raw = json.loads(REGISTRY_PATH.read_text())
        raw["definitions"][0]["definition_sha256"] = "f" * 64
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "registry.json"
            path.write_text(json.dumps(raw))
            with self.assertRaisesRegex(ContractError, "definition hash mismatch"):
                load_metric_registry(path)

    def test_registry_rejects_duplicate_metric_id(self):
        d = self.registry.definitions[0]
        with self.assertRaisesRegex(ContractError, "duplicate metric_id"):
            MetricRegistry("duplicate-id", (d, d))

    def test_registry_rejects_exact_semantic_alias(self):
        source = self.registry.resolve("mean_wall_clock_s")
        alias = MetricDefinition(
            metric_id="wall_clock_mean_seconds",
            description="Alias that should not be accepted.",
            unit=source.unit,
            aggregation=source.aggregation,
            population=source.population,
            valid_domain=source.valid_domain,
            directionality="contextual",
            collection_method=source.collection_method,
            implementation_ref="proposed:alias",
            revision="1",
        )
        assessment = self.registry.assess_proposal(proposal(alias))
        self.assertEqual(assessment.disposition, ProposalDisposition.REJECT)
        self.assertIn("mean_wall_clock_s", assessment.similar_metric_ids)

    def test_typo_or_refinement_like_metric_is_unknown_not_pass(self):
        candidate = MetricDefinition(
            metric_id="mean_wall_clock_s_basline",
            description="Mean wall-clock duration for a deterministic baseline cohort.",
            unit="seconds",
            aggregation="arithmetic_mean(wall_clock_s)",
            population="Retained M6 runs whose bound cohort_id equals baseline-v1.",
            valid_domain="x >= 0",
            directionality="lower_is_better",
            collection_method=(
                "Filter retained runs to cohort_id == baseline-v1 and compute "
                "arithmetic_mean(wall_clock_s)."
            ),
            implementation_ref="proposed:m6.baseline_wall_clock",
            revision="1",
        )
        assessment = self.registry.assess_proposal(proposal(candidate))
        self.assertEqual(assessment.disposition, ProposalDisposition.UNKNOWN)
        self.assertIn("mean_wall_clock_s", assessment.similar_metric_ids)

    def test_ambiguous_population_is_unknown(self):
        candidate = MetricDefinition(
            metric_id="baseline_latency_s",
            description="Mean wall-clock duration during baseline operation.",
            unit="seconds",
            aggregation="arithmetic_mean(wall_clock_s)",
            population="Runs under normal operating conditions.",
            valid_domain="x >= 0",
            directionality="lower_is_better",
            collection_method="Collect wall_clock_s for the proposed baseline population.",
            implementation_ref="proposed:m6.baseline_latency",
            revision="1",
        )
        assessment = self.registry.assess_proposal(proposal(candidate))
        self.assertEqual(assessment.disposition, ProposalDisposition.UNKNOWN)
        self.assertTrue(any("ambiguous" in f for f in assessment.findings))

    def test_genuinely_new_well_defined_axis_advances_only_to_semantic_review(self):
        candidate = MetricDefinition(
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
        )
        assessment = self.registry.assess_proposal(proposal(candidate))
        self.assertEqual(assessment.disposition, ProposalDisposition.SEMANTIC_REVIEW)
        self.assertTrue(assessment.mechanically_admissible)

    def test_unregistered_observed_anomaly_is_rejected(self):
        candidate = MetricDefinition(
            metric_id="first_call_elapsed_ms_mean",
            description="Arithmetic mean elapsed duration of the first provider call.",
            unit="milliseconds",
            aggregation="arithmetic_mean(first_call_elapsed_ms)",
            population="All retained M6 self-development/shipping runs in the bound EvidenceSnapshot.",
            valid_domain="x >= 0",
            directionality="lower_is_better",
            collection_method="Arithmetic mean of retained per-run first_call_elapsed_ms.",
            implementation_ref="proposed:m6.first_call_elapsed",
            revision="1",
        )
        assessment = self.registry.assess_proposal(
            proposal(candidate, observed_metric="not_registered")
        )
        self.assertEqual(assessment.disposition, ProposalDisposition.REJECT)

    def test_snapshot_binding_requires_every_metric_registered(self):
        bound = self.registry.bind_snapshot(
            {"shipping_task_success_rate": 0.6, "mean_wall_clock_s": 696.4382}
        )
        self.assertEqual(bound["metric_registry_revision"], self.registry.revision)
        self.assertEqual(bound["metric_registry_sha256"], self.registry.registry_sha256)
        self.registry.validate_snapshot_binding(bound)
        with self.assertRaisesRegex(ContractError, "unregistered discovery metric"):
            self.registry.bind_snapshot({"invented_metric": 1.0})

    def test_snapshot_registry_hash_or_revision_mismatch_fails_closed(self):
        bound = self.registry.bind_snapshot({"shipping_task_success_rate": 0.6})
        bad_hash = dict(bound, metric_registry_sha256="1" * 64)
        with self.assertRaisesRegex(ContractError, "hash mismatch"):
            self.registry.validate_snapshot_binding(bad_hash)
        bad_revision = dict(bound, metric_registry_revision="other")
        with self.assertRaisesRegex(ContractError, "revision mismatch"):
            self.registry.validate_snapshot_binding(bad_revision)

    def test_unit_mismatch_is_rejected(self):
        self.registry.validate_observation("mean_wall_clock_s", 1.0, "seconds")
        with self.assertRaisesRegex(ContractError, "unit mismatch"):
            self.registry.validate_observation("mean_wall_clock_s", 1.0, "milliseconds")

    def test_metric_definition_requires_canonical_identifier(self):
        with self.assertRaisesRegex(ContractError, "snake_case"):
            MetricDefinition(
                metric_id="Mean Wall Clock",
                description="bad",
                unit="seconds",
                aggregation="mean",
                population="all",
                valid_domain="x >= 0",
                directionality="contextual",
                collection_method="measure",
                implementation_ref="test",
                revision="1",
            )

    def test_metric_proposal_cannot_drop_human_gate(self):
        d = MetricDefinition(
            metric_id="first_call_elapsed_ms_mean",
            description="Arithmetic mean elapsed duration of the first provider call.",
            unit="milliseconds",
            aggregation="arithmetic_mean(first_call_elapsed_ms)",
            population="All retained M6 self-development/shipping runs in the bound EvidenceSnapshot.",
            valid_domain="x >= 0",
            directionality="lower_is_better",
            collection_method="Arithmetic mean of retained per-run first_call_elapsed_ms.",
            implementation_ref="proposed:m6.first_call_elapsed",
            revision="1",
        )
        with self.assertRaisesRegex(ContractError, "human approval"):
            proposal(d, human_approval_required=False)

    def test_registry_exposes_no_mutation_surface(self):
        before = self.registry.registry_sha256
        wire = self.registry.to_dict()
        wire["definitions"][0]["description"] = "mutated copy"
        self.assertEqual(self.registry.registry_sha256, before)
        self.assertFalse(hasattr(self.registry, "register"))

    def test_receipt_binding_changes_with_registry_revision(self):
        rules = {"experiment": "M6-SPEC-007P", "admission": "metric-registry-v1"}
        a = admission_binding(
            evidence_snapshot_hash=SNAPSHOT_HASH,
            registry=self.registry,
            verifier_rules=rules,
        )
        other = MetricRegistry("m6-discovery-v2", self.registry.definitions)
        b = admission_binding(
            evidence_snapshot_hash=SNAPSHOT_HASH,
            registry=other,
            verifier_rules=rules,
        )
        self.assertNotEqual(a["cache_key"], b["cache_key"])
        self.assertNotEqual(a["verifier_revision"], b["verifier_revision"])

    def test_receipt_binding_rejects_invalid_snapshot_hash(self):
        with self.assertRaisesRegex(ContractError, "SHA-256"):
            admission_binding(
                evidence_snapshot_hash="not-a-hash",
                registry=self.registry,
                verifier_rules={"rule": "v1"},
            )


if __name__ == "__main__":
    unittest.main()
