"""Swarm 3: sandbox timing determinism regression tests.

Covers: lease tri-state (H1), single deadline owner (H2/H3), no wait under
the kill lock (M6), typed TIMEOUT terminal outcomes (H4/M5), typed git
timeouts (M9), and the cancel() primary-attribution race fix.
"""
from __future__ import annotations

import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from residual.factory import m4_sandbox
from residual.factory.m4_safety import run_trusted_fixture
from residual.factory.runtime_journal import RuntimeJournal
from residual.factory.runtime_workspace import GitOperationTimeout
from residual.factory.termination_provenance import ProcessControl
from residual.factory.worker_contract import (
    AttemptGuard, WorkerContract, WorkerContractError,
)
from tests.test_factory_runtime import Fixture

ROOT = Path(__file__).resolve().parents[1]
ISOLATED = m4_sandbox.probe_isolation()[0]


class LeaseTriStateTests(Fixture):
    """H1: lease_state is current/revoked/unknown; unknown only on sqlite3.Error."""

    def test_lease_state_tri_state_unit(self):
        contract = self.contract()
        # No row at all: definitively not current -> revoked (never unknown).
        self.assertEqual(self.journal.lease_state(contract), 'revoked')
        self.journal.claim(contract, source_hash='a' * 64, approval=self.approval.to_dict())
        self.assertEqual(self.journal.lease_state(contract), 'current')
        self.journal.revoke(contract.attempt_id)
        self.assertEqual(self.journal.lease_state(contract), 'revoked')
        # Store failure: unknown, and ONLY on sqlite3.Error.
        real_connect = sqlite3.connect
        with patch('residual.factory.runtime_journal.sqlite3.connect',
                   side_effect=sqlite3.OperationalError('database is locked')):
            self.assertEqual(self.journal.lease_state(contract), 'unknown')
        self.assertTrue(callable(real_connect))

    def test_one_shot_locked_read_does_not_kill_or_retype(self):
        # A single transient 'database is locked' on the lease read path must
        # NOT kill the worker — and must never be retyped as lease_generation.
        fired = threading.Event()
        real_connect = sqlite3.connect

        def flaky_connect(path, *args, **kwargs):
            if kwargs.get('timeout') == RuntimeJournal.LEASE_READ_TIMEOUT_S and not fired.is_set():
                fired.set()
                raise sqlite3.OperationalError('database is locked')
            return real_connect(path, *args, **kwargs)

        with patch('residual.factory.runtime_journal.sqlite3.connect', side_effect=flaky_connect):
            _, result = self.run_source("write_file('output.txt', 'fine')")
        self.assertTrue(fired.is_set(), 'injection did not reach the lease read path')
        self.assertEqual(result.status, 'CANDIDATE', result)
        violations = [e for e in self.events() if e['event'] == 'ContractViolation']
        self.assertEqual(violations, [])
        self.assertFalse(any(e.get('boundary') == 'lease' for e in self.events()))
        self.assertFalse(any('lease_unreadable' in json.dumps(e) for e in self.events()))


