"""Offline tests for tamper detection and fail-closed readiness."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from residual.eval.protocol import ProtocolError, validate_protocol


ROOT = Path(__file__).resolve().parents[1]


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'docs/evaluation', self.root / 'docs/evaluation')
        self.path = self.root / 'docs/evaluation/r0-r5.protocol.json'
        self.sha = hashlib.sha256(self.path.read_bytes()).hexdigest()

    def check(self, **kwargs):
        return validate_protocol(self.path, self.root, expected_sha256=self.sha, **kwargs)

    def mutate(self, callback):
        p = json.loads(self.path.read_text())
        callback(p)
        self.path.write_text(json.dumps(p))
        self.sha = hashlib.sha256(self.path.read_bytes()).hexdigest()

    def test_preparation_integrity_is_not_live_readiness(self):
        self.assertEqual(self.check()['readiness'], 'blocked')
        with self.assertRaisesRegex(ProtocolError, 'freeze unavailable'):
            self.check(require_frozen=True)

    def test_protocol_tamper(self):
        self.path.write_text(self.path.read_text() + ' ')
        with self.assertRaisesRegex(ProtocolError, 'protocol SHA256'):
            self.check()

    def test_workload_tamper(self):
        (self.root / 'docs/evaluation/r0-r5.fixture-workload.json').write_text('{}')
        with self.assertRaisesRegex(ProtocolError, 'workload SHA256'):
            self.check()

    def test_declared_frozen_does_not_enable_live(self):
        self.mutate(lambda p: p.update(frozen=True, live_execution_enabled=True))
        with self.assertRaisesRegex(ProtocolError, 'cannot qualify live'):
            self.check()

    def test_population_cannot_shrink(self):
        self.mutate(lambda p: p['task_population'].pop())
        with self.assertRaisesRegex(ProtocolError, 'population'):
            self.check()

    def test_relative_path_cannot_escape(self):
        self.mutate(lambda p: p['workload'].update(path='../external.json'))
        with self.assertRaisesRegex(ProtocolError, 'repository-relative'):
            self.check()

    def test_duplicate_configuration_rejected(self):
        self.mutate(lambda p: p['configurations'][1].update(id='R0'))
        with self.assertRaisesRegex(ProtocolError, 'exactly once'):
            self.check()

    def test_missing_seed_rejected(self):
        self.mutate(lambda p: p['seeds'].pop())
        with self.assertRaisesRegex(ProtocolError, 'schedule seed'):
            self.check()
