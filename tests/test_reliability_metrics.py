import unittest

from residual.reliability_metrics import (
    derive_reliability_report,
    fault_containment_metrics,
    orchestration_tax_proxy,
    summarize_reliability,
)


class ReliabilityMetricTests(unittest.TestCase):
    def rows(self):
        return [
            {"run_id": "a", "mode": "r4", "status": "completed", "controller_success": True,
             "success": True, "grade": {"pass": True}},
            {"run_id": "b", "mode": "r4", "status": "completed", "controller_success": True,
             "success": False, "grade": {"pass": False}},
            # Correct candidate rejected by the controller: important for separating P(X) from P(X|A).
            {"run_id": "c", "mode": "r4", "status": "completed", "controller_success": False,
             "success": False, "grade": {"pass": True}},
            {"run_id": "d", "mode": "r4", "status": "not_run_budget", "controller_success": False,
             "success": False},
        ]

    def test_separates_candidate_correctness_from_acceptance(self):
        m = summarize_reliability(self.rows())
        self.assertEqual(m["scheduled"], 4)
        self.assertEqual(m["completed"], 3)
        self.assertEqual(m["accepted"], 2)
        self.assertEqual(m["independently_correct_candidates"], 2)
        self.assertEqual(m["accepted_correct"], 1)
        self.assertEqual(m["false_acceptances"], 1)
        self.assertEqual(m["coverage"], .5)
        self.assertEqual(m["candidate_correctness_completed"], 2 / 3)
        self.assertEqual(m["candidate_correctness_scheduled"], .5)
        self.assertEqual(m["accepted_correctness"], .5)
        self.assertEqual(m["accepted_error_rate"], .5)
        self.assertEqual(m["false_acceptance_rate"], .5)
        self.assertEqual(m["independent_success_rate"], .5)
        self.assertEqual(m["accepted_system_success_rate"], .25)

    def test_zero_acceptance_does_not_become_perfect_reliability(self):
        rows = [{"status": "completed", "controller_success": False, "grade": {"pass": True}}]
        m = summarize_reliability(rows)
        self.assertIsNone(m["accepted_correctness"])
        self.assertIsNone(m["accepted_error_rate"])
        self.assertEqual(m["coverage"], 0)

    def test_fcr_requires_explicit_fault_labels(self):
        ordinary = [{"status": "completed", "controller_success": False, "grade": {"pass": False}}]
        m = fault_containment_metrics(ordinary)
        self.assertEqual(m["known_fault_trials"], 0)
        self.assertIsNone(m["failure_containment_rate"])
        self.assertFalse(m["fcr_complete"])

        faults = [
            {"fault_injected": True, "fault_contained": True, "status": "completed",
             "controller_success": False, "grade": {"pass": False}},
            {"fault_injected": True, "fault_contained": False, "status": "completed",
             "controller_success": True, "grade": {"pass": False}},
        ]
        m = fault_containment_metrics(faults)
        self.assertEqual(m["failure_containment_rate"], .5)
        self.assertEqual(m["incorrect_faults_crossing_acceptance_boundary"], 1)
        self.assertTrue(m["fcr_complete"])

    def test_orchestration_tax_is_explicitly_proxy_only(self):
        tax = orchestration_tax_proxy({"other_host_elapsed_ms": 123.0})
        self.assertEqual(tax["host_overhead_proxy_ms"], 123.0)
        self.assertFalse(tax["exact_orchestration_tax_available"])
        self.assertIn("integration", tax["missing_components"])

    def test_derives_per_mode_report(self):
        rows = self.rows()
        study = {
            "schema_version": "residual.study-report.v1",
            "sha256": "a" * 64,
            "simulation": True,
            "evidence_level": "development_fixture",
            "split": "evaluation",
            "runs": rows,
            "summary": [{"mode": "r4", "other_host_elapsed_ms": 42.0}],
        }
        report = derive_reliability_report(study)
        self.assertEqual(report["schema_version"], "residual.reliability-metrics.v1")
        self.assertIn("r4", report["modes"])
        self.assertTrue(report["simulation"])
        self.assertEqual(report["modes"]["r4"]["reliability"]["false_acceptances"], 1)
        self.assertEqual(len(report["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
