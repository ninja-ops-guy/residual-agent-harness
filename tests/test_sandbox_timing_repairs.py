"""PR #108 Lane 2 repair regressions: real locks and owned child processes.

No kernel-isolation claim is made by these mechanism tests. Recovery substitutes
only the sandbox handshake and reap availability; pidfd ownership, consuming
wait, Git workspace, resource cleanup and journal publication remain real.
"""
from __future__ import annotations

import signal
import sqlite3
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from residual.factory.runtime_journal import LeaseRead
from residual.factory.runtime_workspace import ManagedWorktree
from residual.factory.termination_provenance import ProcessControl
from residual.factory.worker_contract import WorkerContractError
from residual.sandbox import subprocess_backend
from residual.sandbox.spec import SandboxLimits, SandboxSpec, Violation
from tests.test_factory_runtime import Fixture
from tests.test_sandbox_timing_adversarial import (
    _ExclusiveHolder, _JournalCase, _mk_contract, _seed_attempt,
)


class DeclaredTimeoutTests(unittest.TestCase):
    def test_direct_payload_cannot_pass_after_declared_deadline(self):
        spec = SandboxSpec('direct-budget', limits=SandboxLimits(timeout_seconds=1))
        result = subprocess_backend.run_contained(['/bin/sleep', '2'], spec)
        self.assertTrue(result.timed_out, result)
        self.assertEqual(result.violation, Violation.TIMEOUT)
        self.assertFalse(result.ok)

    def test_environment_path_obeys_same_declared_deadline(self):
        spec = SandboxSpec('env-budget', limits=SandboxLimits(timeout_seconds=1))
        result = subprocess_backend.run_contained_env(
            ['/bin/sleep', '2'], spec, stdin='', extra_env={'PATH': '/usr/bin:/bin'})
        self.assertTrue(result.timed_out, result)
        self.assertEqual(result.violation, Violation.TIMEOUT)
        self.assertFalse(result.ok)


class ContentionBudgetTests(_JournalCase):
    def seed(self):
        contract = _mk_contract()
        with sqlite3.connect(self.journal.path, isolation_level=None) as db:
            _seed_attempt(db, contract)
        return contract

    def test_retry_preserves_real_sqlite_diagnostic(self):
        contract = self.seed()
        self.journal.LEASE_READ_TIMEOUT_S = 0.01
        reads = []
        original = self.journal.lease_read

        def observe(*args, **kwargs):
            read = original(*args, **kwargs)
            reads.append(read)
            return read

        with _ExclusiveHolder(self.journal.path), patch.object(self.journal, 'lease_read', observe):
            denial = self._runtime()._lease_denial(contract, 'real_contention')
        self.assertTrue(any(r.diag == ('OperationalError', sqlite3.SQLITE_BUSY) for r in reads))
        self.assertEqual(denial[2]['read_error_type'], 'OperationalError')
        self.assertEqual(denial[2]['sqlite_errorcode'], sqlite3.SQLITE_BUSY)

    def test_watchdog_deadline_during_real_lease_contention(self):
        contract = self.seed()
        contract.wall_clock_budget_s, contract.memory_limit_mb = 0.3, 128
        process = subprocess.Popen(['/bin/sleep', '30'])
        control = ProcessControl(process, correlation_id='contention-budget')
        try:
            with _ExclusiveHolder(self.journal.path):
                started = time.monotonic()
                # Substitute the RSS sample only; this host may not expose it.
                with patch('residual.factory.runtime.Path.read_text', return_value='1 1'):
                    self._runtime()._watch(control, contract, started + 0.3,
                                          threading.Event(), threading.Event())
            self.assertLess(time.monotonic() - started, 0.8)
            self.assertEqual(control.reason[:2], ('resource', 'wall_clock_budget_s'))
            self.assertTrue(control.reaped)
            self.assertEqual(control.termination_record().observed_signal, signal.SIGKILL)
        finally:
            if not control.reaped:
                control.kill(('review', 'cleanup', {}))
            if not control.reaped:
                control.reap(timeout=5)
            control.close()

    def test_reader_retry_caps_connection_and_query_budget(self):
        self.seed()
        self.journal.READ_CONNECT_TIMEOUT_S = 0.8
        original = sqlite3.connect
        budgets = []

        def connect(*args, **kwargs):
            budgets.append(kwargs.get('timeout'))
            if len(budgets) == 1:
                time.sleep(0.3)
                raise sqlite3.OperationalError('database is locked')
            return original(*args, **kwargs)

        with _ExclusiveHolder(self.journal.path):
            started = time.monotonic()
            with patch('residual.factory.runtime_journal.sqlite3.connect', connect):
                with self.assertRaises(sqlite3.OperationalError):
                    self.journal.observations()
            elapsed = time.monotonic() - started
        self.assertGreaterEqual(len(budgets), 2)
        self.assertLess(budgets[1], 0.6)
        self.assertLess(elapsed, 1.0)

    def test_reader_does_not_retry_non_contention_errors(self):
        error = sqlite3.OperationalError('no such table: events')
        error.sqlite_errorcode = sqlite3.SQLITE_ERROR
        with patch('residual.factory.runtime_journal.sqlite3.connect', side_effect=error) as connect:
            with self.assertRaises(sqlite3.OperationalError) as caught:
                self.journal.observations()
        self.assertIs(caught.exception, error)
        connect.assert_called_once()

    def test_slow_connection_cannot_start_query_after_reader_deadline(self):
        self.journal.READ_CONNECT_TIMEOUT_S = 0.1
        original = sqlite3.connect
        statements = []
        def connect(*args, **kwargs):
            db = original(*args, **kwargs)
            db.set_trace_callback(statements.append)
            time.sleep(0.15)
            return db
        with patch('residual.factory.runtime_journal.sqlite3.connect', connect):
            with self.assertRaises(sqlite3.OperationalError):
                self.journal.observations()
        self.assertFalse(any(s.startswith('SELECT') for s in statements), statements)


