import concurrent.futures
import importlib.util
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from observation_layer import Observation, ObservationBus, ObservationKind, ObservationSequencer, TraceContext, verify_chain
from observation_layer.sinks import InMemorySink, NullSink
from observation_layer.filters import compose, allow_kinds, redact_payload, sample_every
from observation_layer.hooks import instrument_tool, llm_call
from observation_layer.query import load_jsonl
from residual.station.service import Station, demo_spec
from residual.station.models import save_settings


# Run every supplied test under the project's stdlib runner, including tmp_path fixtures.
source=Path(__file__).resolve().parents[2]/'vendor/user-modules/test_observation_original.py'
if not source.exists(): source=Path(__file__).resolve().parents[2].parent/'vendor/user-modules/test_observation_original.py'
module_spec=importlib.util.spec_from_file_location('uploaded_observation_tests',source)
original=importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(original)
class UploadedObservationTests(unittest.TestCase): pass
for name,cls in vars(original).items():
    if not name.startswith('Test') or not inspect.isclass(cls): continue
    for method in vars(cls):
        if not method.startswith('test_'): continue
        def wrap(self,klass=cls,name=method):
            with tempfile.TemporaryDirectory() as d:
                fn=getattr(klass(),name)
                fn(Path(d)) if 'tmp_path' in inspect.signature(fn).parameters else fn()
        setattr(UploadedObservationTests,'test_'+name+'_'+method[5:],wrap)


class ObservationIntegrityTests(unittest.TestCase):
    def test_filter_redaction_and_sampling_form_valid_retained_chain(self):
        mem=InMemorySink();bus=ObservationBus(mem,compose(allow_kinds('llm.request'),sample_every(2),redact_payload(['SECRET'])),trace_id='t')
        for i in range(12):
            bus.emit(ObservationKind.LLM_REQUEST,{'nested':[{'key':'SECRET'}]})
            bus.emit(ObservationKind.CHECKPOINT,{})
        self.assertEqual(len(mem.events),6)
        self.assertTrue(verify_chain(mem.events,expected_head=bus.sequencer.head_hash,expected_count=6))
        self.assertNotIn('SECRET',str(mem.events))

    def test_nested_payload_cannot_change_after_emission(self):
        payload={'nested':{'items':['x']}};bus=ObservationBus(InMemorySink())
        obs=bus.emit(ObservationKind.CHECKPOINT,payload);payload['nested']['items'].append('y')
        self.assertEqual(obs.payload['nested']['items'],('x',))
        with self.assertRaises(TypeError): obs.payload['nested']['key']='bad'
        object.__setattr__(obs,'payload',{'forged':True})
        self.assertFalse(verify_chain([obs]))

    def test_tail_deletion_detected_with_checkpoint_and_mixed_traces_refused(self):
        seq=ObservationSequencer('t');events=[seq.next(ObservationKind.CHECKPOINT,{}) for _ in range(3)]
        self.assertFalse(verify_chain(events[:-1],expected_head=seq.head_hash,expected_count=3))
        object.__setattr__(events[1],'trace_id','other')
        self.assertFalse(verify_chain(events))

    def test_invalid_json_replay_fails_visible_and_trace_context_cannot_relabel(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'trace.jsonl';p.write_text('{bad JSON}\n')
            with self.assertRaises(ValueError): list(load_jsonl(p))
        with self.assertRaises(ValueError): TraceContext(ObservationBus(trace_id='one'),'two')

    def test_filter_sink_and_custom_bus_failures_preserve_wrapped_results(self):
        def bad(_): raise RuntimeError('SECRET')
        bus=ObservationBus(InMemorySink(),filter=bad)
        @instrument_tool(bus,'add')
        def add(a,b): return a+b
        self.assertEqual(add(2,3),5);self.assertEqual(bus.errors,2)
        class Broken:
            def emit(self,*a,**kw): raise RuntimeError('SECRET')
        @instrument_tool(Broken(),'same')
        def same(): return 42
        self.assertEqual(same(),42)
        with llm_call(Broken(),'model'): pass

    def test_station_restart_concurrency_and_export_preserve_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            a=Station(d);pid=a.create(demo_spec(),demo=True)['project_id'];b=Station(d)
            def write(i):
                bus=(a if i%2 else b).store.observation_bus(pid)
                bus.emit(ObservationKind.CHECKPOINT,{'i':i})
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: list(pool.map(write,range(30)))
            c=Station(d);summary=c.store.observation_summary(pid)
            self.assertEqual(summary['integrity'],'verified');self.assertEqual(summary['event_count'],31)
            records=[Observation(**json.loads(line)) for line in c.store.observation_export(pid).splitlines()]
            self.assertTrue(verify_chain(records,expected_head=summary['head_hash'],expected_count=31))
            page=c.store.observations(pid,limit=10);page2=c.store.observations(pid,after=page['next_cursor'],limit=10)
            self.assertTrue(page['has_more']);self.assertFalse({e['obs_id'] for e in page['events']}&{e['obs_id'] for e in page2['events']})
            with c.store.transaction() as conn: conn.execute('DELETE FROM observations WHERE seq=(SELECT max(seq) FROM observations WHERE trace=?)',(pid,))
            self.assertEqual(c.store.observation_summary(pid)['integrity'],'failed')

    def test_observations_off_and_broken_sink_do_not_change_ldd_authority(self):
        with tempfile.TemporaryDirectory() as d:
            s=Station(d);save_settings(s.store,{'observations_enabled':False})
            pid=s.create(demo_spec(),demo=True)['project_id']
            self.assertEqual(s.batch(pid)['integrated'],3)
            self.assertEqual(s.store.observation_summary(pid)['event_count'],0)
            save_settings(s.store,{'observations_enabled':True})
            with patch.object(s.store,'_append_observation',side_effect=RuntimeError('broken telemetry')):
                s.store.event(pid,'project.note',{'message':'LDD fact'})
            self.assertEqual(s.store.events(pid)[-1]['data']['message'],'LDD fact')
            self.assertEqual(s.store.observation_failures,1)
            self.assertNotIn('llm.request',s.store.report(pid)['changes'])
