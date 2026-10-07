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
from residual.factory.runtime_journal import LeaseRead, RuntimeJournal
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
        # Store failure: unknown, and ONLY on sqlite3.Error. The diagnostic is
        # returned atomically WITH the state, never via journal-global state.
        with patch('residual.factory.runtime_journal.sqlite3.connect',
                   side_effect=sqlite3.OperationalError('database is locked')):
            self.assertEqual(self.journal.lease_state(contract), 'unknown')
            read = self.journal.lease_read(contract)
            self.assertEqual(read.state, 'unknown')
            self.assertEqual(read.diag[0], 'OperationalError')
            self.assertIsInstance(read.diag[1], int)
        self.assertTrue(callable(real_connect := sqlite3.connect))

    def test_lease_read_binds_diag_per_call_not_journal_global(self):
        # Review blocker 4: no mutable journal-global diagnostic exists; a
        # concurrent attempt's failed read cannot overwrite this attempt's
        # provenance.
        self.assertFalse(hasattr(self.journal, 'lease_read_diag'),
                         'journal-global lease_read_diag must not exist')
        contract = self.contract()
        errors = [sqlite3.OperationalError('locked'), sqlite3.DatabaseError('disk')]
        reads = []
        with patch('residual.factory.runtime_journal.sqlite3.connect',
                   side_effect=errors):
            reads.append(self.journal.lease_read(contract))
            reads.append(self.journal.lease_read(contract))
        self.assertEqual([r.state for r in reads], ['unknown', 'unknown'])
        # Each read carries ITS OWN diagnostic; no cross-attribution.
        self.assertEqual(reads[0].diag[0], 'OperationalError')
        self.assertEqual(reads[1].diag[0], 'DatabaseError')

    def test_lease_read_deadline_caps_busy_budget(self):
        # Review blocker 2 (journal side): with an exhausted caller deadline
        # the read must not touch the store at all, and a live deadline caps
        # the SQLite busy budget at the remaining time.
        contract = self.contract()
        read = self.journal.lease_read(contract, deadline=time.monotonic() - 1)
        self.assertEqual(read.state, 'unknown')
        self.assertEqual(read.diag[0], 'read_budget_exhausted')
        budgets = []
        real_connect = sqlite3.connect

        def spy_connect(path, *args, **kwargs):
            budgets.append(kwargs.get('timeout'))
            return real_connect(path, *args, **kwargs)

        deadline = time.monotonic() + 1.0
        with patch('residual.factory.runtime_journal.sqlite3.connect', side_effect=spy_connect):
            self.journal.lease_read(contract, deadline=deadline)
        self.assertEqual(len(budgets), 1)
        # Budget was capped by the remaining deadline (< 1.0s), not the full
        # 2s default; the +0.1 covers scheduling granularity only.
        self.assertLessEqual(budgets[0], 1.0 + 0.1)
        self.assertLess(budgets[0], RuntimeJournal.LEASE_READ_TIMEOUT_S)

    def test_one_shot_locked_read_does_not_kill_or_retype(self):
        # A single transient 'database is locked' on the lease read path must
        # NOT kill the worker — and must never be retyped as lease_generation.
        fired = threading.Event()
        real_connect = sqlite3.connect

        def flaky_connect(path, *args, **kwargs):
            timeout = kwargs.get('timeout')
            # The lease read path is the bounded one (budget <= the 2s lease
            # read cap); journal writers (0.2s) and bulk readers (5s) differ.
            if isinstance(timeout, float) and 0.2 < timeout <= RuntimeJournal.LEASE_READ_TIMEOUT_S \
                    and not fired.is_set():
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
        with patch.object(self.journal, 'lease_read', return_value=LeaseRead('current')):
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
        with patch.object(self.journal, 'lease_read', return_value=LeaseRead('current')):
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
        with patch.object(self.journal, 'lease_read', return_value=LeaseRead('current')):
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
        # (c) review blocker 3: `stopped` is evidence of an actually reaped
        # process. A reap timeout leaves the child possibly live, so stopped
        # MUST stay clear and the record must still be refused.
        self.assertFalse(control.reaped)
        self.assertFalse(control.stopped.is_set())
        with self.assertRaises(RuntimeError):
            control.termination_record()

    def test_reap_timeout_then_successful_followup_reap_restores_invariants(self):
        # Review blocker 3 (lifecycle): after a reap timeout, a mandatory
        # follow-up reap restores the stopped/reaped invariant exactly once
        # the process is actually reaped.
        control = self._control()
        with patch('residual.factory.termination_provenance.select.select',
                   return_value=([], [], [])):
            control.kill(None, requester='runtime')
        self.assertFalse(control.stopped.is_set())
        self.assertFalse(control.reaped)
        # The child was SIGKILLed (signal sent before the timed-out wait); a
        # follow-up reap now completes and only NOW sets stopped.
        returncode = control.reap(timeout=5)
        self.assertEqual(returncode, -signal.SIGKILL)
        self.assertTrue(control.reaped)
        self.assertTrue(control.stopped.is_set())
        record = control.termination_record()
        self.assertEqual(record.observed_signal, signal.SIGKILL)

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
        # Review blocker 5: the documented deterministic returncode-124
        # contract holds in the trusted-fixture lane too (never the killed
        # child's signal code).
        self.assertEqual(result.returncode, 124)
        self.assertEqual(result.returncode, m4_sandbox.SANDBOX_TIMEOUT_EXIT)
        # A fixture legitimately exiting 124 on its own is typed FAIL with
        # timed_out False — same disambiguation as the isolated lane.
        with tempfile.TemporaryDirectory() as directory:
            exited = run_trusted_fixture(
                (sys.executable, '-c', 'import sys; sys.exit(124)'),
                Path(directory), timeout_s=20, output_limit=1024)
        self.assertEqual(exited.status, 'fail')
        self.assertEqual(exited.returncode, 124)
        self.assertFalse(exited.timed_out)


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
        # The runtime attribute is set; the signed v2 receipt payload encodes
        # the timeout through status/termination_reason/returncode (124) —
        # timed_out is deliberately NOT a payload key (v2 bytes frozen).
        self.assertTrue(timed.timed_out)
        payload = timed.to_dict()
        self.assertNotIn('timed_out', payload)
        self.assertEqual(payload['termination_reason'], 'timeout')
        self.assertEqual(payload['status'], 'timeout')
        self.assertEqual(payload['returncode'], 124)


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


