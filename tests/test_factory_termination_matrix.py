"""The matrix runner isolates repository imports and never counts skips as evidence."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/factory_termination_matrix.py'
spec = importlib.util.spec_from_file_location('matrix_runner_test_subject', SCRIPT)
matrix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(matrix)


class MatrixIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self, name, *, skip=False, fail=False):
        repo = self.root / name
        (repo / 'tests').mkdir(parents=True)
        (repo / 'matrix_fixture_identity.py').write_text(f'VALUE = {name!r}\n')
        body = 'self.skipTest("fixture unsupported")' if skip else f'self.assertEqual(VALUE, {("wrong" if fail else name)!r})'
        (repo / 'tests/test_factory_runtime.py').write_text(
            'import unittest\nfrom matrix_fixture_identity import VALUE\n'
            'class ExecutionTests(unittest.TestCase):\n'
            f'    def {matrix.RAW_TEST}(self):\n        {body}\n'
            f'    def {matrix.NEW_BLOCKED_TEST}(self):\n        {body}\n')
        for args in (('init','-q'),('add','.'),('-c','user.name=fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture')):
            subprocess.run(['git','-C',str(repo),*args], check=True, capture_output=True)
        return repo

    def run_matrix(self, repo, *extra):
        output = self.root / f'{repo.name}.json'
        run = subprocess.run
        def quiet_run(*args, **kwargs):
            return run(*args, **kwargs, stdout=subprocess.DEVNULL)
        with patch.object(matrix.subprocess, 'run', side_effect=quiet_run):
            code = matrix.main(['--repo-root',str(repo),'--condition','normal','--runs','2',
                                '--output',str(output),*extra])
        return code, json.loads(output.read_text())

    def test_two_inprocess_calls_cannot_cross_contaminate_modules_or_path(self):
        before_path = list(sys.path)
        before_module = sys.modules.get('matrix_fixture_identity')
        for name in ('baseline', 'candidate'):
            code, report = self.run_matrix(self.fixture(name))
            self.assertEqual(code, 0, report)
            self.assertEqual(report['runs_per_test'], 2)
            self.assertEqual(sys.path, before_path)
            self.assertIs(sys.modules.get('matrix_fixture_identity'), before_module)
            self.assertNotIn('swarm3_target_factory_runtime', sys.modules)

    def test_failed_candidates_are_nonzero_and_keep_failures(self):
        code, report = self.run_matrix(self.fixture('failed', fail=True))
        self.assertEqual(code, 1)
        self.assertEqual(len(report['details']), 4)
        self.assertTrue(all(row['failures'] == 2 and row['zero_failure_upper_95'] is None for row in report['stats'].values()))

    def test_historical_failures_can_be_retained_without_stopping_candidate(self):
        code, report = self.run_matrix(self.fixture('historical', fail=True), '--allow-failures')
        self.assertEqual(code, 0)
        self.assertTrue(report['details'])
        self.assertTrue(all(row['zero_failure_upper_95'] is None for row in report['stats'].values()))

    def test_skips_never_produce_zero_failure_bound_even_in_historical_mode(self):
        code, report = self.run_matrix(self.fixture('unsupported', skip=True), '--allow-failures')
        self.assertEqual(code, 2)
        self.assertTrue(all(row['skips'] == 2 and row['zero_failure_upper_95'] is None for row in report['stats'].values()))

    def test_upper_bound_has_the_fixed_condition_denominator(self):
        self.assertIsNone(matrix.upper_95_zero_failures(0))
        self.assertAlmostEqual(matrix.upper_95_zero_failures(500), 0.005973551516349596)
