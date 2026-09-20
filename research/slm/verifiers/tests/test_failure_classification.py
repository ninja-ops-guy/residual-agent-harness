"""Test battery: failure_classification verifier."""
from __future__ import annotations

import unittest

from research.slm.verifiers import MalformedOutput, Verdict
from research.slm.verifiers.failure_classification import FailureClassificationVerifier

V = FailureClassificationVerifier()


def make_item(**over):
    item = {
        "item_id": "fc-001",
        "category": "failure_classification",
        "verifier_ref": V.VERIFIER_ID,
        "input_state": {
            "taxonomy": [
                "transient_timeout",
                "capability_mismatch",
                "authority_denied",
                "contract_violation",
            ],
            "aliases": {"timeout": "transient_timeout"},
            "observation": {"error": "deadline exceeded after 30000ms"},
        },
        "expected_output": {"label": "transient_timeout"},
    }
    item.update(over)
    return item


class TestFailureClassification(unittest.TestCase):
    def test_correct_answer_passes(self):
        result = V.verify(make_item(), {"label": "transient_timeout"})
        self.assertEqual(result.verdict, Verdict.PASS)

    def test_preregistered_alias_passes(self):
        result = V.verify(make_item(), {"label": "timeout"})
        self.assertEqual(result.verdict, Verdict.PASS)

    def test_incorrect_answer_fails(self):
        result = V.verify(make_item(), {"label": "contract_violation"})
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "WRONG_LABEL")

    def test_malformed_output_fails(self):
        result = V.verify(make_item(), MalformedOutput("42"))
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "MALFORMED_OUTPUT")

    def test_unregistered_alias_fails(self):
        # "slow" is not in the taxonomy and was never preregistered as an
        # alias — unauthorized label invention is a hard FAIL
        result = V.verify(make_item(), {"label": "slow"})
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "UNKNOWN_LABEL")

    def test_defect_expected_label_outside_taxonomy(self):
        item = make_item()
        item["expected_output"] = {"label": "alien_label"}
        result = V.verify(item, {"label": "alien_label"})
        self.assertEqual(result.verdict, Verdict.BENCHMARK_DEFECT)
        self.assertEqual(result.reason_code, "DEFECT_EXPECTED_LABEL_NOT_IN_TAXONOMY")

    def test_defect_alias_collides_with_taxonomy(self):
        item = make_item()
        item["input_state"]["aliases"] = {"transient_timeout": "capability_mismatch"}
        result = V.verify(item, {"label": "transient_timeout"})
        self.assertEqual(result.verdict, Verdict.BENCHMARK_DEFECT)
        self.assertEqual(result.reason_code, "DEFECT_ALIAS_COLLIDES_WITH_TAXONOMY")

    def test_defect_alias_target_unknown(self):
        item = make_item()
        item["input_state"]["aliases"] = {"timeout": "does_not_exist"}
        result = V.verify(item, {"label": "timeout"})
        self.assertEqual(result.verdict, Verdict.BENCHMARK_DEFECT)
        self.assertEqual(result.reason_code, "DEFECT_ALIAS_TARGET_UNKNOWN")


if __name__ == "__main__":
    unittest.main()
