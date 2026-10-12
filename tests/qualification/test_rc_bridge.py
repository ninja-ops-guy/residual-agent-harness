"""Wired offline admission + supervision + bridge; immutable in-memory journal."""
import copy
from dataclasses import asdict, replace
import json
from pathlib import Path
import tempfile
import sys
from types import ModuleType
import unittest
from unittest.mock import patch
import zipfile

from scripts import qualification_rc_bridge as bridge
from scripts import qualification_rc_soak as soak
from scripts import qualification_rc_supervision as sup
if __package__:
    from .test_rc_soak import write_selected_fixture, policy
    from .test_rc_supervision import Clock, Process, Driver, PAYLOAD, DIGEST
else:
    from test_rc_soak import write_selected_fixture, policy
    from test_rc_supervision import Clock, Process, Driver, PAYLOAD, DIGEST


class FixtureJournal:
    def __init__(self):
        self.rows = []
        self.failure = None
        self.effect = None
        self.fail_effect = None

    def append(self, raw):
        assert type(raw) is bytes
        if self.effect: return self.effect(raw)
        self.rows.append(raw)

    def fail(self, raw):
        assert type(raw) is bytes
        if self.fail_effect: return self.fail_effect(raw)
        if self.failure is None: self.failure = raw


class BridgeTests(unittest.TestCase):
    def setUp(self):
        # Model a fresh admission namespace; restore the outer test process on cleanup.
        # The production candidate_already_loaded guard remains exercised below.
        modules = patch.dict(sys.modules)
        modules.start()
        self.addCleanup(modules.stop)
        for name in list(sys.modules):
            if name.split('.')[0] in soak.Binding.PREFIXES:
                del sys.modules[name]
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.installed = self.root/'installed'
        (self.installed/'residual').mkdir(parents=True)
        wheel = self.root/'candidate.whl'
        with zipfile.ZipFile(wheel, 'w') as archive:
            for name, raw in {'residual/__init__.py': b'',
                              'residual/adapter.py': b'raise AssertionError("must not execute")\n'}.items():
                archive.writestr(name, raw)
                (self.installed/name).write_bytes(raw)
        config = self.root/'configuration.json'; config.write_bytes(b'{}')
        manifest, digest = write_selected_fixture(self.root, wheel, config,
                                                  profile_policy=policy(duration=86400))
        self.selected = soak.SelectedManifest.load(manifest, self.root, digest)
        self.clock = Clock()
        ids = [sup.ProcessIdentity('fixture', i+1, 'birth-'+str(i), str(i+1)*64) for i in range(3)]
        self.tasks = tuple(sup.Task('task-'+str(i), 'attempt-1', 'nonce-'+str(i), i, 3+i*3, DIGEST) for i in range(2))
        self.requirements = sup.Requirements('run-1', *ids, 0, 1, 2, .25, self.tasks)
        self.observer, self.target, self.driver = Process(ids[0]), Process(ids[1]), Driver(ids[2])
        self.journal = FixtureJournal()
        self.epoch = 'epoch-1'
        self.expected = soak.digest(sup.canonical(bridge.selection_identity(self.selected, self.requirements, self.epoch)))
        self.controller = self.make()

    def make(self, **changes):
        args = dict(selected=self.selected, installed_root=self.installed, requirements=self.requirements,
                    epoch=self.epoch, expected_sha256=self.expected, clock=self.clock,
                    observer=self.observer, target=self.target, driver=self.driver, journal=self.journal)
        args.update(changes)
        return bridge.Bridge(**args)

    def outcome(self, index=0, **changes):
        task = self.tasks[index]
        value = {k: getattr(task,k) for k in ('task_id','attempt_id','nonce','sequence')}
        value.update(result_id='result-'+str(index), status='succeeded', payload=copy.deepcopy(PAYLOAD),
                     target=asdict(self.requirements.target), driver=asdict(self.requirements.driver))
        value.update(changes)
        self.driver.observation['outcome'] = value
        return value

    def replay(self, rows=None, **changes):
        args = dict(selected=self.selected, requirements=self.requirements, epoch=self.epoch,
                    expected_sha256=self.expected, failure=self.journal.failure)
        args.update(changes)
        return bridge.replay(self.journal.rows if rows is None else rows, **args)

    def complete(self):
        self.outcome(); self.controller.tick()
        self.clock.value = 1; self.outcome(1)
        return self.controller.tick()

    def assert_failed(self, report, reason, count=0):
        self.assertEqual(report['state'], 'failed')
        self.assertEqual(report['first_failure']['reason'], reason)
        self.assertEqual(report['accepted_result_count'], count)
        self.assertFalse(report['rc_qualified'])
        self.assertFalse(report['elapsed_soak_satisfied'])

    def test_wired_plan_completion_is_not_24h_soak_or_qualification(self):
        report = self.complete()
        self.assertEqual(report['state'], 'plan_observed_complete')
        self.assertEqual(report['accepted_result_count'], 2)
        self.assertEqual(self.selected.verify_inputs()['duration'], 86400)
        self.assertFalse(report['elapsed_soak_satisfied']); self.assertFalse(report['rc_qualified'])
        self.assertEqual(report['missing_capabilities'], list(bridge.MISSING))
        self.assertEqual(self.replay(require_complete=True)['accepted'], report['accepted'])
        self.assertEqual(self.controller.finish(), report)
        self.assertNotIn('residual.adapter', __import__('sys').modules)

    def test_external_selection_binds_manifest_profile_run_requirements_and_epoch(self):
        for changes in ({'epoch':'other'}, {'requirements':replace(self.requirements, run_id='other')},
                        {'requirements':replace(self.requirements, maximum_gap=3)}, {'expected_sha256':'0'*64}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError,'selection_mismatch'):
                self.make(**changes)
        facts = self.selected.facts
        facts['profile']['sha256'] = '0'*64
        alternative = soak.SelectedManifest(self.selected.path, self.root,
                        soak.digest(soak.canonical(facts)), soak.canonical(facts))
        with self.assertRaisesRegex(ValueError, 'selection_mismatch'): self.make(selected=alternative)
        self.assertEqual(len(self.journal.rows), 1)

    def test_admission_drift_prevents_any_poll_or_progress(self):
        (self.installed/'residual/adapter.py').write_bytes(b'changed')
        report = self.controller.tick()
        self.assert_failed(report, 'invalid_admission_or_observation')
        self.assertEqual(self.observer.calls+self.target.calls+self.driver.calls, 0)
        self.assertEqual(self.replay()['first_failure'], report['first_failure'])

    def test_loaded_candidate_still_rejected_by_real_admission_guard(self):
        sys.modules['residual'] = ModuleType('residual')
        with self.assertRaisesRegex(ValueError, 'candidate_already_loaded'):
            self.make()
        self.assertEqual(len(self.journal.rows), 1)

    def test_wrong_task_attempt_nonce_generation_and_cumulative_claim_rejected(self):
        bad_target = asdict(self.requirements.target); bad_target['birth_token'] = 'replaced'
        for changes in ({'task_id':'wrong'}, {'attempt_id':'wrong'}, {'nonce':'wrong'},
                        {'target':bad_target}, {'completed_count':9000}):
            with self.subTest(changes=changes):
                self.setUp(); self.outcome(**changes)
                report = self.controller.tick()
                self.assertEqual(report['state'], 'failed')
                self.assertEqual(report['accepted_result_count'], 0)
                self.assertEqual(self.replay()['first_failure'], report['first_failure'])

    def test_duplicate_receipt_cannot_advance_existing_progress(self):
        self.outcome(); self.controller.tick(); self.clock.value = 1
        self.outcome(1, result_id='result-0')
        report = self.controller.tick()
        self.assert_failed(report, 'duplicate_result', 1)
        self.assertEqual(self.replay()['accepted_result_count'], 1)

    def test_missing_outcomes_fail_explicit_finish_and_deadline(self):
        self.controller.tick()
        with self.assertRaisesRegex(ValueError,'missing_outcomes'): self.replay(require_complete=True)
        report = self.controller.finish()
        self.assert_failed(report, 'missing_outcomes')
        self.assertEqual(self.replay()['first_failure'], report['first_failure'])
        self.setUp()
        for t in range(4):
            self.clock.value = t; report = self.controller.tick()
        self.assert_failed(report, 'task_deadline_missed')

    def test_copied_receipts_and_reports_do_not_alias_adapter_or_journal(self):
        shared = self.outcome(); report = self.controller.tick()
        original = tuple(self.journal.rows)
        shared['payload']['fixture_operation'] = 'mutated'
        shared['result_id'] = 'mutated'; report['accepted'].clear()
        self.assertEqual(self.controller.report()['accepted'][0]['result_id'], 'result-0')
        self.assertEqual(self.replay()['accepted'][0]['payload_sha256'], DIGEST)
        self.assertEqual(tuple(self.journal.rows), original)

    def test_replay_rejects_wrong_binding_generation_receipt_and_malformed_records(self):
        self.complete()
        mutations = [lambda r: r['selection'].update(run_id='wrong'),
                     lambda r: r['selection'].update(epoch='wrong'),
                     lambda r: r.update(sequence=True),
                     lambda r: r.update(extra='unknown'),
                     lambda r: r['value']['target'].update(birth_token='wrong'),
                     lambda r: r['value']['driver'].update(pid=True),
                     lambda r: r['value']['report'].update(run_id='wrong'),
                     lambda r: r['value']['report'].update(accepted_result_count=100),
                     lambda r: r['value']['report'].update(rc_qualified=True),
                     lambda r: r['value']['report'].update(missing_capabilities=[]),
                     lambda r: r['value']['report']['accepted'][0].update(attempt_id='wrong'),
                     lambda r: r['value']['report']['accepted'][0].update(payload_sha256='0'*64),
                     lambda r: r['value']['report']['accepted'].clear()]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                rows = list(self.journal.rows); row = json.loads(rows[1]); mutate(row)
                rows[1] = sup.canonical(row)
                with self.assertRaises(ValueError): self.replay(rows)
        for rows in ([], [b'{bad'], [b'{"x":1,"x":2}'], self.journal.rows[1:],
                     self.journal.rows+[self.journal.rows[-1]],
                     [self.journal.rows[0], self.journal.rows[-1]]):
            with self.subTest(rows=rows), self.assertRaises(ValueError): self.replay(rows)

    def test_replay_rejects_duplicate_ids_and_changed_prior_receipts(self):
        self.complete()
        for mutate in (lambda r: r['value']['report']['accepted'][1].update(result_id='result-0'),
                       lambda r: r['value']['report']['accepted'][0].update(result_id='new')):
            rows = list(self.journal.rows); last = json.loads(rows[-1]); mutate(last)
            rows[-1] = sup.canonical(last)
            with self.assertRaises(ValueError): self.replay(rows)

    def test_write_failure_before_and_after_append_never_commits_progress(self):
        for after in (False, True):
            with self.subTest(after=after):
                self.setUp(); self.outcome()
                def fail(raw):
                    if after: self.journal.rows.append(raw)
                    raise OSError('fixture failure')
                self.journal.effect = fail
                report = self.controller.tick()
                self.assert_failed(report, 'journal_write_failed')
                replayed = self.replay()
                self.assertEqual(replayed['accepted_result_count'], 0)
                self.assertEqual(replayed['first_failure'], report['first_failure'])
                self.assertEqual(self.controller.tick(), report)

    def test_failure_sidecar_write_failure_still_invalidates_live_run(self):
        self.journal.effect = lambda _: (_ for _ in ()).throw(OSError())
        self.journal.fail_effect = lambda _: (_ for _ in ()).throw(OSError())
        self.outcome(); report = self.controller.tick()
        self.assert_failed(report, 'journal_write_failed')
        self.assertFalse(report['failure_recorded'])
        self.assertEqual(self.controller.finish(), report)

    def test_failed_write_preserves_previously_committed_receipt(self):
        self.outcome(); self.controller.tick(); self.clock.value = 1; self.outcome(1)
        def append_without_ack(raw):
            self.journal.rows.append(raw)
            return False
        self.journal.effect = append_without_ack
        report = self.controller.tick()
        self.assert_failed(report, 'journal_write_failed', 1)
        replayed = self.replay()
        self.assertEqual(replayed['accepted_result_count'], 1)
        self.assertEqual(replayed['first_failure'], report['first_failure'])
        self.assertEqual(report['accepted'], replayed['accepted'])

    def test_failure_record_malformed_selection_and_commit_boundary_rejected(self):
        self.controller.cancel()
        for mutate in (lambda r: r['selection'].update(epoch='wrong'),
                       lambda r: r.update(committed_records=True),
                       lambda r: r.update(committed_records=1000),
                       lambda r: r.update(extra='unknown'),
                       lambda r: r['first_failure'].update(reason='unbounded secret text'),
                       lambda r: r['first_failure'].update(supervision={'reason':'different'})):
            with self.subTest(mutation=mutate):
                record = json.loads(self.journal.failure); mutate(record)
                with self.assertRaises(ValueError): self.replay(failure=sup.canonical(record))

    def test_initial_journal_write_failure_prevents_supervision(self):
        journal = FixtureJournal()
        journal.effect = lambda _: (_ for _ in ()).throw(OSError())
        controller = self.make(journal=journal)
        self.assert_failed(controller.tick(), 'journal_write_failed')
        self.assertEqual(self.observer.calls, 0)

    def test_cancel_interrupt_callbacks_preserve_first_failure_no_append(self):
        for action in ('cancel','interrupt'):
            with self.subTest(action=action):
                self.setUp(); self.outcome()
                self.driver.effect = lambda _: getattr(self.controller, action)()
                report = self.controller.tick()
                self.assertEqual(report['state'], 'failed')
                self.assertEqual(report['accepted_result_count'], 0)
                self.assertEqual(len(self.journal.rows), 1)
                self.controller.interrupt(); self.controller.cancel()
                self.assertEqual(self.controller.report(), report)
                self.assertEqual(self.replay()['first_failure'], report['first_failure'])

    def test_cancellation_inside_journal_append_discards_uncommitted_receipt(self):
        self.outcome()
        def cancel(raw):
            self.journal.rows.append(raw)
            self.controller.cancel()
        self.journal.effect = cancel
        report = self.controller.tick()
        self.assert_failed(report, 'cancelled_by_caller')
        self.assertEqual(self.replay()['accepted_result_count'], 0)

    def test_reentrant_tick_latches_failure(self):
        self.observer.effect = lambda _: self.controller.tick()
        self.assert_failed(self.controller.tick(), 'reentrant_tick')

    def test_installed_mutation_inside_final_task_polls_never_commits_receipt(self):
        for role in ('observer', 'target', 'driver'):
            for boundary in (1, 2):
                with self.subTest(role=role, boundary=boundary):
                    self.setUp(); self.outcome()
                    first = self.controller.tick()
                    self.assertEqual(first['accepted_result_count'], 1)
                    committed = tuple(self.journal.rows)
                    self.clock.value = 1; self.outcome(1)
                    installed = self.installed/'residual/adapter.py'
                    original = installed.read_bytes()
                    handle = getattr(self, role)
                    trigger = handle.calls+boundary
                    def mutate_inside_poll(h):
                        if h.calls == trigger: installed.write_bytes(b'changed during final task poll\n')
                    handle.effect = mutate_inside_poll
                    report = self.controller.tick()
                    # Actual validator, wheel/configuration unchanged; no mock bypass.
                    with self.assertRaisesRegex(ValueError, 'installed_bytes_drift'):
                        self.controller._binding.validate_installation()
                    self.assert_failed(report, 'invalid_admission_or_observation', 1)
                    self.assertEqual(tuple(self.journal.rows), committed)
                    self.assertEqual(report['accepted'], first['accepted'])
                    replayed = self.replay()
                    self.assert_failed(replayed, 'invalid_admission_or_observation', 1)
                    self.assertEqual(replayed['first_failure'], report['first_failure'])
                    calls = (self.observer.calls, self.target.calls, self.driver.calls)
                    installed.write_bytes(original)
                    self.controller.interrupt(); self.controller.cancel()
                    self.assertEqual(self.controller.tick(), report)
                    self.assertEqual(self.controller.finish(), report)
                    self.assertEqual((self.observer.calls, self.target.calls, self.driver.calls), calls)

    def test_completed_finish_and_tick_revalidate_installation_without_polling(self):
        for method in ('finish', 'tick'):
            with self.subTest(method=method):
                self.setUp(); complete = self.complete()
                committed = tuple(self.journal.rows)
                calls = (self.observer.calls, self.target.calls, self.driver.calls)
                (self.installed/'residual/adapter.py').write_bytes(b'changed after plan completion\n')
                report = getattr(self.controller, method)()
                self.assert_failed(report, 'invalid_admission_or_observation', 2)
                self.assertEqual(report['accepted'], complete['accepted'])
                self.assertEqual(tuple(self.journal.rows), committed)
                self.assertEqual(self.replay()['first_failure'], report['first_failure'])
                self.assertEqual(self.controller.finish(), report)
                self.assertEqual((self.observer.calls, self.target.calls, self.driver.calls), calls)


if __name__ == '__main__': unittest.main()
