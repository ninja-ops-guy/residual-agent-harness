import unittest

from residual.core import ContractError
from residual.reliability_experiment_report import build_experiment_report, summarize_fault_trials, summarize_timings


def receipt(fid, kind, detected, contained, escaped, timing):
    return {
        "schema_version": "residual.fault-trial.v1",
        "fault_injected": True,
        "injection_observed": True,
        "fault_id": fid,
        "fault_kind": kind,
        "fault_detected": detected,
        "fault_contained": contained,
        "incorrect_fault_crossed_acceptance_boundary": escaped,
        "timing": {
            "schema_version": "residual.orchestration-timing.v1",
            "dispatch_scheduling_ms": timing[0],
            "context_packaging_and_planning_ms": timing[1],
            "integration_ms": timing[2],
            "measured_orchestration_ms": sum(timing),
            "planning_context_split_available": False,
        },
    }


class ReliabilityExperimentReportTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            receipt("a", "malformed_reply", True, True, False, (1, 2, 3)),
            receipt("b", "malformed_reply", True, False, True, (2, 4, 6)),
            receipt("c", "provider_error", False, True, False, (3, 6, 9)),
        ]

    def test_fault_summary_keeps_detection_and_containment_separate(self):
        summary = summarize_fault_trials(self.rows)
        self.assertEqual(summary["trials"], 3)
        self.assertEqual(summary["detected"], 2)
        self.assertEqual(summary["contained"], 2)
        self.assertEqual(summary["escaped_incorrect"], 1)
        self.assertEqual(summary["failure_containment_rate"], 2 / 3)
        self.assertEqual(summary["by_fault_kind"]["malformed_reply"]["failure_containment_rate"], .5)

    def test_timing_summary_uses_direct_components(self):
        summary = summarize_timings(self.rows)
        self.assertEqual(summary["dispatch_scheduling_ms"]["median"], 2)
        self.assertEqual(summary["context_packaging_and_planning_ms"]["total"], 12)
        self.assertEqual(summary["integration_ms"]["median"], 6)
        self.assertFalse(summary["planning_context_split_available"])

    def test_report_is_hash_bound_and_declares_coverage(self):
        report = build_experiment_report(self.rows)
        self.assertEqual(report["schema_version"], "residual.reliability-experiment-report.v1")
        self.assertIn("sha256", report)
        self.assertEqual(report["fault_containment"]["trials"], 3)
        self.assertEqual(report["fault_catalog"]["executable_count"], 9)
        self.assertIn("resource_exhaustion", report["fault_catalog"]["executable"])
        self.assertIn("forbidden_filesystem_write", report["fault_catalog"]["deferred_runtime_required"])

    def test_invalid_receipts_fail_closed(self):
        bad = dict(self.rows[0])
        bad.pop("fault_contained")
        with self.assertRaises(ContractError):
            summarize_fault_trials([bad])
        unobserved = dict(self.rows[0])
        unobserved["injection_observed"] = False
        with self.assertRaises(ContractError):
            summarize_fault_trials([unobserved])
        unknown = dict(self.rows[0])
        unknown["fault_kind"] = "imaginary"
        with self.assertRaises(ContractError):
            summarize_fault_trials([unknown])
        bad_timing = dict(self.rows[0]["timing"])
        bad_timing["integration_ms"] = float("nan")
        with self.assertRaises(ContractError):
            summarize_timings([bad_timing])


if __name__ == "__main__":
    unittest.main()
