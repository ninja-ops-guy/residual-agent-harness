from __future__ import annotations

import hashlib
import json
import unittest
from dataclasses import FrozenInstanceError


class ImprovementSpecContractTests(unittest.TestCase):
    def make_spec(self):
        from residual.improvement.spec import ImprovementSpec
        return ImprovementSpec(
            improvement_id="RI-ROADMAP-001",
            observation="repair attempts consume measurable resources",
            hypothesis="bounded repair context can reduce repeated implementation failures",
            target_metrics=("task_success_rate", "repair_attempts"),
            preserve_metrics=("verification_integrity",),
            protected_invariants=("M4", "evidence_integrity", "promotion_authority"),
            acceptance={"success_rate_min": 0.9, "max_regression": 0.0},
        )

    def test_canonical_identity_and_defensive_serialization(self):
        spec = self.make_spec()
        value = spec.to_dict()
        self.assertEqual(value["target_metrics"], ["task_success_rate", "repair_attempts"])
        self.assertEqual(value["preserve_metrics"], ["verification_integrity"])
        self.assertEqual(value["protected_invariants"], ["M4", "evidence_integrity", "promotion_authority"])
        self.assertTrue(value["human_approval_required"])

        value["acceptance"]["success_rate_min"] = 0
        self.assertEqual(spec.to_dict()["acceptance"]["success_rate_min"], 0.9)

        expected = json.dumps(spec.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.assertEqual(spec.canonical_json(), expected)
        self.assertEqual(spec.sha256(), hashlib.sha256(expected.encode("utf-8")).hexdigest())
        self.assertEqual(spec.sha256(), self.make_spec().sha256())

    def test_contract_is_frozen(self):
        spec = self.make_spec()
        with self.assertRaises(FrozenInstanceError):
            spec.improvement_id = "changed"

    def test_invalid_contracts_are_rejected(self):
        from residual.improvement.spec import ImprovementSpec

        base = dict(
            improvement_id="RI-ROADMAP-001",
            observation="measured observation",
            hypothesis="falsifiable hypothesis",
            target_metrics=("target",),
            preserve_metrics=("preserve",),
            protected_invariants=("M4",),
            acceptance={"minimum": 1},
        )
        cases = [
            {**base, "improvement_id": " "},
            {**base, "observation": "\t"},
            {**base, "hypothesis": ""},
            {**base, "target_metrics": ()},
            {**base, "preserve_metrics": ()},
            {**base, "protected_invariants": ()},
            {**base, "target_metrics": ("ok", " ")},
            {**base, "preserve_metrics": (" ",)},
            {**base, "protected_invariants": ("M4", "")},
            {**base, "acceptance": {}},
            {**base, "human_approval_required": False},
        ]
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    ImprovementSpec(**case)


if __name__ == "__main__":
    unittest.main()