class LeaseUnknownBoundedDeadlineTests(Fixture):
    """Review blocker 2: ONE absolute deadline bounds the whole lease-unknown
    gate, including the FIRST read and every retry's SQLite busy budget."""

    def test_persistent_contention_bounded_by_single_deadline(self):
        # Every read consumes its full busy budget (persistent contention).
        # The advertised 2s bound must cover ALL of it: first read + retries.
        contract = self.contract()
        calls = []

        def stuck_read(c, *, deadline=None, clock=None):
            calls.append(deadline)
            time.sleep(RuntimeJournal.LEASE_READ_TIMEOUT_S)  # consume the budget
            return LeaseRead('unknown', ('OperationalError', 5))

        started = time.monotonic()
        with patch.object(self.journal, 'lease_read', side_effect=stuck_read):
            denial = self.runtime._lease_denial(contract, 'revoked_or_unavailable')
        elapsed = time.monotonic() - started
        self.assertIsNotNone(denial)
        self.assertEqual(denial[:2], ('lease', 'lease_unreadable'))
        self.assertEqual(denial[2]['read_error_type'], 'OperationalError')
        self.assertEqual(denial[2]['sqlite_errorcode'], 5)
        # The first read alone consumed the entire 2s window; no second
        # full-budget read may be issued. Pre-repair code started its own 2s
        # deadline only AFTER the first 2s read returned (>= 4s total).
        self.assertEqual(len(calls), 1)
        self.assertLess(elapsed, RuntimeJournal.LEASE_READ_TIMEOUT_S + 2.0)

    def test_retry_recovers_before_deadline_without_kill(self):
        contract = self.contract()
        self.journal.claim(contract, source_hash='a' * 64, approval=self.approval.to_dict())
        responses = iter([LeaseRead('unknown', ('OperationalError', 5)),
                          LeaseRead('unknown', ('OperationalError', 5)),
                          LeaseRead('current')])

        def flaky(c, *, deadline=None, clock=None):
            return next(responses)

        with patch.object(self.journal, 'lease_read', side_effect=flaky):
            self.assertIsNone(self.runtime._lease_denial(contract, 'revoked_or_unavailable'))

    def test_unknown_diag_is_atomic_per_attempt(self):
        # Review blocker 4 (runtime side): the denial action embeds the
        # diagnostic bound to THIS attempt's read object — no journal-global
        # state is consulted.
        contract = self.contract()
        with patch.object(self.journal, 'lease_read',
                          return_value=LeaseRead('unknown', ('OperationalError', 5))):
            denial = self.runtime._lease_denial(contract, 'revoked_or_unavailable')
        self.assertEqual(denial[:2], ('lease', 'lease_unreadable'))
        self.assertEqual((denial[2]['read_error_type'], denial[2]['sqlite_errorcode']),
                         ('OperationalError', 5))


