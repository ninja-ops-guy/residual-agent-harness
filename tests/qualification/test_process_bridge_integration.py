"""Opt-in actual children -> Supervisor -> Bridge -> existing fixture journal.

The admitted wheel is synthetic and not the launched child image. These tests
prove interface correlation/retention, not production artifact execution or soak.
"""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

from scripts import qualification_disposable_process as adapter
from scripts import qualification_rc_bridge as bridge
from scripts import qualification_rc_soak as soak
from scripts import qualification_rc_supervision as sup
if __package__:
    from .test_rc_bridge import FixtureJournal
    from .test_rc_soak import write_selected_fixture, policy
else:
    from test_rc_bridge import FixtureJournal
    from test_rc_soak import write_selected_fixture, policy


@unittest.skipUnless(os.environ.get('RESIDUAL_RUN_DISPOSABLE_PROCESS_TESTS') == '1',
                     'NOT RUN: owned process bridge integration requires explicit opt-in')
class ProcessBridgeIntegrationTests(unittest.TestCase):
    STARTUP, LIFETIME, CLEANUP = 5.0, 20.0, 2.0
    CADENCE, GAP, POLL_BUDGET = 0.2, 2.0, 0.1
    DEADLINE_OFFSETS = (3.0,6.0)

    def setUp(self):
        self.workspace = Path(os.environ['RESIDUAL_DISPOSABLE_WORKSPACE']).resolve()
        fixture = Path(os.environ['RESIDUAL_DISPOSABLE_FIXTURES']).resolve()
        fixture.relative_to(self.workspace)
        self.root = Path(tempfile.mkdtemp(prefix='process-bridge-',dir=fixture))
        self.children = []
        self.last_report = self.replayed = None
        self.journal = FixtureJournal()
        self.journal.append = unittest.mock.Mock(wraps=self.journal.append)
        self.journal.fail = unittest.mock.Mock(wraps=self.journal.fail)
        # Restore outer discovery imports; never disable production admission checks.
        modules = patch.dict(sys.modules)
        modules.start(); self.addCleanup(modules.stop)
        for name in list(sys.modules):
            if name.split('.')[0] in soak.Binding.PREFIXES: del sys.modules[name]
        self.addCleanup(self.cleanup_owned_and_save)
        self.installed = self.root/'installed'
        (self.installed/'residual').mkdir(parents=True)
        wheel = self.root/'fixture.whl'
        with zipfile.ZipFile(wheel,'w') as archive:
            for name,raw in {'residual/__init__.py':b'',
                             'residual/adapter.py':b'raise AssertionError("admission must not execute")\n'}.items():
                archive.writestr(name,raw); (self.installed/name).write_bytes(raw)
        configuration = self.root/'configuration.json'; configuration.write_bytes(b'{}')
        manifest,expected = write_selected_fixture(self.root,wheel,configuration,
                                                   profile_policy=policy(duration=86400))
        self.selected = soak.SelectedManifest.load(manifest,self.root,expected)

    def cleanup_owned_and_save(self):
        receipts, errors = [], []
        for child in reversed(self.children):
            try: receipts.append(child.close())
            except BaseException as exc:
                errors.append({'pid':child.identity.pid,'type':type(exc).__name__,'error':str(exc)})
        (self.root/'journal.jsonl').write_bytes(b'\n'.join(self.journal.rows)+b'\n')
        if self.journal.failure is not None: (self.root/'first-failure.json').write_bytes(self.journal.failure)
        evidence = {'test':self.id(),'children':receipts,'cleanup_errors':errors,
                    'live_report':self.last_report,'replay_report':self.replayed,
                    'append_calls':self.journal.append.call_count,'failure_write_calls':self.journal.fail.call_count,
                    'requirements':asdict(self.requirements) if hasattr(self,'requirements') else None,
                    'selected_manifest_sha256':self.selected.sha256 if hasattr(self,'selected') else None,
                    'test_timeouts':{'startup':self.STARTUP,'lifetime':self.LIFETIME,'cleanup':self.CLEANUP,
                                     'cadence':self.CADENCE,'maximum_gap':self.GAP,'poll_budget':self.POLL_BUDGET,
                                     'task_deadline_offsets':self.DEADLINE_OFFSETS},
                    'limits':['synthetic admitted wheel is not launched child image',
                              'fixture journal is not durable storage','no independent coordinator watchdog'],
                    'rc_qualified':False}
        (self.root/'integration-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
        print('integration_evidence='+str(self.root/'integration-evidence.json'),flush=True)
        self.assertFalse(errors,errors)

    def prepare(self, mode):
        for role in ('observer','target','driver'):
            child = adapter.OwnedPython(workspace=self.workspace,directory=self.root,role=role,
                mode=mode if role=='driver' else 'healthy',lifetime=self.LIFETIME,cleanup_timeout=self.CLEANUP)
            self.children.append(child)
        self.observer,self.target,self.driver = self.children
        adapter.wait_ready(self.children,timeout=self.STARTUP,interval=.02)
        self.assertEqual(len({c.identity.pid for c in self.children}),3)
        self.assertEqual(len({c.identity.birth_token for c in self.children}),3)
        start = time.monotonic()
        digest = hashlib.sha256(sup.canonical({'fixture_operation':'completed'})).hexdigest()
        self.tasks = tuple(sup.Task('task-'+str(i),'attempt-1','nonce-'+str(i),i,start+offset,digest)
                           for i,offset in enumerate(self.DEADLINE_OFFSETS))
        self.requirements = sup.Requirements('e2e-'+self.driver.token,*[c.identity for c in self.children],
                                             start,self.CADENCE,self.GAP,self.POLL_BUDGET,self.tasks)
        self.epoch = 'epoch-'+self.observer.token
        self.expected = soak.digest(sup.canonical(bridge.selection_identity(self.selected,self.requirements,self.epoch)))
        self.controller = bridge.Bridge(selected=self.selected,installed_root=self.installed,
            requirements=self.requirements,epoch=self.epoch,expected_sha256=self.expected,clock=time.monotonic,
            observer=self.observer,target=self.target,driver=self.driver,journal=self.journal)
        self.assertIs(type(self.controller._supervisor),sup.Supervisor)
        self.driver.configure(self.tasks,self.target.identity,self.driver.identity)

    def drive(self, accepted=None):
        while time.monotonic() < self.tasks[-1].deadline+1:
            self.last_report = self.controller.tick()
            if self.last_report['state'] != 'pending': return self.last_report
            if accepted is not None and self.last_report['accepted_result_count'] >= accepted: return self.last_report
            time.sleep(self.CADENCE)
        self.fail('external fixture deadline exceeded')

    def check_replay(self, complete=False):
        self.replayed = bridge.replay(self.journal.rows,selected=self.selected,requirements=self.requirements,
            epoch=self.epoch,expected_sha256=self.expected,failure=self.journal.failure,require_complete=complete)
        for key in ('state','selection','accepted','accepted_result_count','first_failure','missing_capabilities'):
            self.assertEqual(self.replayed[key],self.last_report[key])
        for value in (self.last_report,self.replayed):
            self.assertFalse(value['rc_qualified']); self.assertFalse(value['elapsed_soak_satisfied'])
            self.assertEqual(value['missing_capabilities'],list(bridge.MISSING))
            self.assertEqual(value['selection'],bridge.selection_identity(self.selected,self.requirements,self.epoch))
        self.assertEqual(self.selected.verify_inputs()['duration'],86400)

    def check_sticky_failure(self, reason):
        self.assertEqual(self.last_report['state'],'failed')
        self.assertEqual(self.last_report['first_failure']['reason'],reason)
        self.assertEqual(self.last_report['accepted_result_count'],1)
        self.assertTrue(self.last_report['failure_recorded'])
        self.assertEqual(self.last_report['accepted'][0]['result_id'],'child-result-0')
        self.check_replay()
        rows,failure = tuple(self.journal.rows),self.journal.failure
        calls = self.journal.append.call_count,self.journal.fail.call_count
        polls = [c.poll_calls for c in self.children]
        self.assertEqual(calls[1],1)
        for operation in (self.controller.tick,self.controller.finish,self.controller.cancel,self.controller.interrupt):
            self.assertEqual(operation(),self.last_report)
        self.assertEqual([c.poll_calls for c in self.children],polls)
        self.assertEqual((self.journal.append.call_count,self.journal.fail.call_count),calls)
        self.assertEqual(tuple(self.journal.rows),rows); self.assertEqual(self.journal.failure,failure)
        self.assertTrue(all(c._proc.poll() is None for c in self.children))

    def test_healthy_two_receipts_through_actual_bridge(self):
        self.prepare('healthy'); self.drive()
        self.assertEqual(self.last_report['state'],'plan_observed_complete')
        self.assertEqual(self.last_report['accepted_result_count'],2)
        self.assertEqual([r['result_id'] for r in self.last_report['accepted']],['child-result-0','child-result-1'])
        self.assertIsNone(self.journal.failure); self.assertEqual(self.journal.fail.call_count,0)
        self.check_replay(complete=True)
        self.assertEqual(self.controller.finish(),self.last_report)

    def test_real_pending_child_deadline_retains_first_committed_receipt(self):
        self.prepare('never_second'); self.drive(accepted=1)
        committed = self.last_report['accepted']
        time.sleep(self.CADENCE)
        self.drive()
        self.check_sticky_failure('task_deadline_missed')
        detail = self.last_report['first_failure']['supervision']
        self.assertEqual(detail['task_index'],1)
        self.assertGreaterEqual(detail['last_monotonic'],self.tasks[1].deadline)
        self.assertEqual(self.last_report['accepted'],committed)

    def test_cancellation_after_receipt_retains_journal_first_failure(self):
        self.prepare('never_second'); self.drive(accepted=1)
        self.assertEqual(self.last_report['state'],'pending')
        committed = self.last_report['accepted']
        self.last_report = self.controller.cancel()
        self.check_sticky_failure('cancelled_by_caller')
        self.assertEqual(self.last_report['accepted'],committed)


if __name__ == '__main__': unittest.main(failfast=True)