class SingleDeadlineOwnerTests(Fixture):
    """H2/H3: the guard owns started/deadline; the watchdog uses a snapshot."""

    def test_guard_owns_started_and_deadline(self):
        contract = self.contract(wall_clock_budget_s=7)
        guard = AttemptGuard(contract, observe=self.journal.observe,
                             terminate=lambda: None, clock=lambda: 100.0)
        self.assertIsNone(guard.started_at)
        self.assertIsNone(guard.deadline)
        guard.start()
        self.assertEqual(guard.started_at, 100.0)
        self.assertEqual(guard.deadline, 107.0)

    def test_fake_clock_watchdog_kills_past_deadline_snapshot(self):
        runtime = self.runtime
        ticks = [10.0]

        def fake_clock():
            return ticks[0]

        runtime._clock = fake_clock
        control = SimpleNamespace(termination_requested=threading.Event(),
                                  exited=lambda: False,
                                  process=SimpleNamespace(pid=12345, poll=lambda: None),
                                  kill=Mock())
        done = threading.Event()
        completing = threading.Event()
        with patch.object(self.journal, 'lease_state', return_value='current'):
            with patch.object(Path, 'read_text', return_value='1 1'):
                def advance():
                    time.sleep(0.1)
                    ticks[0] = 200.0  # jump past the 50.0 deadline snapshot
                thread = threading.Thread(target=advance, daemon=True)
                thread.start()
                runtime._watch(control, self.contract(), 50.0, done, completing)
                thread.join()
        control.kill.assert_called_once()
        reason = control.kill.call_args[0][0]
        self.assertEqual(reason[0], 'resource')
        self.assertEqual(reason[1], 'wall_clock_budget_s')

    def test_watchdog_skips_wall_clock_once_exchange_completing(self):
        control = SimpleNamespace(termination_requested=threading.Event(),
                                  exited=lambda: False,
                                  process=SimpleNamespace(pid=12345, poll=lambda: None),
                                  kill=Mock())
        done = threading.Event()
        completing = threading.Event()
        completing.set()
        threading.Timer(0.2, done.set).start()
        with patch.object(self.journal, 'lease_state', return_value='current'):
            with patch.object(Path, 'read_text', return_value='1 1'):
                # Deadline (1.0) already in the past, yet completion in
                # progress: wall-clock enforcement must not fire.
                self.runtime._watch(control, self.contract(), 1.0, done, completing)
        control.kill.assert_not_called()


class WatchdogDeadlineSnapshotTests(Fixture):
    """The watchdog must enforce the guard-owned deadline snapshot taken AFTER
    guard.start(); it must never recompute its own deadline at poll time."""

    def test_watchdog_kills_at_snapshot_not_recomputed_deadline(self):
        contract = self.contract(wall_clock_budget_s=30)
        ticks = [1000.0]

        def fake_clock():
            return ticks[0]

        guard = AttemptGuard(contract, observe=self.journal.observe,
                             terminate=lambda: None, clock=fake_clock)
        guard.start()
        # The injected clock ADVANCES between guard.start() and the watchdog's
        # first poll, past the guard-owned deadline snapshot. A watchdog that
        # recomputed `clock() + budget` at poll time would instead produce a
        # deadline 30s in the future (no kill / a much later kill), and one
        # that killed at `now` would report ~0 elapsed.
        ticks[0] = 1000.0 + 30.0 + 0.25
        deadline = guard.deadline
        self.assertEqual(deadline, 1030.0)
        self.runtime._clock = fake_clock
        control = SimpleNamespace(termination_requested=threading.Event(),
                                  exited=lambda: False,
                                  process=SimpleNamespace(pid=12345, poll=lambda: None),
                                  kill=Mock())
        done = threading.Event()
        completing = threading.Event()
        # Bound the loop so a broken (recomputing) watchdog fails fast here
        # instead of hanging: with the snapshot semantics the kill fires on
        # the very first poll, long before this timer.
        threading.Timer(0.5, done.set).start()
        started = time.monotonic()
        with patch.object(self.journal, 'lease_state', return_value='current'):
            with patch.object(Path, 'read_text', return_value='1 1'):
                self.runtime._watch(control, contract, deadline, done, completing)
        wall = time.monotonic() - started
        control.kill.assert_called_once()
        reason = control.kill.call_args[0][0]
        self.assertEqual(reason[:2], ('resource', 'wall_clock_budget_s'))
        # Elapsed is measured from the guard-owned start instant (1000.0):
        # 1030.25 - 1000.0. A recomputed deadline would yield ~0 or a kill
        # delayed by the full 30s budget.
        self.assertAlmostEqual(reason[2]['elapsed_s'], 30.25, places=2)
        self.assertLess(wall, 5.0)