class JournalContentionReadTests(Fixture):
    """CI SQLite-lock repair: expected observation/status reads must not fail
    merely because another runtime path holds a SQLite transaction."""

    def test_observations_retry_transient_lock_then_succeed(self):
        # Deterministic revert-proof: with the pre-repair single-shot 0.2s
        # reader (no retry), the first locked attempt raises and this test
        # fails; with the bounded retry read path the read recovers.
        self.journal.observe({'event': 'Probe', 'n': 1})
        attempts = []
        real_connect = sqlite3.connect

        def contended(path, *args, **kwargs):
            attempts.append(1)
            if len(attempts) <= 2:
                raise sqlite3.OperationalError('database is locked')
            return real_connect(path, *args, **kwargs)

        with patch('residual.factory.runtime_journal.sqlite3.connect',
                   side_effect=contended):
            observations = self.journal.observations()
        self.assertEqual(len(attempts), 3)
        self.assertTrue(any(o.payload.get('event') == 'Probe' for o in observations))

    def test_observations_bounded_failure_under_persistent_lock(self):
        # Persistent contention: the read fails only after the bounded 5s
        # budget, never immediately, and raises the sqlite error (fail-closed).
        with patch('residual.factory.runtime_journal.sqlite3.connect',
                   side_effect=sqlite3.OperationalError('database is locked')):
            started = time.monotonic()
            with self.assertRaises(sqlite3.OperationalError):
                self.journal.observations()
            elapsed = time.monotonic() - started
        self.assertGreaterEqual(elapsed, RuntimeJournal.READ_CONNECT_TIMEOUT_S - 0.5)
        self.assertLess(elapsed, RuntimeJournal.READ_CONNECT_TIMEOUT_S + 5.0)

    def test_observations_under_held_wal_writer_lock(self):
        # Real WAL characterization: a held BEGIN IMMEDIATE writer does not
        # block readers at all — observations() serves the pre-transaction
        # snapshot while the writer lock is held.
        self.journal.observe({'event': 'BeforeLock'})
        holder = sqlite3.connect(self.journal.path, isolation_level=None)
        self.addCleanup(holder.close)
        holder.execute('BEGIN IMMEDIATE')
        try:
            events = [o.payload.get('event') for o in self.journal.observations()]
            self.assertIn('BeforeLock', events)
            rows = self.journal.attempts()
            self.assertEqual(rows, [])
        finally:
            holder.execute('ROLLBACK')

    def test_readiness_polling_survives_concurrent_writer(self):
        # Mirrors the failed CI scenario (test_lease_revocation_kills_with_
        # lease_generation): wait_active()-style observations() polling from a
        # reader thread while the runtime writes journal events must not raise.
        errors = []
        stop = threading.Event()

        def poll():
            while not stop.is_set():
                try:
                    self.journal.observations()
                except Exception as exc:  # noqa: BLE001 - record, assert below
                    errors.append(exc)
                    return

        reader = threading.Thread(target=poll, daemon=True)
        reader.start()
        try:
            _, result = self.run_source("write_file('output.txt', 'fine')")
        finally:
            stop.set()
            reader.join(timeout=15)
        self.assertFalse(reader.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(result.status, 'CANDIDATE', result)


if __name__ == '__main__':
    unittest.main()
