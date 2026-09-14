from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT / "benchmarks" / "factory" / "fb001" / "common.py"
spec = importlib.util.spec_from_file_location("fb001_common", COMMON)
fb001 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(fb001)


class FB001Tests(unittest.TestCase):
    def test_fixture_commits_are_frozen(self):
        with tempfile.TemporaryDirectory() as td:
            input_commit, output_commit = fb001.create_fixture(Path(td) / "repo", known_good=True)
        self.assertEqual(input_commit, fb001.INPUT_COMMIT)
        self.assertEqual(output_commit, fb001.EXPECTED_OUTPUT_COMMIT)

    def test_live_finalizer_is_canonical(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            fb001.create_fixture(repo, known_good=False)
            commit = fb001.write_policy(repo, dict(fb001.EXPECTED))
            self.assertEqual(commit, fb001.EXPECTED_OUTPUT_COMMIT)
            self.assertTrue((repo / "policy.json").is_file())

    def test_wrong_answer_cannot_finalize(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            fb001.create_fixture(repo, known_good=False)
            wrong = dict(fb001.EXPECTED)
            wrong["timeout_budget_seconds"] = 31
            with self.assertRaises(ValueError):
                fb001.write_policy(repo, wrong)

    def test_six_independent_prompts_are_bound(self):
        self.assertEqual(set(fb001.PROMPTS), set(fb001.EXPECTED))
        self.assertEqual(len(fb001.EXPECTED), 6)


if __name__ == "__main__":
    unittest.main()
