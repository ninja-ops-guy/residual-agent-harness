import unittest

from residual.control_plane.amendments import AmendmentClassifier, DEFAULT_RULES
from residual.control_plane.environment import EnvironmentRecord, EnvironmentRegistry
from residual.control_plane.models import AmendmentClass, AmendmentDelta, AtomicEffect, IntentState
from residual.control_plane.transactions import SideEffectTransaction, TransactionCoordinator


class GovernanceTests(unittest.TestCase):
    def test_every_default_amendment_rule(self):
        classifier = AmendmentClassifier()
        for delta_type, expected in DEFAULT_RULES.items():
            with self.subTest(delta_type=delta_type):
                self.assertEqual(classifier.classify_delta(AmendmentDelta(delta_type)), expected)

    def test_compound_amendment_uses_max_class(self):
        classifier = AmendmentClassifier()
        deltas = (
            AmendmentDelta("clarification"),
            AmendmentDelta("budget.increase"),
            AmendmentDelta("authority.side_effect_add"),
        )
        self.assertEqual(classifier.classify(deltas), AmendmentClass.AUTHORITY)

    def test_risk_override_and_bounds(self):
        classifier = AmendmentClassifier()
        self.assertEqual(classifier.classify_delta(AmendmentDelta("custom", risk_score=4)), AmendmentClass.TRUST_BOUNDARY)
        with self.assertRaises(ValueError):
            classifier.classify_delta(AmendmentDelta("custom", risk_score=5))

    def test_unknown_delta_fails_closed(self):
        with self.assertRaises(ValueError):
            AmendmentClassifier().classify_delta(AmendmentDelta("unknown.delta"))

    def test_attestation_reasons(self):
        registry = EnvironmentRegistry()
        ok, fp, reason = registry.attest("missing", lambda _: {})
        self.assertFalse(ok); self.assertIsNone(fp); self.assertEqual(reason, "worker_not_registered")
        registry.register(EnvironmentRecord("w", {"model": "m"}, "r1"))
        ok, fp, reason = registry.attest("w", lambda _: (_ for _ in ()).throw(RuntimeError("boom")))
        self.assertFalse(ok); self.assertIsNone(fp); self.assertTrue(reason.startswith("attestor_error:"))
        ok, fp, reason = registry.attest("w", lambda _: {"model": "other"})
        self.assertFalse(ok); self.assertEqual(reason, "fingerprint_mismatch")
        ok, fp, reason = registry.attest("w", lambda _: {"model": "m"})
        self.assertTrue(ok); self.assertEqual(reason, "attested")

    def test_receipt_binds_policy_hash(self):
        tx = SideEffectTransaction("t", {"a": AtomicEffect("a", "i")}, policy_hash="policy-123")
        receipt = TransactionCoordinator(lambda _: "applied", lambda _: "failed").run(tx)
        self.assertEqual(receipt.policy_hash, "policy-123")
        self.assertEqual(receipt.effect_states, (("a", IntentState.APPLIED.value),))

    def test_unrecognized_dispatch_outcome_is_reconciled(self):
        tx = SideEffectTransaction("t", {"a": AtomicEffect("a", "i")}, policy_hash="p")
        receipt = TransactionCoordinator(lambda _: None, lambda _: "applied").run(tx)
        self.assertEqual(receipt.effect_states, (("a", IntentState.APPLIED.value),))
        self.assertTrue(any(ref.startswith("ambiguous:a:") for ref in receipt.evidence_refs))


if __name__ == "__main__":
    unittest.main()
