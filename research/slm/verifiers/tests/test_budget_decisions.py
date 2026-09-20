"""Test battery: budget_decisions verifier."""
from __future__ import annotations

import unittest

from research.slm.verifiers import MalformedOutput, Verdict
from research.slm.verifiers.budget_decisions import BudgetDecisionsVerifier

V = BudgetDecisionsVerifier()


def make_item(**over):
    item = {
        "item_id": "bd-001",
        "category": "budget_decisions",
        "verifier_ref": V.VERIFIER_ID,
        "input_state": {
            "budget": {
                "total_usd": 10.0,
                "spent_usd": 4.0,
                "safety_reserve_usd": 1.0,
                "mission_critical": False,
            },
            "routes": [
                {"route_id": "cheap", "cost_usd": 2.0},
                {"route_id": "boundary", "cost_usd": 5.0},   # == spendable
                {"route_id": "pricey", "cost_usd": 9.0},
            ],
        },
        # spendable = 10-4-1 = 5; non-critical => cost < 5 strictly
        "expected_output": {"decision": "cheap", "feasible_routes": ["cheap"]},
    }
    item.update(over)
    return item


class TestBudgetDecisions(unittest.TestCase):
    def test_correct_answer_passes(self):
        result = V.verify(make_item(), {"decision": "cheap"})
        self.assertEqual(result.verdict, Verdict.PASS)

    def test_incorrect_answer_fails(self):
        result = V.verify(make_item(), {"decision": "pricey"})
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "BUDGET_EXCEEDED")

    def test_malformed_output_fails(self):
        result = V.verify(make_item(), MalformedOutput(None))
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "MALFORMED_OUTPUT")

    def test_safety_reserve_violation_fails(self):
        # boundary route costs exactly the spendable amount; non-critical
        # policy forbids consuming the whole slack down to the reserve
        result = V.verify(make_item(), {"decision": "boundary"})
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "BUDGET_EXCEEDED")

    def test_mission_critical_allows_zero_slack(self):
        item = make_item()
        item["input_state"]["budget"]["mission_critical"] = True
        item["expected_output"] = {
            "decision": "boundary",
            "feasible_routes": ["cheap", "boundary"],
        }
        result = V.verify(item, {"decision": "boundary"})
        self.assertEqual(result.verdict, Verdict.PASS)

    def test_defect_when_frozen_feasible_set_wrong(self):
        item = make_item()
        item["expected_output"] = {
            "decision": "cheap",
            "feasible_routes": ["cheap", "pricey"],
        }
        result = V.verify(item, {"decision": "cheap"})
        self.assertEqual(result.verdict, Verdict.BENCHMARK_DEFECT)
        self.assertEqual(result.reason_code, "EXPECTED_SET_MISMATCH")

    def test_defect_when_expected_decision_infeasible(self):
        item = make_item()
        item["expected_output"] = {"decision": "pricey", "feasible_routes": ["cheap"]}
        result = V.verify(item, {"decision": "pricey"})
        self.assertEqual(result.verdict, Verdict.BENCHMARK_DEFECT)
        self.assertEqual(result.reason_code, "DEFECT_DECISION_INFEASIBLE")

    def test_unnecessary_abort_fails(self):
        result = V.verify(make_item(), {"decision": "abort"})
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "UNNECESSARY_ABORT")


if __name__ == "__main__":
    unittest.main()
