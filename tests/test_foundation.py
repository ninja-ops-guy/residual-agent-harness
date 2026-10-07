"""Contract, integrity, and real station integration regressions for Track 1."""
import dataclasses
import json
import tempfile
import threading
import unittest
from pathlib import Path

from residual import (AmendmentRule, BrakeAction, BrakeTrip, CheckResult, CheckType,
    GoalSpec, LoopController, ReceiptReference, RunOutcome, StationExtensionRegistry,
    StationReceipt, SuccessCriterion, Verifier, VerifierDescriptor, VerifierRevision,
    validate_receipt_graph, ProposedAction, QuarantineStore, PolicyDecision)
from residual.core import Artifact, ContractError, Obligation, Registry, Task, Verdict, digest, register_builtins
from residual.engine import Harness
from residual.storage import Cache
from residual.modules.adapters import LifecycleModule, HITLModule, MeshModule
from residual.receipts import cache_key


def spec(evaluator='sample:check', max_passes=2):
    return GoalSpec('goal', 'Test bounded execution',
        (SuccessCriterion('check', CheckType.MECHANICAL, 'Validate candidate', evaluator),),
        max_passes, 1000, 60, AmendmentRule(('operator',)))


def identity(tag='one'):
    return VerifierRevision(digest({'implementation': tag}), digest({}), digest({}))


class Pass:
    def __init__(self, candidate=True, observations=None):
        self.calls = 0
        self.candidate, self.observations = candidate, observations or []
    def run_pass(self, spec, number):
        self.calls += 1
        return {'candidate': self.candidate, 'tokens_used': 0, 'observations': self.observations}


class Sample(LifecycleModule):
    name = 'sample'
    def verifiers(self):
        return {'check': VerifierDescriptor(CheckType.MECHANICAL,
            lambda value, params: (CheckResult.PASS if value else CheckResult.FAIL, 'checked'), identity())}


class ReceiptTests(unittest.TestCase):
    def receipt(self, tid='child', parents=(), **kw):
        values = dict(task_id=tid, cache_key=digest('context'), value_hash=digest(True),
                      verifier_name='sample:check', verifier_revision=identity().effective_revision,
                      verdict=CheckResult.PASS, parent_receipts=parents)
        return StationReceipt(**{**values, **kw})

    def test_round_trip_all_nine_fields_and_domains(self):
        receipt = self.receipt(engine_name='langgraph', engine_version='0.3.1')
        self.assertEqual(len(receipt.payload()), 9)
        self.assertEqual(receipt.payload()['engine_name'], 'langgraph')
        self.assertEqual(receipt.payload()['engine_version'], '0.3.1')
        self.assertEqual(StationReceipt.from_json(json.dumps(receipt.to_dict())), receipt)
        self.assertNotEqual(receipt.receipt_hash, digest(receipt.payload()))
        self.assertNotEqual(receipt.receipt_hash, self.receipt(verdict=CheckResult.UNKNOWN,
            engine_name='langgraph', engine_version='0.3.1').receipt_hash)
        self.assertNotEqual(receipt.receipt_hash, self.receipt(engine_name='crewai', engine_version='0.3.1').receipt_hash)
        self.assertNotEqual(receipt.receipt_hash, self.receipt(engine_name='langgraph', engine_version='0.3.2').receipt_hash)

    def test_tampering_or_unknown_envelope_profile_rejected(self):
        for field, value in [('schema_version', 'future'), ('hash_algorithm', 'md5'), ('receipt_hash', '0'*64)]:
            envelope = self.receipt().to_dict(); envelope[field] = value
            with self.assertRaises(ContractError): StationReceipt.from_dict(envelope)
        envelope = self.receipt().to_dict(); envelope['payload']['value_hash'] = digest(False)
        with self.assertRaises(ContractError): StationReceipt.from_dict(envelope)
        envelope = self.receipt(engine_name='langgraph', engine_version='1').to_dict(); envelope['payload']['engine_name'] = 'crewai'
        with self.assertRaises(ContractError): StationReceipt.from_dict(envelope)
        with self.assertRaises(ContractError): StationReceipt.from_json('{"payload":{},"payload":{}}')

    def test_closed_verdicts_hashes_and_namespace(self):
        for key, value in [('value_hash', 'f'*63), ('cache_key', 'Z'*64), ('verdict', 'skipped'),
                           ('verdict', 'approved'), ('verifier_name', 'anonymous'), ('verifier_revision', 'v1'),
                           ('engine_name', ''), ('engine_version', '')]:
            with self.subTest(key=key):
                with self.assertRaises(ContractError): self.receipt(**{key:value})

    def test_prerequisite_order_and_graph(self):
        a, b = self.receipt('a'), self.receipt('b')
        refs = (ReceiptReference('b', b.receipt_hash), ReceiptReference('a', a.receipt_hash))
        child = self.receipt(parents=refs)
        self.assertEqual(child, self.receipt(parents=refs[::-1]))
        validate_receipt_graph({'a': a, 'b': b, 'child': child}, {'a': (), 'b': (), 'child': ('b', 'a')})
        with self.assertRaises(ContractError): self.receipt(parents=(refs[0], refs[0]))
        with self.assertRaises(ContractError): validate_receipt_graph({'a':a,'child':child}, {'a':(), 'child':('a',)})
        with self.assertRaises(ContractError): validate_receipt_graph({'a':a,'b':b}, {'a':('b',), 'b':('a',)})

    def test_unknown_cannot_match_acceptance(self):
        receipt = self.receipt(verdict=CheckResult.UNKNOWN)
        self.assertFalse(receipt.matches(value=True, cache_key=receipt.cache_key,
            verifier_name=receipt.verifier_name, verifier_revision=receipt.verifier_revision, parents=()))

    def test_cache_key_binds_every_context_component(self):
        values = dict(project_id='project',task_id='child',goal_hash=digest('goal'),contract_hash=digest('contract'),
                      verifier_name='sample:check',verifier_revision=identity().effective_revision,check_type='mechanical',
                      artifacts={'source':digest('source')},parents=())
        original = cache_key(**values)
        changes = dict(project_id='another', task_id='another', goal_hash=digest('goal2'), contract_hash=digest('contract2'),
            verifier_name='another:check', verifier_revision=identity('two').effective_revision, check_type='structural',
            artifacts={'source':digest('source2')}, parents=(ReceiptReference('a', digest('parent')),))
        for key, value in changes.items():
            with self.subTest(key=key): self.assertNotEqual(original, cache_key(**{**values,key:value}))


