"""Actual child ownership with explicitly injected constructor/cleanup failures."""
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts import qualification_disposable_process as adapter


@unittest.skipUnless(os.environ.get('RESIDUAL_RUN_DISPOSABLE_PROCESS_TESTS') == '1',
                     'NOT RUN: disposable process fixtures require explicit opt-in')
class ConstructorOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(os.environ['RESIDUAL_DISPOSABLE_WORKSPACE']).resolve()
        self.directory = Path(tempfile.mkdtemp(prefix='constructor-owned-',
                              dir=os.environ['RESIDUAL_DISPOSABLE_FIXTURES']))
        self.audits = []
        self.addCleanup(self.save_audit)

    def save_audit(self):
        path = self.directory/'constructor-ownership.json'
        path.write_text(json.dumps(self.audits,indent=2)+'\n',encoding='utf-8')
        print('constructor_audit='+str(path),flush=True)

    def construct(self):
        return adapter.OwnedPython(workspace=self.workspace,directory=self.directory,role='target',
                                   mode='healthy',lifetime=15.0,cleanup_timeout=2.0)

    def capture(self, failure, factory):
        try:
            self.construct()
        except BaseException as caught:
            self.assertIs(caught,failure)
            self.assertIsNotNone(caught.owned_process)
            audit = {'injected_failure':factory,'original_error':str(caught),
                     'owned_pid':caught.owned_process.pid,'command':caught.owned_process.args,
                     'constructor_cleanup':caught.owned_process_cleanup,
                     'observed_returncode':caught.owned_process.poll(),
                     'test_cleanup_needed':False}
            self.audits.append(audit)
            return caught,audit
        self.fail('injected constructor failure was not raised')

    def test_failures_after_spawn_reap_owned_child_and_join_only_started_reader(self):
        original_start = threading.Thread.start
        for stage in ('identity','before_thread_start','after_thread_start'):
            with self.subTest(stage=stage):
                failure = RuntimeError('injected initialization failure: '+stage)
                def start_then_fail(thread):
                    original_start(thread)
                    raise failure
                if stage == 'identity':
                    fault = patch.object(adapter.sup,'ProcessIdentity',side_effect=failure)
                else:
                    fault = patch.object(threading.Thread,'start',
                        side_effect=failure) if stage == 'before_thread_start' else patch.object(threading.Thread,'start',start_then_fail)
                with fault:
                    caught,audit = self.capture(failure,stage)
                receipt = caught.owned_process_cleanup
                self.assertTrue(receipt['reaped'])
                self.assertFalse(receipt['errors'])
                self.assertIsNotNone(caught.owned_process.returncode)
                self.assertEqual(receipt['reader_started'],stage == 'after_thread_start')
                self.assertEqual(receipt['reader_joined'],stage == 'after_thread_start')
                self.assertTrue(caught.owned_process.stdout.closed)
                self.assertTrue(caught.owned_stderr.closed)
                self.assertFalse(caught.owned_reader and caught.owned_reader.is_alive())

    def test_injected_termination_failure_preserves_original_and_owned_handle(self):
        failure = RuntimeError('original constructor failure')
        # This is an injected RuntimeError, not an actual execution/access denial.
        with patch.object(threading.Thread,'start',side_effect=failure), \
             patch.object(adapter.subprocess.Popen,'terminate',side_effect=RuntimeError('injected cleanup failure')):
            caught,audit = self.capture(failure,'constructor plus injected terminate failure')
        try:
            receipt = caught.owned_process_cleanup
            self.assertFalse(receipt['reaped'])
            self.assertEqual(receipt['errors'],[{'stage':'terminate','type':'RuntimeError'}])
            self.assertIsNone(caught.owned_process.poll())
            self.assertFalse(receipt['reader_started'])
            self.assertIn('cleanup incomplete',caught.__notes__[0])
        finally:
            # Explicit test-owner cleanup after removing the injected fault only.
            # Same captured Popen; no new PID lookup or alternative termination route.
            audit['test_cleanup_needed'] = True
            caught.owned_process.terminate()
            caught.owned_process.wait(timeout=2.0)
            audit['test_cleanup_returncode'] = caught.owned_process.returncode
            audit['test_cleanup_reaped'] = caught.owned_process.poll() is not None
        self.assertTrue(audit['test_cleanup_reaped'])

    def test_cleanup_internal_error_cannot_replace_initial_exception(self):
        failure = RuntimeError('original initialization failure')
        # Exercise the last-resort preservation guard, retaining ownership for caller cleanup.
        with patch.object(threading.Thread,'start',side_effect=failure), \
             patch.object(adapter.OwnedPython,'_abort_initialization',side_effect=RuntimeError('injected cleanup internal error')):
            caught,audit = self.capture(failure,'constructor plus injected cleanup internal failure')
        try:
            self.assertEqual(caught.owned_process_cleanup['errors'],
                             [{'stage':'cleanup_internal','type':'RuntimeError'}])
        finally:
            audit['test_cleanup_needed'] = True
            caught.owned_process.terminate(); caught.owned_process.wait(timeout=2.0)
            caught.owned_process.stdout.close(); caught.owned_stderr.close()
            audit['test_cleanup_returncode'] = caught.owned_process.returncode
            audit['test_cleanup_reaped'] = caught.owned_process.poll() is not None
        self.assertTrue(audit['test_cleanup_reaped'])


if __name__ == '__main__': unittest.main(failfast=True)
