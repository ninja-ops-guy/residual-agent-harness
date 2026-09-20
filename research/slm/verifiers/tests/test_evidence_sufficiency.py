"""Test battery: evidence_sufficiency verifier."""
from __future__ import annotations

import unittest

from research.slm.verifiers import MalformedOutput, Verdict
from research.slm.verifiers.evidence_sufficiency import EvidenceSufficiencyVerifier

V = EvidenceSufficiencyVerifier()

GOOD_DIGEST = "sha256:" + "a" * 64
BAD_DIGEST = "not-a-digest"


def artifact(kind, digest=GOOD_DIGEST, provenance=None):
    return {
        "artifact_id": f"art-{kind}",
        "kind": kind,
        "digest": digest,
        "provenance": provenance if provenance is not None else {"source_class": "ax21"},
    }


def make_item(**over):
    item = {
        "item_id": "es-001",
        "category": "evidence_sufficiency",
        "verifier_ref": V.VERIFIER_ID,
        "input_state": {
            "evidence_requirements": [
                {"requirement_id": "req-test", "kind": "test_log"},
                {"requirement_id": "req-receipt", "kind": "signed_receipt"},
            ],
            "artifacts": [artifact("test_log")],
            "required_verifier_outputs": ["slm00.verifier.evidence_sufficiency"],
        },
        "expected_output": {
            "sufficient": False,
            "missing_requirements": ["req-receipt"],
        },
    }
    item.update(over)
    return item


class TestEvidenceSufficiency(unittest.TestCase):
    def test_correct_answer_passes(self):
        result = V.verify(
            make_item(),
            {
                "sufficient": False,
                "missing_requirements": ["req-receipt"],
                "verifier_outputs": ["slm00.verifier.evidence_sufficiency"],
            },
        )
        self.assertEqual(result.verdict, Verdict.PASS)

    def test_incorrect_answer_fails(self):
        result = V.verify(
            make_item(),
            {
                "sufficient": True,
                "missing_requirements": [],
                "verifier_outputs": ["slm00.verifier.evidence_sufficiency"],
            },
        )
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "WRONG_MISSING_SET")

    def test_malformed_output_fails(self):
        result = V.verify(make_item(), MalformedOutput("<xml/>"))
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "MALFORMED_OUTPUT")

    def test_missing_required_verifier_output_fails(self):
        result = V.verify(
            make_item(),
            {
                "sufficient": False,
                "missing_requirements": ["req-receipt"],
                "verifier_outputs": [],
            },
        )
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "MISSING_VERIFIER_OUTPUTS")

    def test_broken_digest_makes_artifact_unusable(self):
        item = make_item()
        item["input_state"]["artifacts"] = [
            artifact("test_log", digest=BAD_DIGEST),
            artifact("signed_receipt"),
        ]
        # now test_log evidence is invalid; receipt is usable
        item["expected_output"] = {
            "sufficient": False,
            "missing_requirements": ["req-test"],
        }
        result = V.verify(
            item,
            {
                "sufficient": False,
                "missing_requirements": ["req-test"],
                "verifier_outputs": ["slm00.verifier.evidence_sufficiency"],
            },
        )
        self.assertEqual(result.verdict, Verdict.PASS)
        # a candidate that ignores the broken digest fails
        result = V.verify(
            item,
            {
                "sufficient": True,
                "missing_requirements": [],
                "verifier_outputs": ["slm00.verifier.evidence_sufficiency"],
            },
        )
        self.assertEqual(result.verdict, Verdict.FAIL)

    def test_defect_when_frozen_set_wrong(self):
        item = make_item()
        item["expected_output"] = {"sufficient": True, "missing_requirements": []}
        result = V.verify(
            item,
            {
                "sufficient": True,
                "missing_requirements": [],
                "verifier_outputs": ["slm00.verifier.evidence_sufficiency"],
            },
        )
        self.assertEqual(result.verdict, Verdict.BENCHMARK_DEFECT)
        self.assertEqual(result.reason_code, "EXPECTED_SET_MISMATCH")

    def test_defect_duplicate_requirement(self):
        item = make_item()
        item["input_state"]["evidence_requirements"].append(
            {"requirement_id": "req-test", "kind": "test_log"}
        )
        result = V.verify(
            item,
            {
                "sufficient": False,
                "missing_requirements": ["req-receipt"],
                "verifier_outputs": ["slm00.verifier.evidence_sufficiency"],
            },
        )
        self.assertEqual(result.verdict, Verdict.BENCHMARK_DEFECT)
        self.assertEqual(result.reason_code, "DEFECT_DUPLICATE_REQUIREMENT_ID")


if __name__ == "__main__":
    unittest.main()
