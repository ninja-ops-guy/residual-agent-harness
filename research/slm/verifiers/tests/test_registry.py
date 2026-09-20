"""Registry/interface tests shared across the verifier suite."""
from __future__ import annotations

import unittest

from research.slm.verifiers import (
    VERIFIER_REGISTRY,
    Verdict,
    get_verifier,
    verify,
)

CATEGORIES = {
    "worker_routing",
    "contract_compilation",
    "evidence_sufficiency",
    "retry_escalate_abort",
    "budget_decisions",
    "failure_classification",
    "adversarial_malformed",
    "stale_state_authority",
}


class TestRegistry(unittest.TestCase):
    def test_all_eight_categories_registered(self):
        self.assertEqual(len(VERIFIER_REGISTRY), 8)
        self.assertEqual(
            {cls.CATEGORY for cls in VERIFIER_REGISTRY.values()}, CATEGORIES
        )

    def test_ids_stable_and_namespaced(self):
        for verifier_id in VERIFIER_REGISTRY:
            self.assertTrue(verifier_id.startswith("slm00.verifier."))

    def test_get_verifier_roundtrip(self):
        for verifier_id, cls in VERIFIER_REGISTRY.items():
            self.assertIsInstance(get_verifier(verifier_id), cls)

    def test_unknown_id_raises(self):
        with self.assertRaises(KeyError):
            get_verifier("slm00.verifier.nope")

    def test_dispatch_unknown_ref_is_defect(self):
        result = verify({"verifier_ref": "slm00.verifier.nope"}, {})
        self.assertEqual(result.verdict, Verdict.BENCHMARK_DEFECT)
        self.assertEqual(result.reason_code, "UNKNOWN_VERIFIER_REF")

    def test_dispatch_missing_ref_is_defect(self):
        result = verify({}, {})
        self.assertEqual(result.verdict, Verdict.BENCHMARK_DEFECT)
        self.assertEqual(result.reason_code, "ITEM_MISSING_VERIFIER_REF")


if __name__ == "__main__":
    unittest.main()
