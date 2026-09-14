from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMON_PATH = ROOT / 'benchmarks' / 'factory' / 'fb002' / 'common.py'
spec = importlib.util.spec_from_file_location('fb002_common', COMMON_PATH)
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)


class FB002Tests(unittest.TestCase):
    def test_fixture_commits_are_frozen(self):
        with tempfile.TemporaryDirectory() as td:
            inp, out = fb.create_fixture(Path(td) / 'repo', known_good=True)
            self.assertEqual(inp, fb.INPUT_COMMIT)
            self.assertEqual(out, fb.EXPECTED_OUTPUT_COMMIT)

    def test_semantically_equivalent_candidate_is_accepted(self):
        candidate = '''def retry_delay(attempt: int, base: float = 0.25, cap: float = 8.0) -> float:\n    if attempt < 0:\n        raise ValueError("negative")\n    value = base * pow(2, attempt)\n    return cap if value > cap else value\n'''
        self.assertTrue(fb.verify_candidate('retry', candidate))

    def test_wrong_candidate_is_rejected(self):
        self.assertFalse(fb.verify_candidate('config', 'def parse_bool(value: str) -> bool:\n    return True\n'))

    def test_disallowed_import_is_rejected(self):
        self.assertFalse(fb.verify_candidate('text', 'import os\ndef slugify(value: str) -> str:\n    return value\n'))

    def test_dependency_wave_and_canonical_finalization(self):
        accepted = {task: source for task, (_name, source) in fb.REFERENCE.items()}
        self.assertEqual(set(fb.DEPENDENCIES['summary']), {'text', 'config'})
        self.assertEqual(set(fb.DEPENDENCIES['banner']), {'retry', 'paths'})
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / 'repo'; fb.create_fixture(repo)
            commit, passed, total = fb.finalize(repo, accepted)
            self.assertEqual(commit, fb.EXPECTED_OUTPUT_COMMIT)
            self.assertEqual(passed, total)
            self.assertEqual(total, 7)


if __name__ == '__main__':
    unittest.main()
