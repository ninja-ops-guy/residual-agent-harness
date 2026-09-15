"""Independent engineering probes. Synthetic results are never study results."""
from argparse import Namespace
from dataclasses import replace
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from observation_layer import Observation, ObservationKind, SCHEMA_VERSION, verify_chain
from residual.core import digest
from residual.factory.evidence_receipts import StationIdentity

_path = Path(__file__).resolve().parents[1] / "scripts" / "engineering_envelope.py"
_spec = importlib.util.spec_from_file_location("engineering_envelope_tested", _path)
envelope = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(envelope)


class EngineeringEnvelopeTests(unittest.TestCase):
    def test_receipt_signature_detects_semantic_mutation(self):
        receipt, identity = envelope.make_receipt(2)
        self.assertTrue(StationIdentity.verify(receipt, identity.public_bytes()))
        changed = replace(receipt, artifacts=(replace(receipt.artifacts[0], sha256="a" * 64), receipt.artifacts[1]))
        self.assertFalse(StationIdentity.verify(changed, identity.public_bytes()))

    def test_chain_rejects_tamper_reorder_and_anchored_truncation(self):
        first = Observation("a", "test", ObservationKind.CUSTOM, 1, SCHEMA_VERSION, "GENESIS", {"n": 1})
        last = Observation("b", "test", ObservationKind.CUSTOM, 2, SCHEMA_VERSION, first.digest, {"n": 2})
        self.assertTrue(verify_chain([first, last], expected_head=last.digest, expected_count=2))
        for wrong in ([last, first], [first], [first, replace(last, payload={"n": 3})]):
            self.assertFalse(verify_chain(wrong, expected_head=last.digest, expected_count=2))

    def test_timeout_never_becomes_success_from_partial_samples(self):
        attempts = []

        def operation():
            attempts.append(1)
            if len(attempts) == 2:
                raise TimeoutError()
            return "partial"

        result = envelope.measure("test", {}, operation, repeats=3)
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(len(result["samples_ns"]), 1)
        self.assertIsNone(result["median_ns"])
        self.assertIsNone(result["result"])

    def test_size_limits_reject_bools_and_unbounded_requests(self):
        for values in ([], [True], [0], [-1], [1001]):
            with self.assertRaises(ValueError):
                envelope.validate_sizes(values, 1000, "workers")

    def test_real_m2_capture_keeps_candidate_untrusted(self):
        result = envelope.capture_case(2, 10)
        self.assertEqual(result["status"], "measured")
        self.assertEqual(result["result"]["status"], "UNTRUSTED_CANDIDATE")
        self.assertEqual(len(result["result"]["artifacts"]), 2)
        self.assertNotEqual(result["result"]["input_commit"], result["result"]["output_commit"])

    def test_unknown_costs_remain_unknown(self):
        result = envelope.cost_checks()
        self.assertAlmostEqual(result["reported_100_in_50_out_usd"], 0.0002)
        for field in ("missing_usage_usd", "estimated_usage_usd", "unsupported_cache_write_usd"):
            self.assertIsNone(result[field])

    def test_failover_attempts_reserved_before_dispatch(self):
        result = envelope.routing_accounting_probe()
        self.assertEqual(result["dispatch_order"], ["reserve:openai", "dispatch:openai", "complete:openai",
                                                    "reserve:anthropic", "dispatch:anthropic", "complete:anthropic"])
        self.assertEqual(result["attempt_numbers"], [1, 2])
        self.assertEqual(result["statuses"], ["failed", "completed"])
        self.assertTrue(result["shared_request_id"])
        self.assertEqual(result["failed_usage"], {})

    def test_report_is_hashed_and_cannot_mislabel_metadata_as_live_workers(self):
        args = Namespace(workers=[2], observations=[3], dag_nodes=[3], artifacts=[2], capture_files=[],
                         repeats=1, timeout_s=10, review_refs=False)
        with patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
            result = envelope.run(args)
        self.assertFalse(result["confirmatory"])
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["kind"], "engineering-only")
        self.assertEqual(result["report_sha256"], digest({k: v for k, v in result.items() if k != "report_sha256"}))
        self.assertTrue(all(case["status"] == "measured" for case in result["cases"]))
        scheduling = next(c for c in result["cases"] if c["mechanism"] == "scheduler_select_and_measure")
        self.assertEqual(scheduling["result"]["launched_workers"], 0)


class PinnedPRReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # These objects are not guaranteed in a shallow CI clone. Main mechanisms
        # above remain mandatory; pinned review evidence is retained separately.
        for sha in (envelope.OTX, envelope.OBS, envelope.PR81):
            try:
                envelope.git("cat-file", "-e", f"{sha}^{{commit}}")
            except subprocess.SubprocessError:
                raise unittest.SkipTest(f"read-only review object unavailable: {sha}")
        cls.otx = envelope.review_otx()
        cls.obs = envelope.review_observability()
        cls.pr81 = envelope.pr81_source_checks()

    def test_tiny_task_feedback_learns_single(self):
        self.assertEqual(self.otx["choices"][:3], ["swarm", "pair", "single"])
        self.assertTrue(self.otx["learned_single"])
        self.assertIn("synthetic", self.otx["fixture_kind"])

    def test_reproduces_pinned_controller_duplicate_delivery_defect(self):
        self.assertEqual(self.otx["duplicate_outcome_count_delta"], 1)

    def test_metrics_do_not_control_paper_report(self):
        self.assertFalse(self.obs["metrics_mutation_changes_report"])

    def test_reproduces_pinned_report_identity_and_type_defects(self):
        self.assertAlmostEqual(self.obs["reported_p_x"], 2 / 3)
        self.assertEqual(self.obs["unique_execution_p_x"], 0.5)
        self.assertEqual(self.obs["duplicate_acceptances"], 2)
        self.assertTrue(self.obs["mutable_raw_evidence_changes_report"])
        self.assertTrue(self.obs["non_boolean_correct_accepted"])

    def test_pr81_policy_binding_is_acknowledged(self):
        self.assertTrue(self.pr81["verification_policy_hash_present"])
        self.assertIn("output_commit", self.pr81["candidate_binding"])
        self.assertIn("source inspection only", self.pr81["status"])


if __name__ == "__main__":
    unittest.main()