class RegistryTests(unittest.TestCase):
    def test_freezes_in_constructor_and_namespaces_lookups(self):
        registry = StationExtensionRegistry().register_module(Sample())
        self.assertFalse(registry.frozen)
        controller = LoopController(spec(), Verifier({}), Pass(), extensions=registry)
        self.assertTrue(registry.frozen)
        self.assertEqual(controller.run().outcome, RunOutcome.SUCCESS)
        self.assertEqual(list(registry.verifiers()), ['sample:check'])
        with self.assertRaises(ContractError): registry.register_module(Sample())
        with self.assertRaises(TypeError): registry.verifiers()['other'] = None

    def test_registration_rolls_back_bad_second_descriptor(self):
        class Broken(Sample):
            def verifiers(self): return {**super().verifiers(), 'bad': (CheckType.MECHANICAL, lambda a,b: True)}
        registry = StationExtensionRegistry()
        with self.assertRaises(ContractError): registry.register_module(Broken())
        self.assertEqual(registry.modules, ())
        self.assertEqual(registry.policies(), ())
        self.assertEqual(dict(registry.verifiers()), {})
        registry.register_module(Sample())

    def test_legacy_tuple_requires_explicit_identity(self):
        class Legacy(Sample):
            def verifiers(self): return {'check': (CheckType.MECHANICAL, lambda a,b: (CheckResult.PASS, 'ok'))}
        registry = StationExtensionRegistry()
        with self.assertRaises(ContractError): registry.register_module(Legacy())
        registry.register_module(Legacy(), revisions={'check':identity()})
        self.assertEqual(LoopController(spec(), Verifier({}), Pass(), extensions=registry).run().outcome, RunOutcome.SUCCESS)

    def test_rejects_double_prefix_and_check_order_mismatch(self):
        class Prefixed(Sample):
            def verifiers(self): return {'sample:check': super().verifiers()['check']}
        with self.assertRaises(ContractError): StationExtensionRegistry().register_module(Prefixed())
        class Judge(Sample):
            def verifiers(self): return {'check': VerifierDescriptor(CheckType.JUDGE,lambda a,b:(CheckResult.PASS,'ok'),identity())}
        with self.assertRaises(ContractError): LoopController(spec(), Verifier({}), Pass(), extensions=StationExtensionRegistry().register_module(Judge()))

    def test_boolean_policy_annotation_rejected_without_calling_it(self):
        calls = []
        class Wrong(Sample):
            def quarantine_policies(self):
                def policy(action) -> bool:
                    calls.append(action); return True
                return (policy,)
        with self.assertRaises(ContractError): StationExtensionRegistry().register_module(Wrong())
        self.assertEqual(calls, [])

    def test_runtime_invalid_policy_denies_and_all_policies_run(self):
        seen = []
        class Policies(Sample):
            def quarantine_policies(self): return (lambda a: True, lambda a: seen.append(a.name))
        registry = StationExtensionRegistry().register_module(Policies())
        gate = QuarantineStore(); held=gate.hold(ProposedAction('tool_call','read'))
        self.assertEqual(gate.evaluate(held,registry.policies()), PolicyDecision.DENY)
        self.assertEqual(seen, ['read'])

    def test_lifecycle_order_and_read_only_observer_failure(self):
        events = []
        class Hooks(Sample):
            def on_run_opened(self,spec): events.append('open-hook')
            def on_run_closed(self,result): events.append('close-hook'); raise RuntimeError('private detail')
            def on_event(self,kind,payload): raise RuntimeError('private detail')
        registry = StationExtensionRegistry().register_module(Hooks())
        def emit(kind,payload):
            if kind == 'checkpoint': events.append(payload['event'])
        result=LoopController(spec(),Verifier({}),Pass(),extensions=registry,emit=emit).run()
        self.assertEqual(result.outcome,RunOutcome.SUCCESS)
        self.assertEqual(events,['run_opened','open-hook','run_closed','close-hook'])
        self.assertTrue(registry.diagnostics)
        self.assertNotIn('private detail',json.dumps(registry.diagnostics))

    def test_open_failure_aborts_before_dispatch_and_closes_once(self):
        events=[]
        class Broken(Sample):
            def on_run_opened(self,spec): raise RuntimeError()
            def on_run_closed(self,result): events.append(result.outcome)
        harness=Pass(); registry=StationExtensionRegistry().register_module(Broken())
        result=LoopController(spec(),Verifier({}),harness,extensions=registry).run()
        self.assertEqual(result.outcome,RunOutcome.ABORTED)
        self.assertEqual(harness.calls,0)
        self.assertEqual(events,[RunOutcome.ABORTED])

    def test_failed_extension_brake_aborts_and_checks_remaining_brakes(self):
        seen=[]
        class BrokenBrake:
            name='broken'
            def reset(self): pass
            def update(self,event): raise RuntimeError()
        class OtherBrake(BrokenBrake):
            name='other'
            def update(self,event): seen.append(event['kind'])
        class Brakes(Sample):
            def brakes(self): return (BrokenBrake(),OtherBrake())
        harness=Pass()
        result=LoopController(spec(),Verifier({}),harness,extensions=StationExtensionRegistry().register_module(Brakes())).run()
        self.assertEqual(result.outcome,RunOutcome.ABORTED)
        self.assertEqual(harness.calls,0)
        self.assertEqual(seen,['checkpoint'])

    def test_fresh_brakes_for_repeat_run_and_shared_brake_rejected(self):
        created=[]
        class Brake:
            name='count'
            def reset(self): self.count=0
            def update(self,event): self.count+=1
        class Fresh(Sample):
            def brakes(self):
                brake=Brake();created.append(brake);return (brake,)
        controller=LoopController(spec(),Verifier({}),Pass(),extensions=StationExtensionRegistry().register_module(Fresh()))
        self.assertEqual(controller.run().outcome,RunOutcome.SUCCESS)
        self.assertEqual(controller.run().outcome,RunOutcome.SUCCESS)
        self.assertEqual(len(created),2)
        class Shared(Sample):
            def brakes(self): return (created[0],)
        controller=LoopController(spec(),Verifier({}),Pass(),extensions=StationExtensionRegistry().register_module(Shared()))
        self.assertEqual(controller.run().outcome,RunOutcome.SUCCESS)
        self.assertEqual(controller.run().outcome,RunOutcome.ABORTED)

    def test_same_registry_cannot_run_concurrently(self):
        registry=StationExtensionRegistry().register_module(Sample())
        controller=LoopController(spec(),Verifier({}),Pass(),extensions=registry)
        registry.acquire()
        try:
            with self.assertRaises(ContractError): controller.run()
        finally: registry.release()
        self.assertEqual(controller.run().outcome,RunOutcome.SUCCESS)

    def test_unknown_blocks_judge_without_becoming_failure(self):
        s=spec('missing')
        s=dataclasses.replace(s,success_criteria=(*s.success_criteria,SuccessCriterion('judge',CheckType.JUDGE,'Judge','judge')))
        called=[]
        report=Verifier({'missing':lambda c,p:(CheckResult.UNKNOWN,'no evidence'),
                         'judge':lambda c,p:(called.append(True) or CheckResult.PASS,'ok')}).verify({},s)
        self.assertFalse(report.overall_pass)
        self.assertEqual(report.primary_failure,'check')
        self.assertEqual(report.results[0].result,CheckResult.UNKNOWN)
        self.assertEqual(report.results[1].result,CheckResult.SKIPPED)
        self.assertEqual(called,[])

    def test_engine_module_adapter_keeps_strict_verdict(self):
        registry=Registry();StationExtensionRegistry().register_module(Sample()).register_checks(registry)
        registry.solver('yes',lambda context: True)
        task=Task('project','Validate',{},(Obligation('task','Check','sample:check',solver='yes'),))
        result=Harness(registry,None,None).run(task)
        self.assertTrue(result['success'])
        self.assertEqual(result['station_receipts']['task']['payload']['verifier_name'],'sample:check')


