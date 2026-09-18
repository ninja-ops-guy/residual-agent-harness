from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "status" / "low_priority_salvage.v1.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class LowPrioritySalvageManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_is_reference_only_and_non_qualifying(self) -> None:
        self.assertEqual(self.data["schema"], "residual.low-priority-salvage.v1")
        authority = self.data["authority"]
        self.assertTrue(authority["reference_only"])
        self.assertFalse(authority["modifies_runtime"])
        self.assertFalse(authority["modifies_m4_trust_boundary"])
        self.assertFalse(authority["modifies_shared_evidence_schema"])
        self.assertFalse(authority["produces_experimental_results"])
        self.assertFalse(authority["qualifies_release"])
        self.assertRegex(self.data["baseline_commit"], SHA40)

    def test_all_legacy_sources_are_bound_to_exact_heads(self) -> None:
        expected = {
            26: "eec2969a864a7590ddc9aa70114f4a869bf0c6ee",
            38: "b0427d7e0e4213810c019a363c181125e8a7fe11",
            46: "0fe3172a75f9dce104a4af5f3de811fd4b29dec4",
            52: "58b0a23c40cd8d0b893363a62c9bc01c501ab207",
            54: "78b711569faea75357bbe9e7ad588384a87dbc58",
            56: "793d629c483502b8d4e61e058f2e69980f583623",
            12: "63308afb174c837874b159032e80d5b96100e16d",
            17: "1294810f4f6946191bd39aed618d4113df5233dd",
            20: "2af5b2a5bb56d7690944f795448b8bf082b1a699",
            24: "0cd8c01f79b899e7bfbd8eff7decdb99dbf77f52",
        }
        records = self.data["benchmark_lineage"] + self.data["research_lineage"]
        observed = {record["pr"]: record["head"] for record in records}
        self.assertEqual(observed, expected)
        for head in observed.values():
            self.assertRegex(head, SHA40)

    def test_benchmark_fixture_families_cannot_silently_disappear(self) -> None:
        fixtures = {
            record.get("fixture_id")
            for record in self.data["benchmark_lineage"]
            if record.get("fixture_id")
        }
        self.assertEqual(fixtures, {"FB001", "FB002", "FB003", "FB004", "FB-CORPUS"})
        for record in self.data["benchmark_lineage"]:
            self.assertTrue(record["preserve"])
            self.assertTrue(record["source_files"])
            self.assertIn("disposition", record)

    def test_research_probe_inventory_is_explicit(self) -> None:
        expected = {
            12: {
                "malformed_reply", "truncated_reply", "worker_abstain", "provider_error",
                "worker_termination", "invalid_scope_update", "undeclared_evidence_request",
                "oversized_evidence_request", "resource_exhaustion",
            },
            17: {"forbidden_tool", "forbidden_filesystem_write", "raw_filesystem_syscall", "wall_clock_exhaustion"},
            20: {"receipt_signature_tamper", "artifact_store_corruption", "receipt_queue_mutation", "dependency_receipt_mismatch"},
            24: {"input_order_permutation", "missing_parent", "true_overlap_conflict", "verification_failure", "invalid_human_resolution", "integration_receipt_tamper"},
        }
        observed = {record["pr"]: set(record["probes"]) for record in self.data["research_lineage"]}
        self.assertEqual(observed, expected)

    def test_retirement_gate_requires_preservation_before_closure(self) -> None:
        gate = self.data["retirement_gate"]
        self.assertEqual(set(gate["benchmark_prs"]), {26, 38, 46, 52, 54, 56})
        self.assertEqual(set(gate["research_prs"]), {12, 17, 20, 24})
        self.assertEqual(set(gate["already_retired"]), {1, 10, 57, 83})
        self.assertIn(22, gate["already_superseded_closed"])
        self.assertIn("accepted on main", gate["rule"])


if __name__ == "__main__":
    unittest.main()
