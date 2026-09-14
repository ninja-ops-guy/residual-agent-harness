from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from residual.experiments.adapters import (
    EvidenceAdapterError,
    external_market_observations,
    study_observations,
)


class ReliabilityAdapterTests(unittest.TestCase):
    def _study_dir(self) -> Path:
        root = Path(tempfile.mkdtemp())
        protocol = {
            "schema_version": "residual.study-protocol.v1",
            "sha256": "protocol-hash",
            "modes": ["rawish", "residual"],
            "repeats": 1,
            "cases": [{"id": "c1", "family": "repair"}],
        }
        (root / "protocol.json").write_text(json.dumps(protocol), encoding="utf-8")
        rows = [
            {
                "run_id": "r1", "case_id": "c1", "family": "repair", "repeat": 0,
                "mode": "rawish", "status": "completed", "controller_success": True,
                "success": False, "grade": {"pass": False}, "elapsed_ms": 10,
                "result_sha256": "a",
            },
            {
                "run_id": "r2", "case_id": "c1", "family": "repair", "repeat": 0,
                "mode": "residual", "status": "completed", "controller_success": False,
                "success": False, "grade": {"pass": True}, "elapsed_ms": 20,
                "result_sha256": "b",
            },
        ]
        (root / "runs.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        return root

    def test_study_maps_controller_acceptance_and_independent_grade(self):
        observations = study_observations(
            self._study_dir(), mode_map={"rawish": "raw", "residual": "covd"}
        )
        self.assertEqual(len(observations), 2)
        raw, covd = observations
        self.assertEqual(raw.configuration, "raw")
        self.assertTrue(raw.accepted)
        self.assertFalse(raw.independently_correct)
        self.assertIsNone(raw.worker_correct)
        self.assertEqual(covd.configuration, "covd")
        self.assertFalse(covd.accepted)
        self.assertTrue(covd.independently_correct)

    def test_study_refuses_incomplete_evidence_set(self):
        root = self._study_dir()
        rows = (root / "runs.jsonl").read_text(encoding="utf-8").splitlines()
        (root / "runs.jsonl").write_text(rows[0] + "\n", encoding="utf-8")
        with self.assertRaises(EvidenceAdapterError):
            study_observations(root)

    def test_external_market_rows_are_accepted_selected_outputs(self):
        report = {
            "schema_version": "residual.external-evidence.v2",
            "sha256": "report-hash",
            "evaluation_rows": [
                {"trial": 1, "case_id": "e1", "engine_id": "x@1", "passed": False,
                 "latency_ms": 42, "token_usage": 5},
                {"trial": 2, "case_id": "e1", "engine_id": "x@1", "passed": True,
                 "latency_ms": 44, "token_usage": 6},
            ],
        }
        observations = external_market_observations(report)
        self.assertEqual(len(observations), 2)
        self.assertTrue(all(item.accepted for item in observations))
        self.assertFalse(observations[0].independently_correct)
        self.assertTrue(observations[1].independently_correct)

    def test_external_refuses_duplicate_case_trial(self):
        row = {"trial": 1, "case_id": "e1", "engine_id": "x@1", "passed": True,
               "latency_ms": 1, "token_usage": 1}
        report = {
            "schema_version": "residual.external-evidence.v2",
            "sha256": "report-hash",
            "evaluation_rows": [row, dict(row)],
        }
        with self.assertRaises(EvidenceAdapterError):
            external_market_observations(report)


if __name__ == "__main__":
    unittest.main()
