import asyncio
import json
import tempfile
import unittest
from unittest.mock import patch
from ai_providers import *
from observation_layer import ObservationBus, ObservationKind, verify_chain
from observation_layer.sinks import InMemorySink
from residual.core import ContractError, canonical
from residual.modular import ModularProvider, normalized_usage
from residual.station.models import model_call,save_settings,public_settings
from residual.station.service import Station,demo_spec
from tests.modular.test_adapters import endpoint,OPENAI,ANTHROPIC,OLLAMA,REQ


class FakeProvider:
    name='openai'
    def __init__(self,outcome):self.outcome=outcome;self.calls=0
    def chat(self,req):
        self.calls+=1
        if isinstance(self.outcome,Exception):raise self.outcome
        return self.outcome
    def stream(self,req):
        self.calls+=1
        yield StreamChunk(content='prefix')
        raise ProviderError(provider=self.name,code='connection',retryable=True)


class RouterTests(unittest.TestCase):
    def test_attempts_correlate_failover_only_on_retryable_error(self):
        for code,retryable in [('authentication',False),('rate_limit',True)]:
            reg=Registry();one=FakeProvider(ProviderError(provider='openai',code=code,retryable=retryable));two=FakeProvider(ChatResponse('test','ok',usage={'prompt_tokens':9,'completion_tokens':2}));two.name='anthropic'
            reg.register('openai',lambda:one);reg.register('anthropic',lambda:two)
            mem=InMemorySink();receipts=[];router=Router(reg,observation_bus=ObservationBus(mem),after_attempt=receipts.append)
            if retryable:self.assertEqual(router.chat('openai:x',REQ,['anthropic:y']).content,'ok')
            else:
                with self.assertRaises(ProviderError):router.chat('openai:x',REQ,['anthropic:y'])
            self.assertEqual(two.calls,1 if retryable else 0)
            self.assertEqual(len(receipts),2 if retryable else 1)
            self.assertIn("response_metadata", receipts[-1])
            self.assertEqual(len({r['request_id'] for r in receipts}),1)
            self.assertTrue(verify_chain(mem.events));self.assertIn(ObservationKind.LLM_FAILED,[e.kind for e in mem.events])
            self.assertNotIn('Hello café',canonical([o.to_dict() for o in mem.events]))

    def test_stream_partial_failure_does_not_replay_on_fallback(self):
        reg=Registry();one=FakeProvider(None);two=FakeProvider(None);two.name='anthropic'
        reg.register('openai',lambda:one);reg.register('anthropic',lambda:two)
        mem=InMemorySink();r=Router(reg,observation_bus=ObservationBus(mem));stream=r.stream('openai:x',REQ,['anthropic:y'])
        self.assertEqual(next(stream).content,'prefix')
        with self.assertRaises(ProviderError):next(stream)
        self.assertEqual(two.calls,0);self.assertEqual(mem.events[-1].kind,ObservationKind.LLM_FAILED)
        self.assertNotIn('prefix',canonical([e.to_dict() for e in mem.events]))

    def test_observer_failure_does_not_mask_success_or_policy_refusal(self):
        class Broken:
            def emit(self,*a,**kw):raise RuntimeError('telemetry')
        reg=Registry();a=FakeProvider(ChatResponse('test','ok'));reg.register('openai',lambda:a)
        r=Router(reg,observation_bus=Broken());self.assertEqual(r.chat('openai:x',REQ).content,'ok');self.assertEqual(r.observation_errors,2)
        def refuse(*args):raise ContractError('budget exhausted')
        r=Router(reg,before_attempt=refuse)
        with self.assertRaises(ContractError):r.chat('openai:x',REQ)
        self.assertEqual(a.calls,1)


class StationRoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.s=Station(self.temp.name);self.pid=self.s.create(demo_spec(),demo=True,allow_cloud=True)['project_id']
    def tearDown(self):self.temp.cleanup()
    def configure(self,one,two=None):
        save_settings(self.s.store,{'cloud':{'kind':'openai','model':'primary','base_url':one},'cloud_fallbacks':[{'kind':'anthropic','model':'backup','base_url':two}] if two else [],'provider_credentials':{'openai':{'api_key':'OPENAI-SECRET'},'anthropic':{'api_key':'ANTHROPIC-SECRET'}}})

    def test_every_fallback_attempt_is_budgeted_and_counted_with_real_bytes(self):
        with endpoint(lambda _:(503,{'error':'OPENAI-SECRET'},{})) as (one,requests1),endpoint(lambda _:(200,ANTHROPIC,{})) as (two,requests2):
            self.configure(one,two)
            result=model_call(self.s.store,self.pid,'runner',{'source':'SENSITIVE CONTENT'},'SYSTEM',placement='cloud')
            self.assertEqual(result['text'],'ok')
        self.assertEqual(self.s.store.project(self.pid)['calls_reserved'],2)
        metrics=self.s.metrics(self.pid);self.assertEqual(metrics['calls'],2);self.assertEqual(metrics['cloud_input'],11);self.assertEqual(metrics['unreported_calls'],1)
        self.assertEqual(metrics['request_bytes'],len(requests1[0]['body'])+len(requests2[0]['body']))
        self.assertEqual(requests1[0]['headers']['Authorization'],'Bearer OPENAI-SECRET');self.assertEqual(requests2[0]['headers']['X-Api-Key'],'ANTHROPIC-SECRET')
        trace=self.s.store.observations(self.pid)['events'];text=canonical(trace)
        for secret in ['SENSITIVE CONTENT','OPENAI-SECRET','ANTHROPIC-SECRET']:self.assertNotIn(secret,text)
        self.assertEqual(self.s.store.observation_summary(self.pid)['integrity'],'verified')

    def test_budget_exhaustion_stops_fallback_before_network(self):
        with endpoint(lambda _:(503,{},{})) as (one,requests1),endpoint(lambda _:(200,ANTHROPIC,{})) as (two,requests2):
            self.configure(one,two)
            with self.s.store.transaction() as c:
                p=self.s.store._project(c,self.pid);p['cloud_call_limit']=1;c.execute('UPDATE projects SET value=? WHERE id=?',(canonical(p),self.pid))
            with self.assertRaisesRegex(ContractError,'budget'):model_call(self.s.store,self.pid,'runner',{},'S',placement='cloud')
            self.assertEqual(len(requests1),1);self.assertEqual(len(requests2),0)

    def test_cloud_disabled_stops_all_profiles_and_local_fallback_never_uses_cloud(self):
        with endpoint(lambda _:(200,OPENAI,{})) as (cloud,calls):
            self.configure(cloud)
            pid=self.s.create(demo_spec(),demo=True)['project_id']
            with self.assertRaisesRegex(ContractError,'disabled'):model_call(self.s.store,pid,'runner',{},'S',placement='cloud')
            self.assertEqual(calls,[])
        def response(req):
            return (503,{}, {}) if json.loads(req['body'])['model']=='first' else (200,OLLAMA,{})
        with endpoint(response) as (url,requests):
            save_settings(self.s.store,{'local':{'kind':'ollama','model':'first','base_url':url},'local_failover':['second']})
            self.assertEqual(model_call(self.s.store,pid,'runner',{},'S')['text'],'ok')
            self.assertEqual([json.loads(r['body'])['model'] for r in requests],['first','second'])
            self.assertEqual(self.s.store.project(pid)['cloud_calls_reserved'],0)

    def test_credentials_bind_to_provider_and_never_leak_to_local_profile_or_public_state(self):
        save_settings(self.s.store,{'cloud_key':'LEGACY-SECRET'})
        save_settings(self.s.store,{'cloud':{'kind':'anthropic','model':'c'}})
        s=self.s.store.settings();self.assertEqual(s['provider_credentials']['openai_compatible']['api_key'],'LEGACY-SECRET')
        with endpoint(lambda _:(200,OPENAI,{})) as (url,requests):
            save_settings(self.s.store,{'local':{'kind':'openai_compatible','model':'m','base_url':url}})
            with patch.dict('os.environ',{'LLM_API_KEY':'ENV-CLOUD-SECRET'}):model_call(self.s.store,None,'test',{},'S')
            self.assertNotIn('Authorization',requests[0]['headers'])
        self.assertNotIn('LEGACY-SECRET',canonical(public_settings(self.s.store)))
        save_settings(self.s.store,{'provider_credentials':{'openai_compatible':{'clear':True}}})
        self.assertFalse(self.s.store.settings()['provider_credentials']['openai_compatible'])

    def test_observation_volume_does_not_increase_llm_report_payload(self):
        before=canonical(self.s.store.report(self.pid))
        bus=self.s.store.observation_bus(self.pid)
        for i in range(100):bus.emit(ObservationKind.LLM_STREAM_CHUNK,{'chunk':i,'content_chars':25})
        self.assertEqual(canonical(self.s.store.report(self.pid)),before)

    def test_schema_truncation_and_bad_envelopes_never_return_a_candidate(self):
        for response in [{**OLLAMA,'done_reason':'length'}, {**OLLAMA,'message':{'content':'not json'}}]:
            with endpoint(lambda _:(200,response,{})) as (url,_):
                save_settings(self.s.store,{'local':{'kind':'ollama','model':'m','base_url':url}})
                with self.assertRaises(ContractError):model_call(self.s.store,self.pid,'runner',{},'S',schema={'type':'object'})

    def test_arena_key_can_be_saved_before_model_discovery(self):
        save_settings(self.s.store, {
            "cloud": {
                "kind": "arena",
                "model": "",
                "base_url": "https://api.preview.arena.ai/v1",
                "output_token_field": "max_completion_tokens",
            },
            "provider_credentials": {
                "arena": {"api_key": "ARENA-SETUP-SECRET"}
            },
        })
        settings = self.s.store.settings()
        self.assertEqual(settings["cloud"]["kind"], "arena")
        self.assertEqual(settings["cloud"]["model"], "")
        public = public_settings(self.s.store)
        self.assertTrue(public["credential_status"]["arena"]["saved"])
        self.assertEqual(
            public["providers"]["arena"]["setup_url"],
            "https://portal.api.preview.arena.ai/dashboard/keys",
        )
        self.assertNotIn("ARENA-SETUP-SECRET", canonical(public))
        with self.assertRaises(ContractError):
            model_call(self.s.store, self.pid, "runner", {}, "S", placement="cloud")

    def test_api_settings_refuse_wrong_local_classification_and_duplicate_routes(self):
        for value in [{'local':{'kind':'anthropic','model':'m'}},{'local':{'kind':'ollama','model':'m-cloud','base_url':'http://localhost:11434'}},{'cloud':{'kind':'anthropic','model':'m'},'cloud_fallbacks':[{'kind':'anthropic','model':'n'}]}]:
            with self.assertRaises(ContractError):save_settings(self.s.store,value)
