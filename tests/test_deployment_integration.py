"""Regression tests for real host lifecycle and measurable cache contracts."""
import dataclasses
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from residual import AmendmentRule, CheckResult, CheckType, GoalSpec, LoopController, SuccessCriterion, Verifier
from residual.core import ContractError, digest
from residual.lifecycle import ModuleLifecycleBus, bind_memory, bind_trajectory, bind_tui
from residual.memory import EpistemicMemoryStore, MemoryContextAssembler, MemoryRequest
from residual.receipts import StationReceipt, cache_key
from residual.trajectory import TrajectoryRecorder, GoldenTrajectoryStore
from residual.tui import ObservationCollector, StationTUI


def goal():
    return GoalSpec('goal', 'Check candidate', (SuccessCriterion('one',CheckType.MECHANICAL,'Check','host'),),
                    1,100,10,AmendmentRule(('operator',)))


class Pass:
    def __init__(self, value=True, usage=0): self.value,self.usage=value,usage
    def run_pass(self,spec,number):
        return {'candidate':self.value, 'tokens_used':self.usage}


def receipt():
    return StationReceipt('task',digest('binding'),digest(True),'host:check',digest('revision'),CheckResult.PASS)


class LifecycleIntegrationTests(unittest.TestCase):
    def test_deepcopy_crash_and_wildcard_once(self):
        bus=ModuleLifecycleBus(include_metrics=False); seen=[]
        def corrupt(event,payload): payload['nested']['value']=False
        bus.subscribe('*',corrupt); bus.subscribe('*',lambda e,p:seen.append(p['nested']['value']))
        original={'nested':{'value':True}}
        bus.emit('*',original)
        self.assertEqual(seen,[True]); self.assertTrue(original['nested']['value'])

    def test_exception_closes_once_and_does_not_index_memory(self):
        class Broken(Pass):
            def run_pass(self,spec,number): raise RuntimeError('sensitive detail')
        with tempfile.TemporaryDirectory() as td:
            bus=ModuleLifecycleBus(include_metrics=False); closed=[]; traces=[]; resolved=[]
            bus.subscribe('run_closed',lambda e,p:closed.append(p))
            bind_trajectory(bus,TrajectoryRecorder(td+'/traces'),publish=traces.append)
            bind_memory(bus,EpistemicMemoryStore(td+'/memory'),lambda result:resolved.append(result) or [])
            with self.assertRaisesRegex(RuntimeError,'sensitive detail'):
                LoopController(goal(),Verifier({}),Broken(),lifecycle=bus).run()
            self.assertEqual(len(closed),1); self.assertEqual(closed[0]['outcome'],'aborted')
            self.assertEqual(traces[0].outcome,'aborted'); self.assertEqual(resolved,[])
            self.assertNotIn('sensitive detail',str(closed))

    def test_real_tui_thread_stops_on_detach(self):
        collector=ObservationCollector(); tui=StationTUI(collector,refresh_hz=30)
        rendered=threading.Event(); render_threads=[]
        def render(): render_threads.append(threading.get_ident()); rendered.set()
        tui._render=render
        bus=ModuleLifecycleBus(include_metrics=False)
        binding=bind_tui(bus,collector,tui)
        try:
            self.assertTrue(rendered.wait(2))
            result=LoopController(goal(),Verifier({'host':lambda c,p:(CheckResult.PASS,'ok')}),Pass(),lifecycle=bus).run()
            self.assertEqual(collector.snapshot().status,result.outcome.value)
            self.assertNotIn(threading.get_ident(),render_threads)
        finally: binding.close(); binding.close()
        self.assertIsNone(tui._thread)

    def test_memory_assembly_live_reverify_revision_budget_and_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            store=EpistemicMemoryStore(td); r=receipt(); verified=[]
            store.index('known',r.receipt_hash,{'receipt':r.to_dict(),'value':True},r.verifier_revision)
            request=MemoryRequest('known','known',r.verifier_revision,
                lambda received,value:verified.append(received.cache_key) or (received.cache_key==r.cache_key and value is True))
            context=MemoryContextAssembler(store,(request,)).assemble()
            self.assertTrue(context.values['memory']['known']['value']); self.assertEqual(verified,[r.cache_key])
            stale=dataclasses.replace(request,verifier_revision=digest('different'))
            self.assertEqual(MemoryContextAssembler(store,(stale,)).assemble().values['memory'],{})
            rejected=dataclasses.replace(request,verify=lambda r,v:False)
            self.assertEqual(MemoryContextAssembler(store,(rejected,)).assemble().values['memory'],{})
            with self.assertRaises(ContractError): MemoryContextAssembler(store,(),max_bytes=1).assemble()
            file=next(Path(td).glob('*.json')); data=json.loads(file.read_text()); data['artifact_payload']['value']=False
            file.write_text(json.dumps(data))
            self.assertEqual(MemoryContextAssembler(store,(request,)).assemble().values['memory'],{})

    def test_golden_requires_success_integrity_and_explicit_cas(self):
        with tempfile.TemporaryDirectory() as td:
            recorder=TrajectoryRecorder(td+'/traces'); store=GoldenTrajectoryStore(td+'/goldens.sqlite3',recorder)
            success=recorder.record('goal',[],[],'success'); failure=recorder.record('goal',[],[],'aborted')
            with self.assertRaises(ContractError): store.promote('demo',failure.trajectory_hash)
            store.promote('demo',success.trajectory_hash)
            with self.assertRaises(ContractError): store.promote('demo',success.trajectory_hash)
            store.promote('demo',success.trajectory_hash,expected=success.trajectory_hash)
            self.assertTrue(store.compare('demo',success)[0])
            self.assertFalse(store.compare('demo',failure)[0])

    def test_examples_and_compatibility_aliases(self):
        from examples.deployment.lifecycle import run
        from residual.extensions import StationReceipt as Exported
        self.assertIs(Exported,StationReceipt)
        with tempfile.TemporaryDirectory() as td: self.assertEqual(run(td)['memory_value'],5)
        args=dict(project_id='p',task_id='t',goal_hash=digest('g'),contract_hash=digest('c'),verifier_name='host:one',
                  verifier_revision=digest('r'),check_type='mechanical',artifacts={},parents=())
        self.assertEqual(StationReceipt.compute_cache_key(**args),cache_key(**args))

    def test_station_optins_reach_actual_controller(self):
        from residual.station.service import Station, demo_spec
        from residual.station.deployment import deployment_extensions
        from residual.hitl import HITLEscalationGateway
        with tempfile.TemporaryDirectory() as td:
            gateway=HITLEscalationGateway(b'x'*32,td+'/hitl',authenticate=lambda r,b,role:False)
            station=Station(td+'/station',extension_factory=deployment_extensions(hitl_gateway=gateway,tui=True))
            pid=station.create(demo_spec(),demo=True)['project_id']
            registry=station.extensions(pid)
            self.assertIn(('terminal','1.0.0'),registry.modules)
            closed=[]
            with patch('residual.tui.StationTUI._render',lambda self:None):
                result=LoopController(goal(),Verifier({'host':lambda c,p:(CheckResult.FAIL,'not yet')}),Pass(),
                    extensions=registry).run()
            self.assertEqual(result.outcome.value,'escalated')
            self.assertEqual(len(gateway.list_challenges(('operator',))['challenges']),1)
            traces=Path(td+'/station/extensions/'+pid+'/trajectories')
            self.assertEqual(len(list(traces.glob('*.json'))),1)
            self.assertFalse(list(Path(td+'/station/extensions/'+pid+'/memory').glob('*.json')))


