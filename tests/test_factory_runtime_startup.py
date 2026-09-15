"""Causal startup ordering regressions for PR #96; no scheduler-speed assumptions."""
from __future__ import annotations

import sqlite3
import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tests.test_factory_runtime import Fixture


class OneWatchdogTick:
    """Run exactly one watchdog iteration without depending on thread scheduling."""

    def __init__(self):
        self.finished = False

    def wait(self, _timeout):
        previous, self.finished = self.finished, True
        return previous


class StartupOrderingTests(Fixture):
    def test_watchdog_tick_before_started_persistence_cannot_fence_reserved_attempt(self):
        first_tick = threading.Event()
        original_watch = self.runtime._watch
        original_started = self.journal.started
        errors = []

        def watch(control, contract, started_ns, done, *args):
            try:
                original_watch(control, contract, started_ns, OneWatchdogTick(), *args)
            except BaseException as exc:
                errors.append(exc)
            finally:
                first_tick.set()
            original_watch(control, contract, started_ns, done, *args)

        def started(contract, pid):
            self.assertTrue(first_tick.wait(5), 'forced pre-persistence watchdog tick did not complete')
            original_started(contract, pid)

        with patch.object(self.runtime, '_watch', side_effect=watch), \
             patch.object(self.journal, 'started', side_effect=started):
            _, result = self.run_source("write_file('output.txt', 'safe')", wall_clock_budget_s=30)
        self.assertFalse(errors, errors)
        self.assertEqual(result.status, 'CANDIDATE', result)
        self.assertIsNone(result.termination['requested_by'])

    def test_startup_database_lock_does_not_preempt_durable_start(self):
        """Force a real SQLite read failure only during started() persistence.

        This reproduces a startup-unavailability mechanism, not attribution of
        the historical CI failure (which did not retain its read exception).
        """
        locked, first_tick = threading.Event(), threading.Event()
        original_watch, original_started = self.runtime._watch, self.journal.started
        errors = []

        def watch(control, contract, started_ns, done, *args):
            try:
                self.assertTrue(locked.wait(5))
                original_watch(control, contract, started_ns, OneWatchdogTick(), *args)
            except BaseException as exc:
                errors.append(exc)
            finally:
                first_tick.set()
            original_watch(control, contract, started_ns, done, *args)

        def started(contract, pid):
            db = sqlite3.connect(self.journal.path, isolation_level=None)
            try:
                db.execute('PRAGMA locking_mode=EXCLUSIVE')
                db.execute('BEGIN EXCLUSIVE')
                locked.set()
                self.assertTrue(first_tick.wait(5), 'pre-persistence tick did not finish')
                db.execute('ROLLBACK')
            finally:
                db.close()
            original_started(contract, pid)

        with patch.object(self.runtime, '_watch', side_effect=watch), \
             patch.object(self.journal, 'started', side_effect=started):
            _, result = self.run_source("write_file('output.txt', 'safe')", wall_clock_budget_s=30)
        self.assertFalse(errors, errors)
        self.assertEqual(result.status, 'CANDIDATE', result)

    def test_resources_still_enforced_while_started_persistence_is_blocked(self):
        from concurrent.futures import ThreadPoolExecutor
        entered, release = threading.Event(), threading.Event()
        original_started = self.journal.started
        def started(contract, pid):
            entered.set()
            if not release.wait(5):
                raise RuntimeError('fixture persistence barrier timed out')
            original_started(contract, pid)
        clock = lambda: 31_000_000_000 if entered.is_set() else 0
        with patch.object(self.runtime, '_monotonic_ns', side_effect=clock), \
             patch.object(self.journal, 'started', side_effect=started), \
             ThreadPoolExecutor(max_workers=1) as pool:
            c = self.contract(wall_clock_budget_s=30)
            future = pool.submit(self.runtime.run, self.plan, self.approval, c, "write_file('output.txt','no')")
            try:
                self.assertTrue(entered.wait(5))
                with self.runtime._lock:
                    control = self.runtime._active[c.attempt_id]
                self.assertTrue(control.stopped.wait(2), 'resource watchdog was blocked by persistence')
                self.assertFalse(any(e['event'] == 'RuntimeSandboxReady' for e in self.events()))
            finally:
                release.set()
            result = future.result(timeout=5)
        self.assertEqual(result.termination['classification'], 'watchdog_wall_clock')
        self.assertIsNone(result.candidate)
        self.assertFalse(any(e['event'] == 'RuntimeSandboxReady' for e in self.events()))

    def test_failed_started_persistence_prevents_source_dispatch(self):
        with patch.object(self.journal, 'started', side_effect=OSError('fixture failure')):
            _, result = self.run_source("write_file('output.txt', 'no')")
        self.assertEqual(result.status, 'FAILED')
        self.assertTrue(result.process_reaped)
        self.assertIsNone(result.candidate)
        self.assertFalse(any(e['event'] == 'RuntimeSandboxReady' for e in self.events()))

    def test_inconsistent_wait_status_cannot_publish_candidate(self):
        import os
        import signal
        info = SimpleNamespace(si_code=os.CLD_KILLED, si_status=signal.SIGKILL)
        with patch('residual.factory.termination_provenance.os.waitid', return_value=info):
            _, result = self.run_source("write_file('output.txt', 'no')")
        self.assertEqual(result.status, 'FAILED')
        self.assertEqual(result.termination['classification'], 'unknown_wait_status')
        self.assertIsNone(result.candidate)


class StartupWatchdogTests(Fixture):
    def control(self):
        return SimpleNamespace(termination_requested=threading.Event(), exited=lambda: False,
                               process=SimpleNamespace(pid=12345), kill=Mock())

    def test_pending_started_ack_skips_lease_read_only(self):
        control = self.control()
        with patch.object(self.runtime, '_monotonic_ns', return_value=0), \
             patch('residual.factory.runtime.Path.read_text', return_value='1 1'), \
             patch.object(self.journal, 'lease_is_current') as lease:
            self.runtime._watch(control, self.contract(), 0, OneWatchdogTick(), threading.Event())
        lease.assert_not_called()
        control.kill.assert_not_called()

    def test_pending_started_ack_does_not_disable_memory_enforcement(self):
        control = self.control()
        with patch.object(self.runtime, '_monotonic_ns', return_value=0), \
             patch('residual.factory.runtime.Path.read_text', return_value='10000000 10000000'), \
             patch.object(self.journal, 'lease_is_current') as lease:
            self.runtime._watch(control, self.contract(), 0, OneWatchdogTick(), threading.Event())
        lease.assert_not_called()
        self.assertEqual(control.kill.call_args.args[0][1], 'memory_limit_mb')

    def test_after_ack_unavailable_lease_still_fails_closed_with_diagnostic(self):
        control = self.control()
        ready = threading.Event()
        ready.set()
        error = sqlite3.OperationalError('this text must not enter the ledger')
        error.sqlite_errorcode = sqlite3.SQLITE_BUSY
        with patch.object(self.runtime, '_monotonic_ns', return_value=0), \
             patch('residual.factory.runtime.Path.read_text', return_value='1 1'), \
             patch.object(self.journal, 'lease_is_current', side_effect=error):
            self.runtime._watch(control, self.contract(), 0, OneWatchdogTick(), ready)
        control.kill.assert_called_once_with(
            ('lease', 'lease_generation', {'reason':'revoked_or_unavailable',
                                         'read_error_type':'OperationalError',
                                         'sqlite_errorcode':sqlite3.SQLITE_BUSY}), requester='watchdog')
