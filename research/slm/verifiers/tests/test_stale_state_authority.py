"""Test battery: stale_state_authority verifier."""
from __future__ import annotations

import unittest

from research.slm.verifiers import MalformedOutput, Verdict
from research.slm.verifiers.stale_state_authority import StaleStateAuthorityVerifier

V = StaleStateAuthorityVerifier()


def make_item(**over):
    item = {
        "item_id": "ssa-001",
        "category": "stale_state_authority",
        "verifier_ref": V.VERIFIER_ID,
        "input_state": {
            "current_generation": 7,
            "receipt": {"generation": 7, "authority_scope": ["advance_task"]},
            "state_machine": {
                "current_state": "in_progress",
                "legal_transitions": ["review", "blocked"],
            },
            "protected_boundaries": ["authority.granted", "budget.total_usd"],
            "proposed_action": {
                "transition_to": "review",
                "required_authority": ["advance_task"],
                "touches": ["status"],
            },
        },
        "expected_output": {"legal": True, "violation": None},
    }
    item.update(over)
    return item


class TestStaleStateAuthority(unittest.TestCase):
    def test_correct_answer_passes(self):
        result = V.verify(make_item(), {"legal": True, "violation": None})
        self.assertEqual(result.verdict, Verdict.PASS)

    def test_incorrect_answer_fails(self):
        result = V.verify(make_item(), {"legal": False, "violation": "STALE_RECEIPT"})
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "WRONG_LEGALITY")

    def test_malformed_output_fails(self):
        result = V.verify(make_item(), MalformedOutput("null"))
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "MALFORMED_OUTPUT")

    def test_unauthorized_action_fails(self):
        # action requires authority outside the receipt's scope
        item = make_item()
        item["input_state"]["proposed_action"]["required_authority"] = [
            "advance_task",
            "merge_pr",
        ]
        item["expected_output"] = {
            "legal": False,
            "violation": "AUTHORITY_SCOPE_EXCEEDED",
        }
        good = V.verify(
            item, {"legal": False, "violation": "AUTHORITY_SCOPE_EXCEEDED"}
        )
        self.assertEqual(good.verdict, Verdict.PASS)
        bad = V.verify(item, {"legal": True, "violation": None})
        self.assertEqual(bad.verdict, Verdict.FAIL)

    def test_stale_receipt_detection(self):
        item = make_item()
        item["input_state"]["receipt"]["generation"] = 5  # stale vs current 7
        item["expected_output"] = {"legal": False, "violation": "STALE_RECEIPT"}
        result = V.verify(item, {"legal": False, "violation": "STALE_RECEIPT"})
        self.assertEqual(result.verdict, Verdict.PASS)

    def test_illegal_transition_and_protected_boundary(self):
        item = make_item()
        item["input_state"]["proposed_action"]["transition_to"] = "done"
        item["expected_output"] = {"legal": False, "violation": "ILLEGAL_TRANSITION"}
        result = V.verify(item, {"legal": False, "violation": "ILLEGAL_TRANSITION"})
        self.assertEqual(result.verdict, Verdict.PASS)

        item2 = make_item()
        item2["input_state"]["proposed_action"]["touches"] = [
            "status",
            "authority.granted",
        ]
        item2["expected_output"] = {
            "legal": False,
            "violation": "PROTECTED_BOUNDARY_TOUCHED",
        }
        result = V.verify(
            item2, {"legal": False, "violation": "PROTECTED_BOUNDARY_TOUCHED"}
        )
        self.assertEqual(result.verdict, Verdict.PASS)

    def test_defect_when_frozen_violation_wrong(self):
        item = make_item()
        item["input_state"]["receipt"]["generation"] = 5
        item["expected_output"] = {"legal": True, "violation": None}
        result = V.verify(item, {"legal": True, "violation": None})
        self.assertEqual(result.verdict, Verdict.BENCHMARK_DEFECT)
        self.assertEqual(result.reason_code, "EXPECTED_LEGAL_MISMATCH")

    def test_defect_unknown_frozen_violation_label(self):
        item = make_item()
        item["expected_output"] = {"legal": False, "violation": "COSMIC_RAY"}
        result = V.verify(item, {"legal": False, "violation": "COSMIC_RAY"})
        self.assertEqual(result.verdict, Verdict.BENCHMARK_DEFECT)
        self.assertEqual(result.reason_code, "DEFECT_UNKNOWN_VIOLATION")

    def test_violation_precedence_stale_first(self):
        # stale receipt masks a simultaneously illegal transition
        item = make_item()
        item["input_state"]["receipt"]["generation"] = 1
        item["input_state"]["proposed_action"]["transition_to"] = "done"
        item["expected_output"] = {"legal": False, "violation": "STALE_RECEIPT"}
        result = V.verify(item, {"legal": False, "violation": "STALE_RECEIPT"})
        self.assertEqual(result.verdict, Verdict.PASS)


if __name__ == "__main__":
    unittest.main()