class CacheMeasurementTests(unittest.TestCase):
    def test_fixture_tests_measurement_plumbing_not_live_inference(self):
        from residual.benchmark_live import run_trial, aggregate
        from residual.providers import CallableProvider, Reply, Usage
        def provider():
            def generate(packet,limit):
                evidence=json.loads(packet['evidence'][0]['text'])
                values={'total':sum(evidence['numbers']),'label':evidence['label']}
                return Reply(json.dumps({'updates':{o['id']:values[o['id']] for o in packet['obligations']},'requests':[]}),
                             Usage(12,4,source='simulation'))
            return CallableProvider('fixture',generate)
        trial=run_trial(provider,0,repeats=2); result=aggregate([trial])
        self.assertTrue(result['validation_passed'])
        self.assertFalse(result['usage_complete']); self.assertIsNone(result['measured_token_reduction'])
        self.assertEqual(result['avoided_calls'],4)
        self.assertEqual(trial['changed_evidence']['cache_hits'],0)

    def test_missing_ollama_writes_unknown_not_fake_savings(self):
        from residual.benchmark_live import main
        with tempfile.TemporaryDirectory() as td, patch('residual.benchmark_live.model_identity',side_effect=OSError('private')):
            path=td+'/result.json'; self.assertEqual(main(['--output',path]),3)
            data=json.loads(Path(path).read_text())
            self.assertEqual(data['status'],'blocked'); self.assertIsNone(data['token_savings'])
            self.assertFalse(data['live_model_validated']); self.assertNotIn('private',json.dumps(data))