class WatchdogPollingTests(Fixture):
    def test_memory_enforcement_continues_while_lease_is_unknown(self):
        ticks = [100.0]
        self.runtime._clock = lambda: ticks[0]
        control = SimpleNamespace(termination_requested=threading.Event(),
                                  process=SimpleNamespace(pid=12345),
                                  exited=lambda: False, kill=Mock())
        done = threading.Event()
        def unavailable(*args, **kwargs):
            ticks[0] += 1.1
            return LeaseRead('unknown', ('OperationalError', sqlite3.SQLITE_BUSY))
        samples = iter(['1 1', '10000000 10000000'])
        timer = threading.Timer(1, done.set)
        timer.start()
        try:
            with patch.object(self.journal, 'lease_read', unavailable), \
                 patch('residual.factory.runtime.Path.read_text', side_effect=lambda: next(samples)):
                self.runtime._watch(control, self.contract(), 200.0, done, threading.Event())
        finally:
            timer.cancel()
        self.assertEqual(control.kill.call_args.args[0][:2], ('resource', 'memory_limit_mb'))


class PendingReapTests(Fixture):
    def deferred_attempt(self, *, failed_finish=False, primary=None):
        contract = self.contract()
        workspace = ManagedWorktree(self.runtime.repository, self.runtime.root, contract)
        workspace.create()
        popen = subprocess.Popen
        owned = []
        def child(*args, **kwargs):
            return popen(['/bin/sleep', '30'], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        def owner(process, **kwargs):
            control = ProcessControl(process, **kwargs)
            owned.append(control)
            return control
        def unavailable(control, timeout=2.0):
            raise subprocess.TimeoutExpired(control.process.args, timeout)
        def exchange(*args):
            if primary is None:
                raise WorkerContractError('injected')
            requester, reason = primary
            owned[0].kill(reason, requester=requester)
            return False
        try:
            with patch('residual.factory.runtime.ManagedWorktree', return_value=workspace), \
                 patch.object(workspace, 'create'), \
                 patch('residual.factory.runtime.subprocess.Popen', child), \
                 patch('residual.factory.runtime.ProcessControl', owner), \
                 patch.object(self.runtime, '_watch', return_value=None), \
                 patch.object(self.runtime, '_exchange', side_effect=exchange), \
                 patch.object(ProcessControl, 'reap', unavailable):
                result = self.runtime.run(self.plan, self.approval, contract, 'pass')
                self.assertEqual(result.status, 'UNKNOWN')
                self.assertEqual(result.reason, 'reap_pending')
                self.assertFalse(result.process_reaped)
                self.assertIsNone(result.returncode)
                self.assertIsNone(result.termination)
                self.assertIsNone(result.candidate)
                self.assertFalse(owned[0].stopped.is_set())
                self.assertTrue(workspace.path.exists())
                self.assertIs(self.runtime._active[contract.attempt_id], owned[0])
                self.assertEqual(self.journal.attempts()[0]['state'], 'RUNNING')
                self.assertTrue(any(e['event'] == 'RuntimeReapPending' for e in self.events()))
                self.assertFalse(any(e['event'] == 'RuntimeAttemptFinished' for e in self.events()))
                # Keep the fault present across several retry opportunities.
                time.sleep(0.08)
                self.assertFalse(owned[0].stopped.is_set())
                with self.assertRaises(RuntimeError):
                    owned[0].termination_record()
                thread = self.runtime._pending_reaps[contract.attempt_id]
                if failed_finish:
                    self.journal.finish = Mock(side_effect=sqlite3.OperationalError('database is locked'))
            # The injection is gone; the runtime must drive all remaining work.
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            control = owned[0]
            self.assertTrue(control.reaped)
            self.assertTrue(control.stopped.is_set())
            self.assertLess(control.pidfd, 0)
            self.assertTrue(all(s.closed for s in
                                (control.process.stdin, control.process.stdout, control.process.stderr)))
            self.assertFalse(workspace.path.exists())
            return contract, control
        finally:
            for control in owned:
                if not control.reaped:
                    control.kill(('review', 'cleanup', {}))
                if not control.reaped:
                    control.reap(timeout=5)
                control.close()
            workspace.discard()

    def test_pending_reap_fences_then_publishes_exactly_once_after_recovery(self):
        contract, control = self.deferred_attempt()
        self.assertNotIn(contract.attempt_id, self.runtime._active)
        self.assertNotIn(contract.attempt_id, self.runtime._pending_reaps)
        self.assertNotIn(contract.attempt_id, self.runtime._reap_errors)
        self.assertEqual(self.journal.attempts()[0]['state'], 'FAILED')
        events = [e for e in self.events() if e['event'] == 'RuntimeAttemptFinished']
        self.assertEqual(len(events), 1)
        self.assertTrue(events[0]['process_reaped'])
        self.assertEqual(events[0]['termination'], control.termination_record().to_dict())
        self.assertEqual(events[0]['termination']['requested_by'], 'runtime')
        self.assertEqual(events[0]['termination']['request_field'], 'finalizer')

    def test_failed_deferred_publication_stays_pending_with_diagnostic(self):
        contract, _ = self.deferred_attempt(failed_finish=True)
        self.assertIn(contract.attempt_id, self.runtime._active)
        self.assertEqual(self.runtime._reap_errors[contract.attempt_id], 'OperationalError')
        self.assertEqual(self.journal.attempts()[0]['state'], 'RUNNING')
        self.assertFalse(any(e['event'] == 'RuntimeAttemptFinished' for e in self.events()))

    def test_deferred_reap_preserves_watchdog_primary_reason(self):
        _, control = self.deferred_attempt(primary=(
            'watchdog', ('resource', 'wall_clock_budget_s', {'elapsed_s': 5.0})))
        terminal = [e for e in self.events() if e['event'] == 'RuntimeAttemptFinished'][0]
        self.assertEqual((terminal['state'], terminal['reason']), ('VIOLATED', 'wall_clock_budget_s'))
        self.assertEqual(control.termination_record().classification, 'watchdog_wall_clock')
        self.assertEqual(control.termination_record().requested_by, 'watchdog')

    def test_deferred_reap_preserves_operator_cancellation(self):
        _, control = self.deferred_attempt(primary=(
            'operator', ('cancellation', 'operator_cancel', {'reason': 'local_operator'})))
        terminal = [e for e in self.events() if e['event'] == 'RuntimeAttemptFinished'][0]
        self.assertEqual((terminal['state'], terminal['reason']), ('CANCELLED', 'operator_cancel'))
        self.assertEqual(control.termination_record().classification, 'operator_cancel')
        self.assertEqual(control.termination_record().requested_by, 'operator')


if __name__ == '__main__':
    unittest.main()
