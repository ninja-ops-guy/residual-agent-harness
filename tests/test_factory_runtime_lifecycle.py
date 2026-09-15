import json
import shutil
import subprocess
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from residual.core import strict_json
from residual.factory.cli import main
from residual.factory.runtime_journal import LeaseRead, RuntimeJournal
from residual.factory.runtime import main
from residual.factory.termination_provenance import ProcessControl
from residual.factory.worker_contract import WorkerContract, WorkerContractError
from tests.test_factory_runtime import Fixture, RUN_SOURCE


@patch('sys.argv', new=['factory-runtime', '--repo', '.', '--runtime-root', 'x', '--journal', 'j',
                        '--run-id', 'r', '--plan', 'p', '--approval', 'a', '--contract', 'c',
                        '--source', 's'])
def test_cli_rejects_unreadable_plan_with_bounded_error():
    assert main() == 1


class RuntimeLifecycleTests(Fixture):
    def test_cancel_only_true_for_own_observed_cancellation(self):
        def runner():
            self.result = self.runtime.run(self.plan(), self.approval, self.contract(),
                                           'import time\ntime.sleep(30)\n')
        self.journal.observe = self.pause_first_attempt(self.journal.observe)
        thread = self.spawn(runner)
        self.started.wait(10)
        attempt = self.journal.attempts()[0]['attempt_id']
        self.assertTrue(self.runtime.cancel(attempt))
        thread.join(10)
        self.assertEqual(self.result.status, 'CANCELLED')
        # A second cancel after the terminal transition is not a cancellation.
        self.assertFalse(self.runtime.cancel(attempt))
        row = self.journal.attempts()[0]
        self.assertTrue(row['revoked'])
        self.assertEqual(row['state'], 'CANCELLED')
        # The recorded primary reason is the cancellation itself.
        self.assertEqual(self.result.termination['request_boundary'], 'cancellation')
        self.assertEqual(self.result.termination['request_field'], 'operator_cancel')
        # Completion is externally visible only after the process is reaped.
        self.assertTrue(self.result.process_reaped)
        self.assertEqual(self.journal.attempts()[0]['state'], 'CANCELLED')

    def test_revoke_after_terminal_state_is_rejected(self):
        result = self.runtime.run(self.plan(), self.approval, self.contract(), RUN_SOURCE)
        self.assertEqual(result.status, 'CANDIDATE')
        with self.assertRaises(WorkerContractError):
            self.journal.revoke(result.attempt_id)

    def test_lease_read_failure_without_other_owner_still_kills(self):
        # The store read is unavailable (not revoked) and no other authority is
        # terminating: the host must stop the worker with the DISTINCT
        # lease_unreadable reason, not a revocation reason.
        ticks = iter([100.0 + 0.5 * n for n in range(64)])
        with patch.object(self.runtime, '_clock', side_effect=lambda: next(ticks)), \
                patch.object(self.journal, 'lease_state', return_value=LeaseRead('unknown')):
            result = self.runtime.run(self.plan(), self.approval, self.contract(), RUN_SOURCE)
        self.assertEqual(result.status, 'VIOLATED')
        self.assertEqual(result.reason, 'lease_unreadable')
        self.assertEqual(result.termination['request_field'], 'lease_unreadable')
        self.assertEqual(result.termination['request_action'],
                         {'reason': 'fenced_before_io'})


class ProcessKillTests(unittest.TestCase):
    def test_kill_records_intent_before_signal_and_single_reap(self):
        process = subprocess.Popen(['sh', '-c', 'sleep 30'])
        control = ProcessControl(process, correlation_id='x')
        try:
            calls = iter((([], [], []), ([control.pidfd], [], [])))
            with patch('residual.factory.termination_provenance.select.select',
                       side_effect=lambda *a, **k: next(calls)):
                control.kill(('resource', 'wall_clock_budget_s', {}), requester='watchdog')
            self.assertEqual(control.reason, ('resource', 'wall_clock_budget_s', {}))
            self.assertTrue(control.stopped.is_set())
            self.assertEqual(control.reap(), process.returncode)
        finally:
            process.kill()
            process.wait()


if __name__ == '__main__':
    unittest.main()
