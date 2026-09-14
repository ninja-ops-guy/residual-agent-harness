from __future__ import annotations

import importlib.util
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMON_PATH = ROOT / 'benchmarks' / 'factory' / 'fb003' / 'common.py'
spec = importlib.util.spec_from_file_location('fb003_common', COMMON_PATH)
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)


class FB003Tests(unittest.TestCase):
    def test_fixture_commits_are_frozen(self):
        with tempfile.TemporaryDirectory() as td:
            inp, out = fb.create_fixture(Path(td) / 'repo', known_good=True)
            self.assertEqual(inp, fb.INPUT_COMMIT)
            self.assertEqual(out, fb.EXPECTED_OUTPUT_COMMIT)

    def test_exact_bounded_edit_is_accepted(self):
        baseline = deepcopy(fb.BASE_POLICY)
        candidate = deepcopy(baseline)
        candidate['timeouts']['connect'] = 3
        self.assertTrue(fb.verify_candidate('connect_timeout', fb.render_policy(candidate), baseline))

    def test_extra_shared_file_mutation_is_rejected(self):
        baseline = deepcopy(fb.BASE_POLICY)
        candidate = deepcopy(baseline)
        candidate['timeouts']['connect'] = 3
        candidate['logging']['level'] = 'DEBUG'
        self.assertFalse(fb.verify_candidate('connect_timeout', fb.render_policy(candidate), baseline))

    def test_executable_or_reflective_source_is_rejected(self):
        source = fb.render_policy(fb.BASE_POLICY) + '\nopen("/tmp/x", "w")\n'
        self.assertFalse(fb.verify_candidate('connect_timeout', source, fb.BASE_POLICY))

    def test_verified_deltas_compose_to_frozen_output(self):
        policy = deepcopy(fb.BASE_POLICY)
        for task_id in fb.TASKS:
            fb.apply_verified_delta(policy, task_id)
        self.assertEqual(policy, fb.EXPECTED_POLICY)
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / 'repo'; fb.create_fixture(repo)
            commit, passed, total = fb.finalize(repo, policy)
            self.assertEqual(commit, fb.EXPECTED_OUTPUT_COMMIT)
            self.assertEqual((passed, total), (2, 2))

    def test_stale_base_candidates_conflict_but_remain_individually_valid(self):
        baseline = deepcopy(fb.BASE_POLICY)
        a = deepcopy(baseline); a['timeouts']['connect'] = 3
        b = deepcopy(baseline); b['timeouts']['read'] = 8
        self.assertTrue(fb.verify_candidate('connect_timeout', fb.render_policy(a), baseline))
        self.assertTrue(fb.verify_candidate('read_timeout', fb.render_policy(b), baseline))
        self.assertNotEqual(fb.render_policy(a), fb.render_policy(b))


if __name__ == '__main__':
    unittest.main()
