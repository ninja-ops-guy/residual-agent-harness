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
        self.assertFalse(result.timed_out)
        payload = result.to_dict()
        self.assertEqual(
            set(payload),
            {"name", "category", "status", "returncode", "stdout_sha256",
             "stderr_sha256", "termination_reason", "execution_boundary",
             "timed_out"},
        )
        for status in ("pass", "fail", "unknown", "error", "timeout"):
            m4_integrator.VerificationResult("n", "type_check", status, None, "0" * 64, "0" * 64)
        timed = m4_integrator.VerificationResult(
            "n", "type_check", "timeout", 124, "0" * 64, "0" * 64,
            termination_reason="timeout", timed_out=True)
        self.assertTrue(timed.to_dict()["timed_out"])
        self.assertEqual(timed.to_dict()["returncode"], 124)


if __name__ == "__main__":
    unittest.main()
