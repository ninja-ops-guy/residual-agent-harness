import json
from pathlib import Path
import unittest


CORPUS = Path(__file__).with_name("fixtures") / "r5_shared_comms_corpus.json"


class R5SharedCommsCorpusTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(CORPUS.read_text(encoding="utf-8"))

    def test_exact_requirement_and_gate_set(self):
        rows = self.corpus["requirements"]
        self.assertEqual([r["id"] for r in rows], [f"R5-SC-{i:03d}" for i in range(1, 15)])
        self.assertEqual([r["gate"] for r in rows], [f"R5-G{i:02d}" for i in range(1, 15)])

    def test_every_requirement_is_executable_oracle_complete(self):
        required = {"id", "gate", "positive", "negative", "adversarial", "invariant",
                    "evidence", "oracle", "false_positive", "false_negative"}
        for row in self.corpus["requirements"]:
            with self.subTest(requirement=row["id"]):
                self.assertEqual(set(row), required)
                for key in required - {"evidence"}:
                    self.assertIsInstance(row[key], str)
                    self.assertTrue(row[key].strip())
                self.assertGreaterEqual(len(row["evidence"]), 6)
                self.assertEqual(len(row["evidence"]), len(set(row["evidence"])))

    def test_corpus_cannot_claim_runtime_implementation_or_missing_evidence_pass(self):
        self.assertFalse(self.corpus["rules"]["runtime_behavior_implemented"])
        self.assertFalse(self.corpus["rules"]["missing_evidence_is_pass"])
        self.assertTrue(self.corpus["rules"]["oracle_requires_exact_match"])


if __name__ == "__main__":
    unittest.main()
