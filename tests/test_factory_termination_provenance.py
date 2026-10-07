"""Direct process-ownership tests: mocked causal interleavings and real Linux children."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import FrozenInstanceError
import errno
import os
import select
import signal
import subprocess
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from residual.factory import termination_provenance as provenance


@unittest.skipUnless(sys.platform == 'linux', 'Linux process control')
class ProcessControlTests(unittest.TestCase):
    def control(self, returncode=0, *, code=None, status=None, ready=True):
        stack = self.enterContext(ExitStack())
        process = Mock(pid=12345, args=['fixture'], returncode=None)
        process.poll.side_effect = AssertionError('poll would consume exit status')
        def wait(timeout):
            process.returncode = returncode
            return returncode
        process.wait.side_effect = wait
        stack.enter_context(patch.object(provenance.os, 'pidfd_open', return_value=10))
        stack.enter_context(patch.object(provenance, '_proc_start_ticks', return_value=42))
        stack.enter_context(patch.object(provenance, '_boot_id', return_value='boot-fixture'))
        stack.enter_context(patch.object(provenance, '_cgroup_memory_events', return_value={'oom_kill': 0}))
        self.probe = stack.enter_context(patch.object(provenance.select, 'select', return_value=([10] if ready else [], [], [])))
        self.send = stack.enter_context(patch.object(provenance.signal, 'pidfd_send_signal'))
        self.close_fd = stack.enter_context(patch.object(provenance.os, 'close'))
        if code is None:
            code = os.CLD_KILLED if returncode < 0 else os.CLD_EXITED
        if status is None:
            status = abs(returncode)
        self.waitid = stack.enter_context(patch.object(provenance.os, 'waitid', return_value=SimpleNamespace(si_code=code, si_status=status)))
        clock = iter(range(100, 1000))
        control = provenance.ProcessControl(process, correlation_id='attempt-fixture', clock_ns=lambda: next(clock))
        return control, process

    def test_identity_is_bound_and_immutable(self):
        c, _ = self.control()
        self.assertEqual(c.identity.to_dict(), {'correlation_id':'attempt-fixture', 'pid':12345, 'pid_start_time_ticks':42, 'boot_id':'boot-fixture'})
        with self.assertRaises(FrozenInstanceError):
            c.identity.pid = 9

    def test_kill_records_request_before_signal_and_reap(self):
        c, p = self.control(-signal.SIGKILL)
        self.probe.side_effect = [([], [], []), ([10], [], [])]
        reason = ('resource', 'wall_clock_budget_s', {'elapsed_s': 2})
        def check_send(fd, sig):
            self.assertEqual((fd, sig), (10, signal.SIGKILL))
            self.assertTrue(c.termination_requested.is_set())
            self.assertEqual(c.reason, reason)
            self.assertEqual(c.requested_by, 'watchdog')
            self.assertIsNotNone(c.requested_monotonic_ns)
            p.wait.assert_not_called()
        self.send.side_effect = check_send
        c.kill(reason, requester='watchdog')
        r = c.termination_record()
        self.assertEqual(r.classification, 'watchdog_wall_clock')
        self.assertLessEqual(r.requested_monotonic_ns, r.observed_monotonic_ns)
        self.assertLessEqual(r.observed_monotonic_ns, r.reaped_monotonic_ns)
        self.assertTrue(c.stopped.is_set())

    def test_reasonless_kill_still_records_host_intent(self):
        c, _ = self.control(-signal.SIGKILL)
        self.probe.side_effect = [([], [], []), ([10], [], [])]
        c.kill()
        self.assertEqual(c.termination_record().classification, 'runtime_cleanup')
        self.assertIsNone(c.termination_record().request_field)
        self.assertEqual(c.termination_record().requested_by, 'runtime')

    def test_reap_is_idempotent_and_only_consuming_path(self):
        c, p = self.control(7)
        self.assertEqual(c.reap(), 7)
        p.returncode = 99  # an external mutation cannot rewrite retained evidence
        self.assertEqual(c.reap(), 7)
        p.wait.assert_called_once()
        p.poll.assert_not_called()
        self.assertEqual(c.termination_record().returncode, 7)
        self.assertEqual(self.waitid.call_args.args[2] & os.WNOWAIT, os.WNOWAIT)

    def test_exited_is_non_consuming(self):
        c, p = self.control()
        self.probe.side_effect = [([], [], []), ([10], [], [])]
        self.assertFalse(c.exited())
        self.assertTrue(c.exited())
        self.assertFalse(c.reaped)
        p.wait.assert_not_called()
        p.poll.assert_not_called()

    def test_probe_holds_state_lock_through_syscall(self):
        c, _ = self.control()
        def try_other_thread():
            acquired = c._state_lock.acquire(blocking=False)
            if acquired:
                c._state_lock.release()
            return acquired
        with ThreadPoolExecutor(max_workers=1) as pool:
            def probe(*_):
                self.assertFalse(pool.submit(try_other_thread).result(timeout=2), 'descriptor probe lost ownership lock')
                return ([], [], [])
            self.probe.side_effect = probe
            self.assertFalse(c.exited())

    def test_bad_descriptor_is_not_treated_as_exit(self):
        c, p = self.control()
        self.probe.side_effect = OSError(errno.EBADF, 'fixture')
        with self.assertRaises(OSError):
            c.exited()
        self.assertFalse(c.reaped)
        p.wait.assert_not_called()

    def test_close_before_reap_is_rejected_without_losing_fd(self):
        c, _ = self.control()
        with self.assertRaisesRegex(RuntimeError, 'before reap'):
            c.close()
        self.assertEqual(c.pidfd, 10)
        self.close_fd.assert_not_called()

    def test_close_is_idempotent_after_reap(self):
        c, _ = self.control()
        c.reap()
        c.close()
        c.close()
        c.kill(('late', 'late', {}), requester='operator')
        self.close_fd.assert_called_once_with(10)
        self.assertTrue(c.exited())
        self.send.assert_not_called()

    def test_termination_record_requires_reaped_process(self):
        c, _ = self.control()
        with self.assertRaisesRegex(RuntimeError, 'requires a reaped'):
            c.termination_record()

    def test_late_kill_preserves_already_exited_signal_and_has_no_requester(self):
        c, p = self.control(-signal.SIGSYS)
        c.kill(('resource', 'wall_clock_budget_s', {}), requester='watchdog')
        r = c.termination_record()
        self.assertEqual(r.classification, 'kernel_sigsys')
        self.assertIsNone(r.requested_by)
        self.assertIsNone(r.requested_monotonic_ns)
        self.assertFalse(c.termination_requested.is_set())
        p.wait.assert_called_once()
        self.send.assert_not_called()

    def test_exit_winning_signal_race_does_not_become_watchdog_kill(self):
        for rc in (0, 7, -signal.SIGSYS, -signal.SIGTERM, -signal.SIGKILL):
            with self.subTest(returncode=rc):
                c, _ = self.control(rc)
                self.probe.side_effect = [([], [], []), ([10], [], [])]
                self.send.side_effect = ProcessLookupError(errno.ESRCH, 'fixture exit race')
                c.kill(('resource', 'wall_clock_budget_s', {}), requester='watchdog')
                r = c.termination_record()
                self.assertEqual(r.requested_by, 'watchdog')  # intent remains visible
                self.assertEqual(r.classification, {0:'clean_exit',7:'process_exit_nonzero',-signal.SIGSYS:'kernel_sigsys',-signal.SIGTERM:'external_signal',-signal.SIGKILL:'unknown_sigkill'}[rc])

    def test_successful_send_still_cannot_explain_sigsys_or_normal_exit(self):
        for rc, expected in ((0, 'clean_exit'), (-signal.SIGSYS, 'kernel_sigsys')):
            with self.subTest(returncode=rc):
                c, _ = self.control(rc)
                self.probe.side_effect = [([], [], []), ([10], [], [])]
                c.kill(('resource', 'wall_clock_budget_s', {}), requester='watchdog')
                self.assertEqual(c.termination_record().classification, expected)

    def test_waitid_handles_killed_dumped_and_exited(self):
        for code, status, rc, expected in ((os.CLD_KILLED,signal.SIGSYS,-signal.SIGSYS,'kernel_sigsys'),(os.CLD_DUMPED,signal.SIGSYS,-signal.SIGSYS,'kernel_sigsys'),(os.CLD_EXITED,137,137,'process_exit_nonzero')):
            with self.subTest(code=code):
                c, _ = self.control(rc, code=code, status=status)
                c.reap()
                self.assertEqual(c.termination_record().classification, expected)

    def test_contradictory_wait_results_remain_unknown_and_keep_both(self):
        c, _ = self.control(0, code=os.CLD_KILLED, status=signal.SIGKILL)
        c.reap()
        r = c.termination_record()
        self.assertEqual(r.classification, 'unknown_wait_status')
        self.assertEqual((r.returncode, r.waitid_code, r.waitid_status), (0, os.CLD_KILLED, signal.SIGKILL))
        self.assertEqual(r.observed_signal, signal.SIGKILL)

    def test_invalid_waitid_code_is_not_clean_exit(self):
        c, _ = self.control(0, code=os.CLD_STOPPED, status=signal.SIGSTOP)
        c.reap()
        self.assertEqual(c.termination_record().classification, 'unknown_wait_status')

    def test_unavailable_waitid_falls_back_to_reaped_status(self):
        c, _ = self.control(-signal.SIGSYS)
        self.waitid.side_effect = OSError(errno.ENOSYS, 'not supported')
        c.reap()
        r = c.termination_record()
        self.assertEqual(r.classification, 'kernel_sigsys')
        self.assertIsNone(r.waitid_code)

    def test_lost_child_ownership_is_not_fallback_success(self):
        c, _ = self.control(0)
        self.waitid.side_effect = ChildProcessError(errno.ECHILD, 'already reaped elsewhere')
        c.reap()
        self.assertEqual(c.termination_record().classification, 'unknown_wait_status')

    def test_shared_cgroup_oom_activity_is_not_process_attribution(self):
        c, _ = self.control(-signal.SIGKILL)
        with patch.object(provenance, '_cgroup_memory_events', return_value={'oom_kill': 1}):
            c.reap()
        r = c.termination_record()
        self.assertEqual(r.classification, 'unknown_sigkill_with_cgroup_oom_activity')
        self.assertIsNone(r.requested_by)

    def test_record_is_frozen_once_and_nested_exports_are_detached(self):
        c, _ = self.control(-signal.SIGKILL)
        self.probe.side_effect = [([], [], []), ([10], [], [])]
        reason = ('guard', 'violation', {'nested': [{'value': 1}]})
        c.kill(reason, requester='guard')
        r = c.termination_record()
        reason[2]['nested'][0]['value'] = 99
        exported = r.to_dict()
        exported['request_action']['nested'][0]['value'] = 50
        self.assertIs(r, c.termination_record())
        self.assertEqual(r.request_action['nested'][0]['value'], 1)
        with self.assertRaises(TypeError):
            r.request_action['nested'][0]['value'] = 2
        with self.assertRaises(TypeError):
            r.cgroup_memory_events_before['oom_kill'] = 7

    def test_timeout_does_not_claim_reaped(self):
        c, p = self.control(ready=False)
        with self.assertRaises(subprocess.TimeoutExpired):
            c.reap(timeout=0)
        p.wait.assert_not_called()
        self.assertFalse(c.reaped)
        self.assertFalse(c.stopped.is_set())

    def test_concurrent_reap_allows_signal_and_consumes_once(self):
        c, p = self.control(-signal.SIGKILL)
        reaper_waiting, signal_sent = threading.Event(), threading.Event()
        def probe(_read, _write, _err, timeout):
            if timeout == 0:
                return ([], [], [])
            reaper_waiting.set()
            self.assertTrue(signal_sent.wait(2), 'blocking reap prevented watchdog signal')
            return ([10], [], [])
        self.probe.side_effect = probe
        self.send.side_effect = lambda *_: signal_sent.set()
        with ThreadPoolExecutor(max_workers=2) as pool:
            waiter = pool.submit(c.reap)
            self.assertTrue(reaper_waiting.wait(2))
            killer = pool.submit(c.kill, ('resource','wall_clock_budget_s',{}), requester='watchdog')
            self.assertEqual(waiter.result(timeout=4), -signal.SIGKILL)
            killer.result(timeout=4)
        p.wait.assert_called_once()
        self.send.assert_called_once()
        self.assertEqual(c.termination_record().classification, 'watchdog_wall_clock')


@unittest.skipUnless(sys.platform == 'linux' and hasattr(os, 'pidfd_open'), 'Linux pidfd')
class RealProcessControlTests(unittest.TestCase):
    def test_live_exit_reap_close_transitions(self):
        child = subprocess.Popen([sys.executable, '-I', '-S', '-c', 'import os; os.read(0, 1)'], stdin=subprocess.PIPE)
        control = provenance.ProcessControl(child, correlation_id='real-lifecycle')
        try:
            self.assertFalse(control.exited())
            child.stdin.write(b'x')
            child.stdin.flush()
            self.assertTrue(select.select([control.pidfd], [], [], 5)[0])
            self.assertTrue(control.exited())
            self.assertIsNone(child.returncode)  # neither observation consumed status
            self.assertEqual(control.reap(), 0)
            before = control.termination_record()
            control.kill(requester='operator')
            self.assertIs(control.termination_record(), before)
            self.assertEqual(before.classification, 'clean_exit')
            self.assertEqual(before.waitid_code, os.CLD_EXITED)
            control.close()
            control.close()
        finally:
            if not control.reaped:
                control.kill()
            control.close()
            child.stdin.close()
