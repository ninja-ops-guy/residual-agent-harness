"""Test battery: contract_compilation verifier."""
from __future__ import annotations

import unittest

from research.slm.verifiers import MalformedOutput, Verdict
from research.slm.verifiers.contract_compilation import ContractCompilationVerifier

V = ContractCompilationVerifier()

REFERENCE_CONTRACT = {
    "contract_id": "c-1",
    "capabilities": ["read_repo", "open_pr"],
    "authority": ["comment"],
    "evidence": ["ev-test-log", "ev-diff"],
    "budget_usd": 2.5,
    "scope": {"repos": ["residual-agent-harness"]},
}


def make_item(**over):
    item = {
        "item_id": "cc-001",
        "category": "contract_compilation",
        "verifier_ref": V.VERIFIER_ID,
        "input_state": {
            "contract_spec": {
                "required_fields": ["contract_id", "capabilities", "budget_usd"],
                "invariants": [
                    {"kind": "max_value", "path": "budget_usd", "value": 5.0},
                    {"kind": "not_empty", "path": "capabilities"},
                ],
                "capability_boundary": ["read_repo", "open_pr", "deploy"],
                "authority_scope": ["comment", "merge"],
                "evidence_requirements": ["ev-test-log"],
                "budget": {"max_cost_usd": 5.0},
            }
        },
        "expected_output": {"contract": REFERENCE_CONTRACT},
    }
    item.update(over)
    return item


class TestContractCompilation(unittest.TestCase):
    def test_correct_answer_passes(self):
        result = V.verify(make_item(), {"contract": dict(REFERENCE_CONTRACT)})
        self.assertEqual(result.verdict, Verdict.PASS)

    def test_semantic_equivalence_passes(self):
        # key order and int/float differences are semantically equal
        shuffled = {
            "budget_usd": 2.50,
            "scope": {"repos": ["residual-agent-harness"]},
            "evidence": ["ev-test-log", "ev-diff"],
            "authority": ["comment"],
            "capabilities": ["read_repo", "open_pr"],
            "contract_id": "c-1",
        }
        result = V.verify(make_item(), {"contract": shuffled})
        self.assertEqual(result.verdict, Verdict.PASS)

    def test_incorrect_answer_fails(self):
        bad = dict(REFERENCE_CONTRACT)
        bad["budget_usd"] = 3.0
        result = V.verify(make_item(), {"contract": bad})
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "CONTRACT_MISMATCH")

    def test_malformed_output_fails(self):
        result = V.verify(make_item(), MalformedOutput("[not json"))
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "MALFORMED_OUTPUT")

    def test_unauthorized_action_fails(self):
        bad = dict(REFERENCE_CONTRACT)
        bad["authority"] = ["comment", "admin_prod"]
        result = V.verify(make_item(), {"contract": bad})
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "AUTHORITY_SCOPE_VIOLATION")
        bad2 = dict(REFERENCE_CONTRACT)
        bad2["capabilities"] = ["read_repo", "wipe_disk"]
        result = V.verify(make_item(), {"contract": bad2})
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "CAPABILITY_BOUNDARY_VIOLATION")

    def test_budget_invariant_fails(self):
        bad = dict(REFERENCE_CONTRACT)
        bad["budget_usd"] = 99.0
        result = V.verify(make_item(), {"contract": bad})
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "INVARIANT_VIOLATED")

    def test_defect_when_reference_violates_spec(self):
        item = make_item()
        ref = dict(REFERENCE_CONTRACT)
        ref["budget_usd"] = 50.0  # violates the spec's own invariant
        item["expected_output"] = {"contract": ref}
        result = V.verify(item, {"contract": ref})
        self.assertEqual(result.verdict, Verdict.BENCHMARK_DEFECT)
        self.assertTrue(result.reason_code.startswith("DEFECT_REFERENCE_"))

    def test_defect_unknown_invariant_kind(self):
        item = make_item()
        item["input_state"]["contract_spec"]["invariants"] = [
            {"kind": "vibes", "path": "budget_usd"}
        ]
        result = V.verify(item, {"contract": dict(REFERENCE_CONTRACT)})
        self.assertEqual(result.verdict, Verdict.BENCHMARK_DEFECT)
        self.assertEqual(result.reason_code, "DEFECT_UNKNOWN_INVARIANT_KIND")


if __name__ == "__main__":
    unittest.main()
