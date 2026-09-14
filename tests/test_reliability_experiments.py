import unittest
from pathlib import Path

from residual.config import build_harness, load_config
from residual.core import ContractError
from residual.reliability_experiments import (
    DEFERRED_FAULT_KINDS,
    FAULT_KINDS,
    FaultSpec,
    OrchestrationTimingProbe,
    run_fault_trial,
    run_timed,
)
from residual.study import load_suite
from residual.study_tasks import grade


ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_config(ROOT / "examples/study-fixture.toml")


class ReliabilityExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cases = load_suite(ROOT / "examples/study/suite.json")
        # joint-choice is independently successful in the existing study fixtures;
        # using it here isolates the injected fault from intentional false-accept
        # cases such as the contract-stress expression fixtures.
        cls.task, cls.grader = next((task, grader) for entry, task, grader in cases if entry["id"] == "joint-choice")

    def harness(self, mode="full_cloud"):
        return build_harness(CONFIG, mode=mode, disable_cache=True)

    def independent_grade(self, values):
        return bool(grade(values, self.grader)["pass"])

    def trial(self, kind, fault_id=None):
        return run_fault_trial(
            self.harness(), self.task,
            FaultSpec(fault_id or kind + "-001", kind, "expert"),
            self.independent_grade,
        )

    def assert_contained_detected(self, receipt, layer):
        self.assertTrue(receipt["fault_injected"])
        self.assertTrue(receipt["injection_observed"])
        self.assertTrue(receipt["fault_detected"])
        self.assertTrue(receipt["fault_contained"])
        self.assertFalse(receipt["incorrect_fault_crossed_acceptance_boundary"])
        self.assertEqual(receipt["expected_containment_layer"], layer)
        self.assertIn("sha256", receipt)

    def test_timing_probe_measures_real_boundaries_without_mutating_result(self):
        result, timing = run_timed(self.harness(), self.task)
        self.assertEqual(result["schema_version"], "residual.run.v1")
        self.assertEqual(timing["schema_version"], "residual.orchestration-timing.v1")
        self.assertGreaterEqual(timing["dispatch_scheduling_ms"], 0)
        self.assertGreaterEqual(timing["context_packaging_and_planning_ms"], 0)
        self.assertGreaterEqual(timing["integration_ms"], 0)
        self.assertAlmostEqual(timing["measured_orchestration_ms"],
            timing["dispatch_scheduling_ms"] + timing["context_packaging_and_planning_ms"] + timing["integration_ms"])
        self.assertFalse(timing["planning_context_split_available"])
        self.assertEqual(timing["task_id"], self.task.id)
        self.assertIn("sha256", timing)

    def test_probe_cannot_be_installed_twice(self):
        probe = OrchestrationTimingProbe(self.harness()).install()
        with self.assertRaises(ContractError):
            probe.install()

    def test_malformed_reply_is_explicit_detected_contained_fault_trial(self):
        self.assert_contained_detected(self.trial("malformed_reply", "malformed-001"),
                                       "schema/contract boundary")

    def test_provider_error_is_detected_even_if_retry_recovers(self):
        self.assert_contained_detected(self.trial("provider_error", "provider-001"),
                                       "provider/runtime boundary")

    def test_worker_abstention_is_labelled_separately_from_containment(self):
        receipt = self.trial("worker_abstain", "abstain-001")
        self.assert_contained_detected(receipt, "worker/controller boundary")
        self.assertEqual(receipt["fault_kind"], "worker_abstain")

    def test_worker_termination_is_detected_and_contained(self):
        self.assert_contained_detected(self.trial("worker_termination"),
                                       "worker/runtime boundary")

    def test_out_of_scope_update_is_rejected_by_protocol_boundary(self):
        self.assert_contained_detected(self.trial("invalid_scope_update"),
                                       "obligation-scope boundary")

    def test_undeclared_evidence_request_is_denied(self):
        self.assert_contained_detected(self.trial("undeclared_evidence_request"),
                                       "evidence-scope boundary")

    def test_oversized_evidence_request_is_denied(self):
        self.assert_contained_detected(self.trial("oversized_evidence_request"),
                                       "evidence-window boundary")

    def test_resource_exhaustion_is_blocked_before_provider_io(self):
        receipt = self.trial("resource_exhaustion")
        self.assert_contained_detected(receipt, "resource-budget boundary")
        # This fault is injected in wire_size; the provider should never need to
        # generate the oversized request in order for the real budget gate to fire.
        self.assertFalse(receipt["controller_accepted"])

    def test_fault_catalog_separates_executable_and_deferred_runtime_faults(self):
        self.assertEqual(len(FAULT_KINDS), 9)
        self.assertIn("forbidden_tool_invocation", DEFERRED_FAULT_KINDS)
        self.assertIn("receipt_tamper", DEFERRED_FAULT_KINDS)
        self.assertIn("integration_conflict", DEFERRED_FAULT_KINDS)
        self.assertTrue(set(FAULT_KINDS).isdisjoint(DEFERRED_FAULT_KINDS))

    def test_invalid_fault_spec_rejected(self):
        with self.assertRaises(ContractError):
            FaultSpec("bad", "imaginary")
        with self.assertRaises(ContractError):
            FaultSpec("bad", "provider_error", "other")
        # Deferred faults are not accepted by the classic Harness experiment
        # runner; this prevents a paper receipt from claiming an injection that
        # did not exercise an implemented containment mechanism.
        with self.assertRaises(ContractError):
            FaultSpec("bad", "forbidden_filesystem_write")


if __name__ == "__main__":
    unittest.main()
