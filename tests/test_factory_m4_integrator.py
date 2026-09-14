from __future__ import annotations

import dataclasses
import hashlib
import tempfile
import time
import unittest
from pathlib import Path

from residual.factory.evidence_bus import EvidenceBus
from residual.factory.evidence_receipts import ArtifactBinding, EvidenceError, StationIdentity, WorkerReceipt
from residual.factory.integrator import DeterministicIntegrator, IntegrationConflict
from residual.factory.runtime_workspace import git


class M4IntegratorTests(unittest.TestCase):
    def setUp(self):
        try:
            self.identity = StationIdentity.generate()
        except EvidenceError as exc:
            self.skipTest(str(exc))
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'; self.repo.mkdir()
        git(self.repo, 'init')
        (self.repo / 'shared.txt').write_text('base\n')
        (self.repo / 'other.txt').write_text('base-other\n')
        git(self.repo, 'add', '.')
        git(self.repo, '-c', 'user.name=test', '-c', 'user.email=test@localhost', 'commit', '-m', 'base')
        self.commit = git(self.repo, 'rev-parse', 'HEAD').decode().strip()
        self.bus = EvidenceBus(self.root / 'evidence.db')
        self.events = []
        self.integrator = DeterministicIntegrator(self.repo, self.bus, self.identity, observe=self.events.append)
        self.checks = {
            'full_test_suite': lambda path: True,
            'type_check': lambda path: True,
            'contract_validation': lambda path: True,
        }

    def receipt(self, task: str, path: str, content: bytes, *, parents=()):
        artifact = ArtifactBinding(path, hashlib.sha256(content).hexdigest(), len(content))
        base = WorkerReceipt(
            receipt_id='receipt-' + task, execution_plan_hash='1' * 64,
            task_id=task, worker_id='worker-' + task, swarm_id='swarm1', attempt_id='attempt-' + task,
            engine_name='brokered-python', engine_version='linux-seccomp-broker-v1',
            input_commit=self.commit, output_commit=hashlib.sha1((task + path).encode()).hexdigest(),
            contract_hash=hashlib.sha256(task.encode()).hexdigest(), artifacts=(artifact,),
            requirements_met=((task, True),), verification_results=(('unit', 'pass'),),
            overall_verdict='pass', verifier_identity='station-verifier', verifier_revision='6' * 64,
            parent_receipts=tuple(parents), issued_at_ns=time.time_ns(), station_key_id=self.identity.key_id,
            station_signature='00')
        signed = dataclasses.replace(base, station_signature=self.identity.sign(base.receipt_hash))
        self.bus.append(signed, {path: content})
        return signed

    def test_same_receipts_produce_same_output_commit(self):
        a = self.receipt('a', 'shared.txt', b'changed\n')
        first = self.integrator.integrate((a.receipt_hash,), checks=self.checks)
        second = self.integrator.integrate((a.receipt_hash,), checks=self.checks)
        self.assertEqual(first.output_commit, second.output_commit)
        self.assertTrue(first.verify(self.identity.public_bytes()))
        self.assertTrue(second.verify(self.identity.public_bytes()))

    def test_topological_order_requires_parents_present(self):
        parent = self.receipt('parent', 'other.txt', b'parent\n')
        child = self.receipt('child', 'shared.txt', b'child\n', parents=(parent.receipt_hash,))
        ordered = self.integrator.topological_order((child, parent))
        self.assertEqual([x.task_id for x in ordered], ['parent', 'child'])
        with self.assertRaises(EvidenceError):
            self.integrator.topological_order((child,))

    def test_true_overlap_conflict_is_not_auto_resolved(self):
        a = self.receipt('a', 'shared.txt', b'left\n')
        b = self.receipt('b', 'shared.txt', b'right\n')
        with self.assertRaises(IntegrationConflict):
            self.integrator.integrate((a.receipt_hash, b.receipt_hash), checks=self.checks)
        self.assertTrue(any(event['event'] == 'IntegrationConflictDetected' for event in self.events))

    def test_human_resolution_is_bound_into_receipt(self):
        a = self.receipt('a', 'shared.txt', b'left\n')
        b = self.receipt('b', 'shared.txt', b'right\n')
        result = self.integrator.integrate((a.receipt_hash, b.receipt_hash), checks=self.checks,
                                           human_resolutions={'shared.txt': a.receipt_hash})
        self.assertEqual(result.human_resolutions, (('shared.txt', a.receipt_hash),))
        self.assertTrue(result.verify(self.identity.public_bytes()))
        self.assertTrue(any(event['event'] == 'IntegrationConflictResolved' for event in self.events))

    def test_identical_overlap_is_deduplicated(self):
        a = self.receipt('a', 'shared.txt', b'same\n')
        b = self.receipt('b', 'shared.txt', b'same\n')
        result = self.integrator.integrate((b.receipt_hash, a.receipt_hash), checks=self.checks)
        self.assertTrue(result.verify(self.identity.public_bytes()))

    def test_project_verification_failure_emits_no_integration_receipt(self):
        a = self.receipt('a', 'shared.txt', b'changed\n')
        checks = dict(self.checks); checks['full_test_suite'] = lambda path: False
        with self.assertRaises(EvidenceError):
            self.integrator.integrate((a.receipt_hash,), checks=checks)
        self.assertTrue(any(event['event'] == 'ProjectVerificationFailed' for event in self.events))
        self.assertFalse(any(event['event'] == 'IntegrationReceiptIssued' for event in self.events))

    def test_required_verification_checks_cannot_be_skipped(self):
        a = self.receipt('a', 'shared.txt', b'changed\n')
        with self.assertRaises(EvidenceError):
            self.integrator.integrate((a.receipt_hash,), checks={'full_test_suite': lambda path: True})


if __name__ == '__main__':
    unittest.main()
