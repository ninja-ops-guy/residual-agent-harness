"""Test battery: retry_escalate_abort verifier."""
from __future__ import annotations

import unittest

from research.slm.verifiers import MalformedOutput, Verdict
from research.slm.verifiers.retry_escalate_abort import RetryEscalateAbortVerifier

V = RetryEscalateAbortVerifier()


def make_item(**over):
    item = {
        "item_id": "rea-001",
        "category": "retry_escalate_abort",
        "verifier_ref": V.VERIFIER_ID,
        "input_state": {
            "policy": {
                "max_retries": 3,
                "retry_on": ["transient_timeout"],
                "escalate_on": ["safety_violation"],
                "escalate_when_retry_exhausted": True,
                "authority_required": ["retry_task"],
            },
            "state": {
                "attempts": 1,
                "failure_class": "transient_timeout",
                "authority_granted": ["retry_task"],
                "capability_ok": True,
            },
        },
        "expected_output": {"action": "retry", "reason_code": "POLICY_RETRY"},
    }
    item.update(over)
    return item


class TestRetryEscalateAbort(unittest.TestCase):
    def test_correct_answer_passes(self):
        result = V.verify(
            make_item(), {"action": "retry", "reason_code": "POLICY_RETRY"}
        )
        self.assertEqual(result.verdict, Verdict.PASS)

    def test_incorrect_answer_fails(self):
        result = V.verify(
            make_item(), {"action": "abort", "reason_code": "POLICY_RETRY"}
        )
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "WRONG_ACTION")

    def test_malformed_output_fails(self):
        result = V.verify(make_item(), MalformedOutput("retry plz"))
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "MALFORMED_OUTPUT")

    def test_unauthorized_retry_escalates(self):
        # retry without required authority -> policy forces escalation
        item = make_item()
        item["input_state"]["state"]["authority_granted"] = []
        item["expected_output"] = {
            "action": "escalate",
            "reason_code": "AUTHORITY_INSUFFICIENT",
        }
        bad = V.verify(item, {"action": "retry", "reason_code": "POLICY_RETRY"})
        self.assertEqual(bad.verdict, Verdict.FAIL)
        self.assertEqual(bad.reason_code, "WRONG_ACTION")
        good = V.verify(
            item, {"action": "escalate", "reason_code": "AUTHORITY_INSUFFICIENT"}
        )
        self.assertEqual(good.verdict, Verdict.PASS)

    def test_retry_budget_exhaustion(self):
        item = make_item()
        item["input_state"]["state"]["attempts"] = 3
        item["expected_output"] = {
            "action": "escalate",
            "reason_code": "RETRY_BUDGET_EXHAUSTED",
        }
        result = V.verify(
            item, {"action": "escalate", "reason_code": "RETRY_BUDGET_EXHAUSTED"}
        )
        self.assertEqual(result.verdict, Verdict.PASS)

    def test_capability_mismatch_aborts(self):
        item = make_item()
        item["input_state"]["state"]["capability_ok"] = False
        item["expected_output"] = {"action": "abort", "reason_code": "CAPABILITY_MISMATCH"}
        result = V.verify(
            item, {"action": "abort", "reason_code": "CAPABILITY_MISMATCH"}
        )
        self.assertEqual(result.verdict, Verdict.PASS)

    def test_defect_when_frozen_action_contradicts_policy(self):
        item = make_item()
        item["expected_output"] = {"action": "abort", "reason_code": "POLICY_RETRY"}
        result = V.verify(item, {"action": "abort", "reason_code": "POLICY_RETRY"})
        self.assertEqual(result.verdict, Verdict.BENCHMARK_DEFECT)
        self.assertEqual(result.reason_code, "EXPECTED_ACTION_MISMATCH")

    def test_defect_overlapping_policy_classes(self):
        item = make_item()
        item["input_state"]["policy"]["retry_on"] = ["transient_timeout"]
        item["input_state"]["policy"]["escalate_on"] = ["transient_timeout"]
        result = V.verify(
            item, {"action": "retry", "reason_code": "POLICY_RETRY"}
        )
        self.assertEqual(result.verdict, Verdict.BENCHMARK_DEFECT)
        self.assertEqual(result.reason_code, "DEFECT_POLICY_OVERLAP")


if __name__ == "__main__":
    unittest.main()