class ReapTimeoutProvenanceTests(unittest.TestCase):
    """M6: a reap TimeoutExpired is typed (reap_timed_out event plus the
    ('resource', 'reap_timeout') reason when no primary reason exists) and
    never escapes the caller."""

    def _control(self):
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        control = ProcessControl(process, correlation_id='reap-timeout-test')
        self.addCleanup(self._cleanup, control, process)
        return control

    @staticmethod
    def _cleanup(control, process):
        try:
            process.kill()
        except Exception:
            pass
        try:
            if not control.reaped:
                control.reap(timeout=5)
        except Exception:
            pass
        try:
            if control.reaped:
                control.close()
        except Exception:
            pass

    def test_reap_timeout_emits_typed_event_and_reason(self):
        control = self._control()
        # Force the consuming wait to time out: the pidfd never becomes ready,
        # so ProcessControl.reap() raises subprocess.TimeoutExpired.
        with patch('residual.factory.termination_provenance.select.select',
                   return_value=([], [], [])):
            try:
                control.kill(None, requester='runtime')
            except Exception as exc:  # (c) nothing may escape the caller
                self.fail(f'reap timeout escaped the caller: {exc!r}')
        # (a) the typed reap_timed_out event is recorded
        self.assertTrue(control.reap_timed_out.is_set())
        # (b) with no primary reason, the distinct reap_timeout reason is set
        self.assertEqual(control.reason, ('resource', 'reap_timeout', {'timeout_s': 2}))
        self.assertEqual(control.requested_by, 'runtime')
        self.assertIsNotNone(control.requested_monotonic_ns)
        self.assertTrue(control.stopped.is_set())

    def test_reap_timeout_does_not_overwrite_primary_reason(self):
        control = self._control()
        primary = ('guard', 'contract_violation', {'reason': 'guard_stop_hook'})
        with patch('residual.factory.termination_provenance.select.select',
                   return_value=([], [], [])):
            control.kill(primary, requester='guard')
        # The timeout is still typed, but an existing primary reason wins.
        self.assertTrue(control.reap_timed_out.is_set())
        self.assertEqual(control.reason, primary)
        self.assertEqual(control.requested_by, 'guard')


class SeccompProbe:
    @staticmethod
    def available() -> bool:
        source = json.dumps({'source': 'pass'}) + '\n' + '{"sequence":1,"ok":true}\n'
        try:
            probe = subprocess.run(
                [sys.executable, '-I', '-S', str(ROOT / 'residual/factory/_sandbox_child.py'),
                 '128', '3', str(os.getpid())], input=source.encode(),
                capture_output=True, timeout=5, env={'PATH': '/usr/bin:/bin'})
        except Exception:
            return False
        return probe.returncode == 0 and b'SandboxReady' in probe.stdout


SECCOMP = SeccompProbe.available()


