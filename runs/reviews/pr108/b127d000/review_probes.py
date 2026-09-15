"""Independent Lane 2 probes. Run from the exact reviewed checkout with pytest.

Expected to FAIL on b127d000. This file does not alter protected source/tests.
SQLite locks and child processes are real. Fault injection is limited to the
named boundary in each test; these are mechanism probes, not M4 qualification.
"""
import json
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

from residual.factory import runtime as fr
from residual.factory.termination_provenance import ProcessControl
from residual.factory.worker_contract import WorkerContractError
from tests.test_factory_runtime import Fixture
from tests.test_sandbox_timing_adversarial import (
    _ExclusiveHolder, _JournalCase, _mk_contract, _seed_attempt,
)


class RemainingLeaseAndReadDefects(_JournalCase):
    def seed(self):
        contract = _mk_contract()
        with sqlite3.connect(self.journal.path, isolation_level=None) as db:
            _seed_attempt(db, contract)
        return contract

    def test_retry_keeps_last_actual_sqlite_error_after_budget_exhaustion(self):
        contract = self.seed()
        runtime = self._runtime()
        # A shorter individual read cap is legal; the outer absolute bound is
        # still the real, unmodified 2 seconds. Every failure is real SQLITE_BUSY.
        self.journal.LEASE_READ_TIMEOUT_S = 0.01
        reads = []
        original = self.journal.lease_read

        def observe(*args, **kwargs):
            result = original(*args, **kwargs)
            reads.append((result.state, result.diag))
            return result

        with _ExclusiveHolder(self.journal.path), patch.object(self.journal, 'lease_read', observe):
            started = time.monotonic()
            denial = runtime._lease_denial(contract, 'review_real_contention')
        detail = {'elapsed_s': time.monotonic() - started, 'reads': reads, 'denial': denial}
        print('LEASE_DIAGNOSTIC', json.dumps(detail))
        self.assertTrue(any(diag == ('OperationalError', sqlite3.SQLITE_BUSY)
                            for _, diag in reads), 'fault did not reach SQLite')
        self.assertEqual(denial[2].get('read_error_type'), 'OperationalError', detail)
        self.assertEqual(denial[2].get('sqlite_errorcode'), sqlite3.SQLITE_BUSY, detail)

    def test_watchdog_wall_deadline_remains_live_during_lease_contention(self):
        contract = self.seed()
        contract.wall_clock_budget_s = 0.3
        contract.memory_limit_mb = 128
        runtime = self._runtime()
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        control = ProcessControl(process, correlation_id='lane2-watchdog')
        try:
            with _ExclusiveHolder(self.journal.path):
                started = time.monotonic()
                # This host cannot meter child RSS. Substitute only the RSS
                # sample; retain real clock, lease DB, watchdog loop and pidfd kill.
                with patch('residual.factory.runtime.Path.read_text', return_value='1 1'):
                    runtime._watch(control, contract, started + 0.3,
                                   threading.Event(), threading.Event())
                elapsed = time.monotonic() - started
            detail = {'elapsed_s': elapsed, 'deadline_s': 0.3, 'reason': control.reason,
                      'termination': control.termination_record().to_dict()}
            print('WATCHDOG_DEADLINE', json.dumps(detail))
            self.assertLess(elapsed, 0.8, detail)
            self.assertEqual(control.reason[:2], ('resource', 'wall_clock_budget_s'), detail)
        finally:
            if not control.reaped:
                control.kill(('review', 'cleanup', {}))
            if not control.reaped:
                control.reap(timeout=5)
            control.close()

    def test_general_read_retry_does_not_restart_full_busy_budget(self):
        self.seed()
        # Scale the documented reader budget to 0.3 s. Model a first connection
        # failing late in that budget; the second read really contends in SQLite.
        self.journal.READ_CONNECT_TIMEOUT_S = 0.3
        real_connect = sqlite3.connect
        attempts = []

        def delayed_first_connect(*args, **kwargs):
            attempts.append(kwargs.get('timeout'))
            if len(attempts) == 1:
                time.sleep(0.25)
                raise sqlite3.OperationalError('database is locked')
            return real_connect(*args, **kwargs)

        with _ExclusiveHolder(self.journal.path):
            started = time.monotonic()
            with patch('residual.factory.runtime_journal.sqlite3.connect', delayed_first_connect):
                with self.assertRaises(sqlite3.OperationalError):
                    self.journal.observations()
            elapsed = time.monotonic() - started
        detail = {'elapsed_s': elapsed, 'total_budget_s': 0.3, 'connection_budgets_s': attempts}
        print('GENERAL_READ_DEADLINE', json.dumps(detail))
        self.assertGreaterEqual(len(attempts), 2, 'retry path was not exercised')
        self.assertLess(elapsed, 0.45, detail)


class ReapRecoveryDefect(Fixture):
    def test_finalizer_drives_reap_recovery_after_transient_timeout(self):
        real_popen = subprocess.Popen
        owned = []

        def safe_child(*args, **kwargs):
            # Stand in for the sandbox handshake only. The subprocess and
            # ProcessControl are real; no candidate code or namespace fallback.
            return real_popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, start_new_session=True)

        def remember_control(process, **kwargs):
            control = ProcessControl(process, **kwargs)
            owned.append(control)
            return control

        def unavailable_reap(control, timeout=2.0):
            raise subprocess.TimeoutExpired(control.process.args, timeout)

        # Prepare real worktree before patching Popen, which git also uses.
        contract = self.contract()
        from residual.factory.runtime_workspace import ManagedWorktree
        workspace = ManagedWorktree(self.runtime.repository, self.runtime.root, contract)
        workspace.create()
        thrown = None
        try:
            with patch('residual.factory.runtime.ManagedWorktree', return_value=workspace), \
                 patch.object(workspace, 'create'), \
                 patch('residual.factory.runtime.subprocess.Popen', safe_child), \
                 patch('residual.factory.runtime.ProcessControl', remember_control), \
                 patch.object(self.runtime, '_watch', return_value=None), \
                 patch.object(self.runtime, '_exchange', side_effect=WorkerContractError('review fault')), \
                 patch.object(ProcessControl, 'reap', unavailable_reap):
                try:
                    self.runtime.run(self.plan, self.approval, contract, 'pass')
                except Exception as exc:
                    thrown = (type(exc).__name__, str(exc))
            self.assertEqual(len(owned), 1, 'fault did not reach ProcessControl')
            control = owned[0]
            recovered = control.stopped.wait(0.5)  # reap injection has ended
            detail = {'exception': thrown, 'reap_timed_out': control.reap_timed_out.is_set(),
                      'stopped': control.stopped.is_set(), 'reaped': control.reaped,
                      'active': contract.attempt_id in self.runtime._active,
                      'journal_state': self.journal.attempts()[0]['state']}
            print('REAP_RECOVERY', json.dumps(detail))
            self.assertTrue(control.reap_timed_out.is_set(), 'fault not exercised')
            self.assertTrue(recovered, detail)
        finally:
            # Cleanup belongs to this probe, never counts as runtime recovery.
            for control in owned:
                if not control.reaped:
                    control.kill(('review', 'cleanup', {}))
                if not control.reaped:
                    control.reap(timeout=5)
                control.close()
                for stream in (control.process.stdin, control.process.stdout, control.process.stderr):
                    if stream is not None:
                        stream.close()
            workspace.discard()
