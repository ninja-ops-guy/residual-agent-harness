"""Tests for calibration.py (toy data only)."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import calibration


def make_records(pairs):
    return [calibration.CalibrationRecord(confidence=c, correct=ok)
            for c, ok in pairs]


class TestCalibration(unittest.TestCase):
    def test_ece_perfect_calibration(self):
        # every record at confidence 1.0 and correct -> ECE 0
        records = make_records([(1.0, True)] * 10)
        self.assertAlmostEqual(
            calibration.expected_calibration_error(records), 0.0)

    def test_ece_worst_case(self):
        records = make_records([(1.0, False)] * 10)
        self.assertAlmostEqual(
            calibration.expected_calibration_error(records), 1.0)

    def test_ece_requires_records(self):
        with self.assertRaises(ValueError):
            calibration.expected_calibration_error([])

    def test_brier(self):
        records = make_records([(0.5, True), (0.5, False)])
        self.assertAlmostEqual(calibration.brier_score(records), 0.25)

    def test_buckets_cover_unit_interval(self):
        records = make_records([(0.05, True), (0.95, False)])
        buckets = calibration.assign_buckets(records, 10)
        self.assertEqual(len(buckets), 10)
        self.assertEqual(sum(b.count for b in buckets), 2)
        self.assertEqual(buckets[0].count, 1)
        self.assertEqual(buckets[9].count, 1)

    def test_confidence_validation(self):
        with self.assertRaises(ValueError):
            calibration.CalibrationRecord(confidence=1.5, correct=True)

    def test_reliability_table_and_svg(self):
        records = make_records([(0.2, False), (0.8, True)])
        table = calibration.reliability_table(records)
        self.assertIn("mean_conf", table)
        svg = calibration.reliability_svg(records)
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("</svg>", svg)

    def test_threshold_sweep_monotone_escalation(self):
        records = [
            calibration.CalibrationRecord(0.9, True,
                                          escalation_required=False),
            calibration.CalibrationRecord(0.1, False,
                                          escalation_required=True),
        ]
        points = calibration.threshold_sweep(records, steps=10)
        self.assertEqual(len(points), 11)
        escalations = [p.escalated_fraction for p in points]
        self.assertEqual(escalations, sorted(escalations))
        # threshold 0: nothing escalated -> the required escalation is missed
        self.assertAlmostEqual(points[0].fner, 1.0)
        # threshold 1: everything escalated -> FNER 0, some UER
        self.assertAlmostEqual(points[-1].fner, 0.0)
        self.assertGreater(points[-1].uer, 0.0)

    def test_threshold_sweep_requires_labels(self):
        with self.assertRaises(ValueError):
            calibration.threshold_sweep(make_records([(0.5, True)]))

    def test_load_records_jsonl(self):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".jsonl", delete=False) as fh:
            fh.write(json.dumps({"confidence": 0.7, "correct": True}) + "\n")
            path = fh.name
        try:
            records = calibration.load_records(path)
            self.assertEqual(len(records), 1)
            self.assertTrue(records[0].correct)
        finally:
            os.unlink(path)

    def test_cli_help(self):
        with self.assertRaises(SystemExit) as ctx:
            calibration.main(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_cli_ece(self):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".jsonl", delete=False) as fh:
            fh.write(json.dumps({"confidence": 1.0, "correct": True}) + "\n")
            path = fh.name
        try:
            self.assertEqual(
                calibration.main(["--input", path, "ece"]), 0)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