class EngineReceiptTests(unittest.TestCase):
    def setup_graph(self):
        r=Registry();register_builtins(r)
        for name in ('child','grandchild'):
            r.check(name,lambda v,c: Verdict.passed() if v is True else Verdict.fail('bad'), '1',identity=identity(name))
            r.solver(name,lambda c: True)
        task=Task('project','Run DAG',{'a':Artifact('a','true')},(
            Obligation('root','Read','json_value',('a',),parameters={'artifact':'a'},solver='json_value'),
            Obligation('child','Use root','child',depends_on=('root',),solver='child'),
            Obligation('grandchild','Use child','grandchild',depends_on=('child',),solver='grandchild')))
        return r,task

    def test_revision_change_invalidates_descendants_downward(self):
        r,task=self.setup_graph(); cache=Cache()
        try:
            h=Harness(r,None,None,cache=cache)
            original=h.run(task)
            self.assertEqual(h.run(task)['metrics']['cache_hits'],3)
            r.identities['json_value']=(identity('changed'), 'mechanical')
            changed=h.run(task)
            self.assertEqual(changed['metrics']['cache_hits'],0)
            for tid in ('root','child','grandchild'):
                self.assertNotEqual(original['station_receipts'][tid]['receipt_hash'],changed['station_receipts'][tid]['receipt_hash'])
            graph={tid:StationReceipt.from_dict(v) for tid,v in changed['station_receipts'].items()}
            validate_receipt_graph(graph,{o.id:o.depends_on for o in task.obligations})
        finally: cache.close()

    def test_intact_cache_receipt_still_runs_active_verifier(self):
        r,task=self.setup_graph();cache=Cache()
        try:
            h=Harness(r,None,None,cache=cache);h.run(task)
            rev,_=r.checks['json_value']; calls=[]
            r.checks['json_value']=(rev,lambda v,c:(calls.append(v) or Verdict('unknown','unavailable')))
            result=h.run(task)
            self.assertFalse(result['success']);self.assertEqual(result['metrics']['cache_hits'],0)
            self.assertGreater(len(calls),0);self.assertEqual(result['station_receipts'],{})
        finally: cache.close()

    def test_tampered_envelope_is_a_cache_miss(self):
        r,task=self.setup_graph();cache=Cache()
        try:
            h=Harness(r,None,None,cache=cache);h.run(task)
            rows=cache.db.execute('SELECT key,value FROM results').fetchall()
            for key,raw in rows:
                entry=json.loads(raw);entry['receipt']['payload']['verifier_revision']='f'*64
                cache.put(key,entry)
            self.assertEqual(h.run(task)['metrics']['cache_hits'],0)
        finally:cache.close()


if __name__=='__main__': unittest.main()
