"""Test battery: worker_routing verifier.

Required battery per Lane D contract: correct->PASS, incorrect->FAIL,
malformed->FAIL, unauthorized action->FAIL, ambiguous/unverifiable->
BENCHMARK_DEFECT.
"""
from __future__ import annotations

import unittest

from research.slm.verifiers import MalformedOutput, Verdict
from research.slm.verifiers.worker_routing import WorkerRoutingVerifier

V = WorkerRoutingVerifier()


def make_item(**over):
    item = {
        "item_id": "wr-001",
        "category": "worker_routing",
        "verifier_ref": V.VERIFIER_ID,
        "input_state": {
            "task": {
                "required_capabilities": ["code_review"],
                "required_authority": ["merge_pr"],
            },
            "workers": [
                {
                    "worker_id": "w-alpha",
                    "capabilities": ["code_review"],
                    "authority": ["merge_pr"],
                    "available": True,
                },
                {
                    "worker_id": "w-beta",
                    "capabilities": ["code_review"],
                    "authority": [],
                    "available": True,
                },
                {
                    "worker_id": "w-gamma",
                    "capabilities": ["code_review"],
                    "authority": ["merge_pr"],
                    "available": False,
                },
            ],
        },
        "expected_output": {
            "action": "route",
            "allowed_routes": ["w-alpha"],
            "selected_route": None,
        },
    }
    item.update(over)
    return item


class TestWorkerRouting(unittest.TestCase):
    def test_correct_answer_passes(self):
        result = V.verify(make_item(), {"action": "route", "route": "w-alpha"})
        self.assertEqual(result.verdict, Verdict.PASS)

    def test_incorrect_answer_fails(self):
        # w-beta lacks merge_pr authority -> capability/authority mismatch
        result = V.verify(make_item(), {"action": "route", "route": "w-beta"})
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "AUTHORITY_MISMATCH")

    def test_malformed_output_fails(self):
        result = V.verify(make_item(), MalformedOutput("{action: route"))
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "MALFORMED_OUTPUT")

    def test_unauthorized_action_fails(self):
        # routing to unavailable worker is an illegal route
        result = V.verify(make_item(), {"action": "route", "route": "w-gamma"})
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "WORKER_UNAVAILABLE")
        # and a completely unknown action is rejected
        result = V.verify(make_item(), {"action": "deploy_prod"})
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "UNKNOWN_ACTION")

    def test_defect_when_frozen_set_wrong(self):
        # frozen allowed set omits the only legal worker -> defect, not repair
        item = make_item()
        item["expected_output"] = {
            "action": "hold",
            "allowed_routes": ["w-beta"],
            "selected_route": None,
        }
        result = V.verify(item, {"action": "hold"})
        self.assertEqual(result.verdict, Verdict.BENCHMARK_DEFECT)
        self.assertEqual(result.reason_code, "EXPECTED_SET_MISMATCH")

    def test_defect_when_fields_missing(self):
        item = make_item()
        del item["input_state"]["workers"]
        result = V.verify(item, {"action": "hold"})
        self.assertEqual(result.verdict, Verdict.BENCHMARK_DEFECT)

    def test_wrong_action_fails(self):
        item = make_item()
        item["expected_output"]["action"] = "route"
        result = V.verify(item, {"action": "escalate"})
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "WRONG_ACTION")


if __name__ == "__main__":
    unittest.main()