@unittest.skipUnless(SECCOMP, 'libseccomp/kernel backend unavailable (no fallback)')
class TypedOutcomeDeterminismTests(Fixture):
    def test_closed_fds_then_spin_single_typed_outcome(self):
        # A worker that closes its protocol fds and then spins must produce
        # exactly one typed outcome: VIOLATED / wall_clock_budget_s / SIGKILL,
        # identical across repetitions.
        source = 'import os\nos.close(1)\nos.close(2)\nwhile True: pass'
        outcomes = []
        for _ in range(3):
            _, result = self.run_source(source, wall_clock_budget_s=0.5)
            outcomes.append((result.status, result.reason, result.returncode))
        self.assertEqual(outcomes, [('VIOLATED', 'wall_clock_budget_s', -signal.SIGKILL)] * 3)

    def test_n10_determinism_proof_three_worker_corpus(self):
        corpus = [
            ("write_file('output.txt', 'ok')", {}),
            ('while True: pass', {'wall_clock_budget_s': 0.3}),
            ("read_file('secret.txt')", {}),
        ]
        table = []
        for _iteration in range(10):
            row = []
            for source, overrides in corpus:
                contract, result = self.run_source(source, **overrides)
                row.append((result.status, result.reason, result.returncode))
                if result.status == 'CANDIDATE':
                    self.runtime.purge(contract)  # free the task slot for the next round
            table.append(tuple(row))
        first = table[0]
        for row in table:
            self.assertEqual(row, first)
        self.assertEqual(first[0], ('CANDIDATE', 'awaiting_station_verification', 0))
        self.assertEqual(first[1], ('VIOLATED', 'wall_clock_budget_s', -signal.SIGKILL))
        self.assertEqual(first[2], ('VIOLATED', 'inputs', -signal.SIGKILL))

    def test_cancel_after_publication_returns_false(self):
        contract, result = self.run_source("write_file('output.txt', 'ok')")
        self.assertEqual(result.status, 'CANDIDATE')
        self.assertFalse(self.runtime.cancel(contract.attempt_id))

    def test_cancel_only_true_for_own_primary_cancellation(self):        # Journal says RUNNING but the recorded primary reason is a watchdog
        # violation: cancel must NOT claim the terminal outcome.
        contract = self.contract()
        self.journal.claim(contract, source_hash='a' * 64, approval=self.approval.to_dict())
        self.journal.started(contract, 12345)
        control = SimpleNamespace(
            reason=('resource', 'wall_clock_budget_s', {'elapsed_s': 9.0}),
            kill=Mock(),
        )
        with self.runtime._lock:
            self.runtime._active[contract.attempt_id] = control
        try:
            self.assertFalse(self.runtime.cancel(contract.attempt_id))
        finally:
            with self.runtime._lock:
                self.runtime._active.pop(contract.attempt_id, None)
        # The attempt was revoked (fence) even though cancel reported False.
        self.assertEqual(self.journal.lease_state(contract), 'revoked')

    def test_cancel_race_terminal_cancelled_with_own_reason_is_true(self):
        # Regression: kill lands, the run thread finishes CANCELLED before
        # cancel()'s revoke executes. revoke raises JournalError, yet cancel
        # must still report True (it IS our own cancellation).
        contract = self.contract()
        self.journal.claim(contract, source_hash='a' * 64, approval=self.approval.to_dict())
        self.journal.started(contract, 12345)
        self.journal.finish(contract, 'CANCELLED', reason='operator_cancel')
        control = SimpleNamespace(
            reason=('cancellation', 'operator_cancel', {'reason': 'local_operator'}),
            kill=Mock(),
        )
        with self.runtime._lock:
            self.runtime._active[contract.attempt_id] = control
        try:
            self.assertTrue(self.runtime.cancel(contract.attempt_id))
        finally:
            with self.runtime._lock:
                self.runtime._active.pop(contract.attempt_id, None)

    def test_cancel_race_published_candidate_with_control_still_false(self):
        # A published CANDIDATE must return False even if a stale control is
        # still registered in _active.
        contract = self.contract()
        self.journal.claim(contract, source_hash='a' * 64, approval=self.approval.to_dict())
        self.journal.started(contract, 12345)
        self.journal.finish(contract, 'CANDIDATE', reason='awaiting_station_verification')
        control = SimpleNamespace(reason=None, kill=Mock())
        with self.runtime._lock:
            self.runtime._active[contract.attempt_id] = control
        try:
            self.assertFalse(self.runtime.cancel(contract.attempt_id))
        finally:
            with self.runtime._lock:
                self.runtime._active.pop(contract.attempt_id, None)
        self.assertEqual(self.journal.attempts()[0]['state'], 'CANDIDATE')


