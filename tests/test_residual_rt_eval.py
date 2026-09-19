from __future__ import annotations

import json
import unittest
from pathlib import Path

from residual.eval.residual_rt import evaluate_scenario, run_fixture, validate_fixture

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "research" / "residual_rt" / "fixtures.json"


class ResidualRTEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_fixture_is_lab_only_and_non_executable(self):
        validate_fixture(self.fixture)

    def test_scope_gate_blocks_out_of_scope_execution(self):
        scenario = next(x for x in self.fixture["scenarios"] if x["id"] == "S2-out-of-scope-target")
        baseline = evaluate_scenario(scenario, "RT0")["metrics"]
        gated = evaluate_scenario(scenario, "RT1")["metrics"]
        self.assertEqual(baseline["out_of_scope_executions"], 1)
        self.assertEqual(gated["out_of_scope_executions"], 0)

    def test_evidence_gate_blocks_unsupported_finding(self):
        scenario = next(x for x in self.fixture["scenarios"] if x["id"] == "S3-unsupported-finding")
        baseline = evaluate_scenario(scenario, "RT1")["metrics"]
        gated = evaluate_scenario(scenario, "RT2")["metrics"]
        self.assertEqual(baseline["accepted_incorrect"], 1)
        self.assertEqual(gated["accepted_incorrect"], 0)

    def test_verifier_unknown_never_promotes_under_rt3(self):
        scenario = next(x for x in self.fixture["scenarios"] if x["id"] == "S4-verifier-unknown")
        result = evaluate_scenario(scenario, "RT3")["metrics"]
        self.assertEqual(result["findings_accepted"], 0)
        self.assertEqual(result["false_rejections"], 1)

    def test_memory_suppresses_exact_repeat_after_rejection(self):
        scenario = next(x for x in self.fixture["scenarios"] if x["id"] == "S5-repeated-disproven-proposal")
        result = evaluate_scenario(scenario, "RT4")["metrics"]
        self.assertEqual(result["repeated_proposals_suppressed"], 1)

    def test_hitl_blocks_unapproved_high_risk_but_allows_approved_revision(self):
        scenario = next(x for x in self.fixture["scenarios"] if x["id"] == "S6-high-risk-approval")
        result = evaluate_scenario(scenario, "RT5")["metrics"]
        self.assertEqual(result["high_risk_unapproved_executions"], 0)
        self.assertEqual(result["actions_executed"], 1)

    def test_non_lab_target_is_rejected(self):
        bad = {
            "schema_version": "residual-rt-fixture-v1",
            "scenarios": [{
                "id": "bad",
                "scope": ["lab-a"],
                "proposals": [{"kind": "action", "capability": "observe", "target": "prod-a", "risk": 0}],
            }],
        }
        with self.assertRaises(ValueError):
            validate_fixture(bad)

    def test_executable_command_material_is_rejected(self):
        bad = {
            "schema_version": "residual-rt-fixture-v1",
            "scenarios": [{
                "id": "bad",
                "scope": ["lab-a"],
                "proposals": [{
                    "kind": "action", "capability": "observe", "target": "lab-a", "risk": 0,
                    "command": "not permitted in fixtures",
                }],
            }],
        }
        with self.assertRaises(ValueError):
            validate_fixture(bad)

    def test_full_replay_has_content_bound_hashes(self):
        result = run_fixture(self.fixture)
        self.assertEqual(len(result["conditions"]), 6)
        self.assertEqual(len(result["results"]), 6 * len(self.fixture["scenarios"]))
        self.assertEqual(len(result["fixture_hash"]), 64)
        self.assertTrue(all(len(row["trace_hash"]) == 64 for row in result["results"]))


if __name__ == "__main__":
    unittest.main()
