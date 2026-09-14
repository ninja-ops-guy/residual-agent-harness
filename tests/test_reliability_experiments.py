import unittest
from pathlib import Path

from residual.config import build_harness, load_config
from residual.core import ContractError
from residual.reliability_experiments import FaultSpec, OrchestrationTimingProbe, run_fault_trial, run_timed
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
        receipt = run_fault_trial(self.harness(), self.task,
            FaultSpec("malformed-001", "malformed_reply", "expert"), self.independent_grade)
        self.assertTrue(receipt["fault_injected"])
        self.assertTrue(receipt["injection_observed"])
        self.assertTrue(receipt["fault_detected"])
        self.assertTrue(receipt["fault_contained"])
        self.assertFalse(receipt["incorrect_fault_crossed_acceptance_boundary"])
        self.assertEqual(receipt["expected_containment_layer"], "schema/contract boundary")
        self.assertIn("sha256", receipt)

    def test_provider_error_is_detected_even_if_retry_recovers(self):
        receipt = run_fault_trial(self.harness(), self.task,
            FaultSpec("provider-001", "provider_error", "expert"), self.independent_grade)
        self.assertTrue(receipt["injection_observed"])
        self.assertTrue(receipt["fault_detected"])
        self.assertTrue(receipt["fault_contained"])
        self.assertFalse(receipt["incorrect_fault_crossed_acceptance_boundary"])

    def test_worker_abstention_is_labelled_separately_from_containment(self):
        receipt = run_fault_trial(self.harness(), self.task,
            FaultSpec("abstain-001", "worker_abstain", "expert"), self.independent_grade)
        self.assertTrue(receipt["fault_detected"])
        self.assertTrue(receipt["fault_contained"])
        self.assertEqual(receipt["fault_kind"], "worker_abstain")

    def test_invalid_fault_spec_rejected(self):
        with self.assertRaises(ContractError):
            FaultSpec("bad", "imaginary")
        with self.assertRaises(ContractError):
            FaultSpec("bad", "provider_error", "other")


if __name__ == "__main__":
    unittest.main()