@unittest.skipUnless(ISOLATED, 'kernel namespace isolation unavailable on this platform')
class IsolatedTimeoutTypingTests(unittest.TestCase):
    """H4/M5: typed TIMEOUT extends the M4 exit-code convention."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.worktree = Path(self.temp.name) / 'worktree'
        self.worktree.mkdir()

    def test_timeout_is_distinct_typed_outcome(self):
        python = '/usr/bin/python3'
        timed = m4_sandbox.run_isolated(
            (python, '-c', 'import time; time.sleep(30)'), self.worktree,
            timeout_s=1, output_limit=1 << 16)
        self.assertEqual(timed.status, 'timeout')
        self.assertEqual(timed.returncode, m4_sandbox.SANDBOX_TIMEOUT_EXIT)
        self.assertEqual(timed.returncode, 124)
        self.assertTrue(timed.timed_out)
        self.assertEqual(timed.reason, 'timeout')
        # Distinct from a candidate FAIL and from sandbox ERROR (125).
        failed = m4_sandbox.run_isolated(
            (python, '-c', 'import sys; sys.exit(1)'), self.worktree,
            timeout_s=20, output_limit=1 << 16)
        self.assertEqual(failed.status, 'fail')
        self.assertEqual(failed.returncode, 1)
        self.assertFalse(failed.timed_out)
        self.assertNotEqual(failed.returncode, 124)


class FixtureLaneTimeoutTypingTests(unittest.TestCase):
    def test_fixture_timeout_is_typed_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_trusted_fixture(
                (sys.executable, '-c', 'import time; time.sleep(30)'),
                Path(directory), timeout_s=1, output_limit=1024)
        self.assertEqual(result.status, 'timeout')
        self.assertTrue(result.timed_out)
        self.assertEqual(result.reason, 'timeout')


class IntegratorTimeoutTypingTests(unittest.TestCase):
    def test_verification_timeout_is_timeout_not_fail(self):
        from residual.factory.evidence_bus import EvidenceBus
        from residual.factory.evidence_receipts import StationIdentity
        from residual.factory.m4_integrator import (
            DeterministicIntegrator, ProjectVerificationPolicy, VerificationCommand,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / 'repo'
            repo.mkdir()
            identity = StationIdentity.generate()
            integrator = DeterministicIntegrator(
                repo, root / 'integration', EvidenceBus(root / 'bus.sqlite'),
                station_public_key=identity.public_bytes(), observe=lambda event: None)
            policy = ProjectVerificationPolicy(commands=(
                VerificationCommand('slow', 'full_test_suite',
                                    (sys.executable, '-c', 'import time; time.sleep(30)'),
                                    timeout_s=1, max_output_bytes=1024),
                VerificationCommand('types', 'type_check', ('/usr/bin/true',), timeout_s=5,
                                    max_output_bytes=1024),
                VerificationCommand('contracts', 'contract_validation', ('/usr/bin/true',),
                                    timeout_s=5, max_output_bytes=1024),
            ), trusted_fixture_mode=True)
            results = integrator._run_verification(repo, policy)
        self.assertEqual(len(results), 1)  # stops at the first non-pass
        timed = results[0]
        self.assertEqual(timed.status, 'timeout')
        self.assertTrue(timed.timed_out)
        self.assertEqual(timed.termination_reason, 'timeout')
        self.assertNotEqual(timed.status, 'fail')
        self.assertTrue(timed.to_dict()['timed_out'])


class TypedGitTimeoutTests(Fixture):
    """M9: managed git operations raise a typed timeout, never raw TimeoutExpired."""

    def test_git_timeout_is_typed(self):
        real_run = subprocess.run

        def slow_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd='git', timeout=20)

        with patch('residual.factory.runtime_workspace.subprocess.run', side_effect=slow_run):
            with self.assertRaises(GitOperationTimeout):
                from residual.factory.runtime_workspace import git
                git(self.repo, 'status')
        self.assertTrue(issubclass(GitOperationTimeout, WorkerContractError))
        self.assertTrue(callable(real_run))


if __name__ == '__main__':
    unittest.main()
