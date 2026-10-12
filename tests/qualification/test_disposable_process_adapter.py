"""Opt-in REAL disposable child tests, separate from injected supervision evidence."""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest

from scripts import qualification_disposable_process as adapter
from scripts import qualification_rc_supervision as sup


@unittest.skipUnless(os.environ.get('RESIDUAL_RUN_DISPOSABLE_PROCESS_TESTS') == '1',
                     'NOT RUN: disposable process fixtures require explicit opt-in')
class DisposableProcessTests(unittest.TestCase):
    # Externally selected TEST timings only; no production defaults or RC thresholds.
    STARTUP = 5.0
    LIFETIME = 15.0
    CLEANUP = 2.0
    CADENCE = 0.15
    GAP = 2.0
    POLL_BUDGET = 0.1
    TASK_DEADLINES = (2.0,4.0)

    def setUp(self):
        self.workspace = Path(os.environ['RESIDUAL_DISPOSABLE_WORKSPACE']).resolve()
        fixture = Path(os.environ['RESIDUAL_DISPOSABLE_FIXTURES']).resolve()
        fixture.relative_to(self.workspace)
        self.directory = Path(tempfile.mkdtemp(prefix='owned-python-',dir=fixture))
        self.children = []
        self.last_report = None
        self.addCleanup(self.cleanup_owned)

    def cleanup_owned(self):
        receipts, errors = [], []
        for child in reversed(self.children):
            try: receipts.append(child.close())
            except BaseException as exc: errors.append({'pid':child.identity.pid,'error':str(exc),'type':type(exc).__name__})
        audit = {'test':self.id(),'children':receipts,'cleanup_errors':errors,'last_report':self.last_report,
                 'test_timeouts':{'startup':self.STARTUP,'lifetime':self.LIFETIME,'cleanup':self.CLEANUP,
                                  'cadence':self.CADENCE,'maximum_gap':self.GAP,'poll_budget':self.POLL_BUDGET,
                                  'task_deadline_offsets':self.TASK_DEADLINES},
                 'rc_qualified':False}
        (self.directory/'ownership-cleanup.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
        print('process_audit='+str(self.directory/'ownership-cleanup.json'),flush=True)
        self.assertFalse(errors, errors)

    def prepare(self, *, target_mode='healthy', driver_mode='healthy'):
        for role,mode in (('observer','healthy'),('target',target_mode),('driver',driver_mode)):
            # A denial is not converted to a fixture outcome or retried.
            child = adapter.OwnedPython(workspace=self.workspace,directory=self.directory,role=role,mode=mode,
                                        lifetime=self.LIFETIME,cleanup_timeout=self.CLEANUP)
            self.children.append(child)
        self.observer,self.target,self.driver = self.children
        adapter.wait_ready(self.children,timeout=self.STARTUP,interval=.02)
        self.assertEqual(len({p.identity.pid for p in self.children}),3)
        self.assertEqual(len({p.identity.birth_token for p in self.children}),3)
        start = time.monotonic()
        digest = hashlib.sha256(sup.canonical({'fixture_operation':'completed'})).hexdigest()
        self.tasks = tuple(sup.Task('task-'+str(i),'attempt-1','nonce-'+str(i),i,start+offset,digest)
                           for i,offset in enumerate(self.TASK_DEADLINES))
        self.requirements = sup.Requirements('disposable-'+self.driver.token,*[p.identity for p in self.children],
                                             start,self.CADENCE,self.GAP,self.POLL_BUDGET,self.tasks)
        self.driver.configure(self.tasks,self.target.identity,self.driver.identity)
        self.controller = sup.Supervisor(self.requirements,clock=time.monotonic,observer=self.observer,
                                         target=self.target,driver=self.driver)

    def drive(self, *, accepted=None):
        stop = self.tasks[-1].deadline+1
        while time.monotonic() < stop:
            self.last_report = self.controller.tick()
            if self.last_report['state'] != 'pending': return self.last_report
            if accepted is not None and self.last_report['accepted_result_count'] >= accepted: return self.last_report
            time.sleep(self.CADENCE)
        self.fail('parent fixture deadline exceeded')

    def assert_unqualified(self, report):
        self.assertFalse(report['rc_qualified'])
        self.assertIn('external_watchdog_unverified',report['missing_capabilities'])
        self.assertIn('adapter_poll_preemption_unverified',report['missing_capabilities'])

    def test_healthy_correlated_child_responses(self):
        self.prepare()
        report = self.drive()
        self.assertEqual(report['state'],'observed_complete')
        self.assertEqual(report['accepted_result_count'],2)
        self.assertEqual([r['result_id'] for r in report['accepted']],['child-result-0','child-result-1'])
        self.assertTrue(all(p._proc.poll() is None for p in self.children))
        self.assert_unqualified(report)

    def test_neverresponding_second_task_times_out_with_partial_progress(self):
        self.prepare(driver_mode='never_second')
        report = self.drive()
        self.assertEqual(report['state'],'failed')
        self.assertEqual(report['first_failure']['reason'],'task_deadline_missed')
        self.assertEqual(report['accepted_result_count'],1)
        self.assertIsNone(self.driver._proc.poll())
        self.controller.cancel(); self.controller.interrupt()
        self.assertEqual(self.controller.tick(),report)
        self.assert_unqualified(report)

    def test_early_exit_of_owned_target_is_observed(self):
        self.prepare(target_mode='exit',driver_mode='never')
        report = self.drive()
        self.assertEqual(report['first_failure']['reason'],'target_exited')
        self.assertEqual(report['accepted_result_count'],0)
        self.assertIsNotNone(self.target._proc.poll())
        self.assert_unqualified(report)

    def test_wrong_child_generation_identity_is_rejected(self):
        self.prepare(target_mode='wrong_identity')
        report = self.drive()
        self.assertEqual(report['first_failure']['reason'],'target_replaced')
        self.assertEqual(report['accepted_result_count'],0)
        self.assert_unqualified(report)

    def test_stale_child_result_is_rejected(self):
        self.prepare(driver_mode='stale')
        report = self.drive()
        self.assertEqual(report['first_failure']['reason'],'stale_or_wrong_attempt_result')
        self.assertEqual(report['accepted_result_count'],0)
        self.assert_unqualified(report)

    def test_cancellation_preserves_progress_cleanup_owns_termination(self):
        self.prepare(driver_mode='never_second')
        report = self.drive(accepted=1)
        self.assertEqual(report['accepted_result_count'],1)
        calls = [p.poll_calls for p in self.children]
        self.last_report = self.controller.cancel()
        self.assertEqual(self.last_report['first_failure']['reason'],'cancelled_by_caller')
        self.assertEqual(self.last_report['accepted'],report['accepted'])
        self.assertEqual(self.controller.tick(),self.last_report)
        self.assertEqual([p.poll_calls for p in self.children],calls)
        self.assertTrue(all(p._proc.poll() is None for p in self.children))
        self.assert_unqualified(self.last_report)


if __name__ == '__main__': unittest.main(failfast=True)
