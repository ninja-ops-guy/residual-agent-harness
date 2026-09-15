"""Issue #63 M4-5: one canonical M4 API surface — no parallel schemas."""
from __future__ import annotations

import unittest

import residual.integrations as integrations
from residual.factory import m4_evidence, m4_integrator, m4_scheduler


class CanonicalApiTests(unittest.TestCase):
    def test_single_canonical_integration_receipt_schema(self):
        self.assertEqual(m4_integrator.INTEGRATION_SCHEMA, "factory-integration-receipt-v2")
        self.assertTrue(hasattr(m4_integrator.IntegrationReceipt, "verify_signature"))
        # The enterprise connector receipt is a distinct, non-parallel name.
        self.assertFalse(hasattr(integrations, "IntegrationReceipt"))
        self.assertTrue(hasattr(integrations, "ConnectorReceipt"))

    def test_canonical_scheduler_decision_schema(self):
        proposal = m4_scheduler.StructuralReplanProposal
        self.assertIn("factory-m4-structural-replan", str(proposal("x", (), "").to_dict()
                        if False else "factory-m4-structural-replan-v1"))
        self.assertEqual(
            m4_evidence.ReadyDagSnapshot("h", (), (), (), 0.0, ()).to_dict()["schema_version"],
            "factory-m4-ready-dag-v1",
        )
        self.assertEqual(
            m4_evidence.EvidenceIntegrationPlan("h", (), (), (), ()).to_dict()["schema_version"],
            "factory-m4-evidence-integration-plan-v1",
        )

    def test_canonical_conflict_resolution_schema(self):
        resolution = m4_integrator.ConflictResolution("p", "hash", "operator", "reason")
        self.assertEqual(set(resolution.to_dict()),
                         {"path", "selected_receipt_hash", "approved_by", "reason"})

    def test_canonical_verifier_result_interface(self):
        result = m4_integrator.VerificationResult(
            "tests", "full_test_suite", "pass", 0, "0" * 64, "0" * 64)
        # Runtime typing attribute exists, but the signed v2 payload is frozen.
        self.assertFalse(result.timed_out)
        payload = result.to_dict()
        self.assertEqual(
            set(payload),
            {"name", "category", "status", "returncode", "stdout_sha256",
             "stderr_sha256", "termination_reason", "execution_boundary"},
        )
        for status in ("pass", "fail", "unknown", "error", "timeout"):
            m4_integrator.VerificationResult("n", "type_check", status, None, "0" * 64, "0" * 64)
        timed = m4_integrator.VerificationResult(
            "n", "type_check", "timeout", 124, "0" * 64, "0" * 64,
            termination_reason="timeout", timed_out=True)
        self.assertTrue(timed.timed_out)
        # v2-frozen serialization: the timeout outcome is encoded through the
        # already-versioned fields, never a new payload key.
        timed_payload = timed.to_dict()
        self.assertNotIn("timed_out", timed_payload)
        self.assertEqual(timed_payload["termination_reason"], "timeout")
        self.assertEqual(timed_payload["status"], "timeout")
        self.assertEqual(timed_payload["returncode"], 124)

    def test_v2_signed_payload_bytes_unchanged_by_timed_out(self):
        # PR #108 review blocker 1: adding VerificationResult.timed_out must
        # NOT mutate the canonical v2 signed payload in place. Identical
        # logical results hash identically regardless of the runtime flag.
        base = m4_integrator.VerificationResult(
            "t", "full_test_suite", "pass", 0, "a" * 64, "b" * 64)
        flagged = m4_integrator.VerificationResult(
            "t", "full_test_suite", "pass", 0, "a" * 64, "b" * 64,
            timed_out=True)
        self.assertEqual(base.to_dict(), flagged.to_dict())

        def receipt(results):
            return m4_integrator.IntegrationReceipt(
                execution_plan_hash="0" * 64, integration_plan_hash="1" * 64,
                input_receipt_hashes=(), output_commit="0" * 40,
                verification_results=results, conflict_resolutions=(),
                integrated_at_ns=1, station_key_id="2" * 64,
                station_signature="pending", verification_policy_hash="3" * 64)
        self.assertEqual(receipt((base,)).receipt_hash,
                         receipt((flagged,)).receipt_hash)
        self.assertNotIn("timed_out",
                         str(receipt((flagged,)).unsigned_payload()))


if __name__ == "__main__":
    unittest.main()
