"""Reproduce #58 lifecycle regressions without launching model or worker code."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
import io
import json
from pathlib import Path
import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tests.test_factory_runtime import Fixture
from residual.factory.runtime import _ProcessControl, main
from residual.factory.runtime_workspace import ManagedWorktree
from residual.factory.worker_contract import WorkerContractError


class LifecycleGuards(Fixture):
    def workspace(self, state='RESERVED'):
        contract = self.contract()
        self.journal.claim(contract, source_hash='a' * 64, approval=self.approval.to_dict())
        workspace = ManagedWorktree(self.repo, self.root / 'work', contract)
        workspace.create()
        if state == 'RUNNING':
            self.journal.started(contract, 12345)  # journal fixture, not an actual worker
        elif state != 'RESERVED':
            self.journal.finish(contract, state)
        return contract, workspace

    def assert_purge_rejected_without_effects(self, contract, workspace):
        events = len(self.events())
        states = self.journal.attempts()
        with self.assertRaises(WorkerContractError):
            self.runtime.purge(contract)
        self.assertTrue(workspace.path.exists(), 'rejection must precede deletion')
        self.assertEqual(self.journal.attempts(), states)
        self.assertEqual(len(self.events()), events)

    def test_reserved_workspace_is_not_deleted_before_rejection(self):
        self.assert_purge_rejected_without_effects(*self.workspace())

    def test_running_workspace_is_not_deleted_before_rejection(self):
        self.assert_purge_rejected_without_effects(*self.workspace('RUNNING'))

    def test_unknown_attempt_is_rejected_before_deletion(self):
        contract = self.contract()
        workspace = ManagedWorktree(self.repo, self.root / 'work', contract)
        workspace.create()
        self.assert_purge_rejected_without_effects(contract, workspace)

    def test_failed_attempt_is_not_relabelled_as_purged_candidate(self):
        self.assert_purge_rejected_without_effects(*self.workspace('FAILED'))

    def test_same_attempt_with_different_contract_cannot_purge(self):
        contract, workspace = self.workspace('CANDIDATE')
        forged = replace(contract, max_file_writes=contract.max_file_writes + 1)
        self.assertNotEqual(contract.contract_hash, forged.contract_hash)
        self.assert_purge_rejected_without_effects(forged, workspace)

    def test_exact_candidate_is_purged_and_observed(self):
        contract, workspace = self.workspace('CANDIDATE')
        self.runtime.purge(contract)
        self.assertFalse(workspace.path.exists())
        self.assertEqual(self.journal.attempts()[0]['state'], 'PURGED')
        self.assertEqual(sum(e['event'] == 'RuntimeCandidatePurged' for e in self.events()), 1)
        with self.assertRaises(WorkerContractError):
            self.runtime.purge(contract)

    def test_missing_worktree_cannot_be_reported_as_successful_purge(self):
        contract, workspace = self.workspace('CANDIDATE')
        workspace.discard()
        with self.assertRaises(WorkerContractError):
            self.runtime.purge(contract)
        self.assertEqual(self.journal.attempts()[0]['state'], 'CANDIDATE')

    def test_invalid_retention_rejected_before_journal_read(self):
        for value in (True, False, 0, -1, float('nan'), float('inf'), -float('inf'), '3600', None):
            with self.subTest(retention=value), patch.object(self.journal, 'attempts') as attempts:
                with self.assertRaises(WorkerContractError):
                    self.runtime.purge_expired(retention_s=value)
                attempts.assert_not_called()

    def test_invalid_retention_clock_rejected_before_journal_read(self):
        for value in (True, -1, 1.5, 'clock'):
            with self.subTest(clock=value), patch.object(self.journal, 'attempts') as attempts:
                with self.assertRaises(WorkerContractError):
                    self.runtime.purge_expired(now_ns=value)
                attempts.assert_not_called()

    def test_expiry_boundary_preserves_candidate_until_due(self):
        contract, workspace = self.workspace('CANDIDATE')
        stamp = self.journal.attempts()[0]['updated_ns']
        self.assertEqual(self.runtime.purge_expired(retention_s=1.5, now_ns=stamp+1_499_999_999), [])
        self.assertTrue(workspace.path.exists())
        self.assertEqual(self.runtime.purge_expired(retention_s=1.5, now_ns=stamp+1_500_000_000), [contract.attempt_id])

    def test_empty_batch_still_validates_capacity(self):
        for value in (0, -1, 33, True, 1.5, '2', None):
            with self.subTest(capacity=value), patch.object(self.journal, 'observe') as observe:
                with self.assertRaises(WorkerContractError):
                    self.runtime.run_many(self.plan, self.approval, [], capacity=value)
                observe.assert_not_called()

    def test_capacity_observation_precedes_dispatch(self):
        contract = self.contract()
        def execute(*_):
            self.assertTrue(any(e['event'] == 'RuntimeCapacitySelected' and e['capacity'] == 2
                                and e['execution_plan_hash'] == self.plan.graph_hash for e in self.events()))
            return 'fixture-result'
        with patch.object(self.runtime, 'run', side_effect=execute):
            self.assertEqual(self.runtime.run_many(self.plan, self.approval, [(contract, 'pass')]), ['fixture-result'])

    def test_capacity_audit_failure_prevents_dispatch(self):
        with patch.object(self.journal, 'observe', side_effect=OSError('fixture audit failure')):
            with patch.object(self.runtime, 'run') as run:
                with self.assertRaises(OSError):
                    self.runtime.run_many(self.plan, self.approval, [(self.contract(), 'pass')])
                run.assert_not_called()

    def test_empty_valid_batch_records_capacity(self):
        self.assertEqual(self.runtime.run_many(self.plan, self.approval, [], capacity=2), [])
        self.assertEqual(self.events()[-1]['event'], 'RuntimeCapacitySelected')

    def test_missing_cli_input_returns_sanitized_blocked_json_for_both_run_aliases(self):
        for option in ('--run-id', '--trace-id'):
            with self.subTest(option=option):
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    code = main(['--repo', str(self.repo), '--runtime-root', str(self.root/'work'),
                                 '--journal', str(self.journal.path), option, 'test-run',
                                 '--plan', str(self.root/'missing.json'), '--approval', 'missing',
                                 '--contract', 'missing', '--source', 'missing'])
                self.assertEqual(code, 1)
                self.assertEqual(out.getvalue(), '')
                self.assertEqual(json.loads(err.getvalue()), {'status': 'blocked', 'error_type': 'FileNotFoundError'})
                self.assertNotIn(str(self.root), err.getvalue())
                self.assertEqual(self.journal.attempts(), [])


class WatchdogIntentGuards(Fixture):
    def control(self):
        return SimpleNamespace(termination_requested=threading.Event(),
                               process=SimpleNamespace(pid=12345, poll=lambda: None), kill=Mock())

    def test_existing_termination_intent_skips_secondary_lease_read(self):
        control = self.control()
        control.termination_requested.set()
        with patch.object(self.journal, 'lease_is_current') as lease:
            self.runtime._watch(control, self.contract(), 100.0, threading.Event())
        lease.assert_not_called()
        control.kill.assert_not_called()

    def test_termination_between_memory_read_and_lease_read_preserves_primary_owner(self):
        control = self.control()
        def statm(*_):
            control.termination_requested.set()
            return '1 1'
        with patch('residual.factory.runtime.time.monotonic', return_value=100.0):
            with patch.object(Path, 'read_text', side_effect=statm):
                with patch.object(self.journal, 'lease_is_current') as lease:
                    self.runtime._watch(control, self.contract(), 100.0, threading.Event())
        lease.assert_not_called()
        control.kill.assert_not_called()

    def test_lease_read_failure_without_other_owner_still_kills(self):
        control = self.control()
        with patch('residual.factory.runtime.time.monotonic', return_value=100.0):
            with patch.object(Path, 'read_text', return_value='1 1'):
                with patch.object(self.journal, 'lease_is_current', side_effect=OSError('fixture error')):
                    self.runtime._watch(control, self.contract(), 100.0, threading.Event())
        control.kill.assert_called_once_with(('lease', 'lease_generation', {'reason': 'revoked_or_unavailable'}))

    def test_kill_records_intent_before_process_poll(self):
        process = Mock(pid=12345)
        with patch('residual.factory.runtime.os.pidfd_open', return_value=10):
            control = _ProcessControl(process)
        def poll():
            self.assertTrue(control.termination_requested.is_set())
            return 0
        process.poll.side_effect = poll
        reason = ('tool', 'broker_protocol', {'reason': 'primary'})
        control.kill(reason)
        self.assertEqual(control.reason, reason)
        self.assertTrue(control.stopped.is_set())
