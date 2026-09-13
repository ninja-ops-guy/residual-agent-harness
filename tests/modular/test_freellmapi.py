"""Offline contract and integration tests. No real provider keys or free quota."""
import asyncio
import copy
import hashlib
import json
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from unittest.mock import patch

from ai_providers import ChatRequest, ChatResponse, Message, ProviderError, Registry, Role, Router, ToolCall, ToolSpec
from ai_providers.adapters._http import MAX_RESPONSE, encode
from ai_providers.adapters.freellmapi_adapter import FreeLLMAPIAdapter, UPSTREAM_ATTEMPT_RESERVATION
from observation_layer import ObservationBus, verify_chain
from observation_layer.sinks import InMemorySink
from residual.config import provider_from, registry_from
from residual.core import ContractError, canonical
from residual.modular import ModularProvider, normalize_profile
from residual.providers import Prices
from residual.station.models import model_call, save_settings, public_settings
from residual.station.service import Station, demo_spec, DEMO_FILES
from tests.modular.test_adapters import endpoint, REQ, OPENAI, ANTHROPIC, OLLAMA

HEADERS={'X-Routed-Via':'groq/test','X-FreeLLM-Compress':'off; saved~=0','X-FreeLLM-Cache':'OFF'}


def profile(url):
    return {'kind':'freellmapi','model':'test','base_url':url,'gateway_allowed_routes':['groq/test']}


def adapter(url, **kwargs):
    return FreeLLMAPIAdapter('GATEWAY-SECRET', url, ['groq/test'], **kwargs)


class GatewayTests(unittest.TestCase):
    def test_wire_headers_provenance_and_unknown_accounting(self):
        body=copy.deepcopy(OPENAI)
        body['metadata']={'gateway':{'actual_provider':'evil','secret':'DO-NOT-LOG'}}
        body['usage']['estimated']=True
        with endpoint(lambda _:(200,body,HEADERS)) as (url,calls):
            a=adapter(url); result=a.chat(REQ); again=a.chat(REQ)
        self.assertEqual(len(calls),2)
        self.assertEqual(calls[0]['path'],'/chat/completions')
        self.assertEqual(json.loads(calls[0]['body'])['max_tokens'],77)
        self.assertEqual(calls[0]['headers']['Authorization'],'Bearer GATEWAY-SECRET')
        self.assertEqual(calls[0]['headers']['X-Freellm-Compress'],'off')
        self.assertEqual(calls[0]['headers']['X-Freellm-Cache'],'off')
        self.assertNotEqual(calls[0]['headers']['X-Session-Id'],calls[1]['headers']['X-Session-Id'])
        self.assertEqual(result.content,'ok');self.assertEqual(result.usage,{})
        self.assertIsNone(result.raw)
        r=result.metadata['gateway']; signed=dict(r);h=signed.pop('receipt_sha256')
        self.assertEqual(h,hashlib.sha256(b'residual.gateway-report.v1\n'+encode(signed)).hexdigest())
        self.assertEqual(r['request_sha256'],hashlib.sha256(calls[0]['body']).hexdigest())
        self.assertEqual(r['response_sha256'],hashlib.sha256(encode(body)).hexdigest())
        self.assertEqual(r['upstream_attempts_reported'],1)
        self.assertFalse(r['accounting_complete']);self.assertTrue(r['usage_estimated'])
        self.assertFalse(r['transformations_verified']);self.assertIsNone(r['catalog_digest'])
        self.assertNotIn('DO-NOT-LOG',canonical(r))
        self.assertEqual(r,again.metadata['gateway'])

    def test_missing_invalid_and_unapproved_routes_fail_closed(self):
        for route in ['', 'cache','fusion:a+b','evil/test','groq/other','groq/test%0Asecret','groq/test; secret','groq/'+'a'*1000]:
            with self.subTest(route=route),endpoint(lambda _:(200,OPENAI,{**HEADERS,'X-Routed-Via':route})) as (url,calls):
                with self.assertRaises(ProviderError) as caught:adapter(url).chat(REQ)
                self.assertEqual(caught.exception.code,'invalid_response')
                self.assertFalse(caught.exception.retryable)

    def test_missing_compression_ack_and_cache_hits_are_rejected(self):
        for changes in [{'X-FreeLLM-Compress':''},{'X-FreeLLM-Compress':'standard; saved~=12'},{'X-FreeLLM-Cache':'HIT'}]:
            with self.subTest(changes=changes),endpoint(lambda _:(200,OPENAI,{**HEADERS,**changes})) as (url,_):
                with self.assertRaises(ProviderError):adapter(url).chat(REQ)

    def test_duplicate_provenance_headers_are_rejected(self):
        with endpoint(lambda _:(200,OPENAI,{**HEADERS,'X-Routed-Via':'groq/test\r\nX-Routed-Via: groq/test'})) as (url,_):
            with self.assertRaises(ProviderError):adapter(url).chat(REQ)

    def test_gateway_retry_counts_are_not_client_attempts(self):
        with endpoint(lambda _:(200,OPENAI,{**HEADERS,'X-Fallback-Attempts':'2','X-Fallback-Detail':'SECRET ERROR BODY'})) as (url,calls):
            result=adapter(url).chat(REQ)
            self.assertEqual(len(calls),1)
            self.assertEqual(result.metadata['gateway']['upstream_attempts_reported'],3)
            self.assertNotIn('SECRET',canonical(result.metadata))
        for count in ['-1','1.0','01','20','999','NaN']:
            with self.subTest(count=count),endpoint(lambda _:(200,OPENAI,{**HEADERS,'X-Fallback-Attempts':count})) as (url,_):
                with self.assertRaises(ProviderError):adapter(url).chat(REQ)

    def test_auto_requires_explicit_opt_in_and_still_checks_route(self):
        with endpoint(lambda _:(200,OPENAI,HEADERS)) as (url,calls):
            for model in ['auto','auto:batch','fusion','fusion:any','other']:
                with self.assertRaises(ProviderError):adapter(url).chat(replace(REQ,model=model))
            self.assertEqual(calls,[])
            self.assertEqual(adapter(url,allow_auto=True).chat(replace(REQ,model='auto:batch')).model,'test')
            with self.assertRaises(ProviderError):adapter(url,allow_auto=True).chat(replace(REQ,model='auto:bad profile'))

    def test_pinned_request_rejects_different_allowlisted_model(self):
        with endpoint(lambda _:(200,OPENAI,{**HEADERS,'X-Routed-Via':'groq/other'})) as (url,_):
            a=FreeLLMAPIAdapter('KEY',url,['groq/test','groq/other'])
            with self.assertRaises(ProviderError):a.chat(REQ)

    def test_tools_streaming_missing_cap_and_unsupported_options_never_dispatch(self):
        requests=[replace(REQ,tools=(ToolSpec('run','run',{}),)),
                  replace(REQ,messages=(Message(Role.TOOL,'result',tool_call_id='1'),)),
                  replace(REQ,messages=(Message(Role.ASSISTANT,'',tool_calls=(ToolCall('1','run','{}'),)),)),
                  replace(REQ,max_tokens=None),replace(REQ,max_tokens=16001),replace(REQ,extra={'reasoning_effort':'high'})]
        with endpoint(lambda _:(200,OPENAI,HEADERS)) as (url,calls):
            a=adapter(url)
            for req in requests:
                with self.assertRaises(ProviderError):a.chat(req)
            with self.assertRaises(ProviderError):list(a.stream(REQ))
            async def run():return [c async for c in a.astream(REQ)]
            with self.assertRaises(ProviderError):asyncio.run(run())
            self.assertEqual(calls,[]);self.assertFalse(a.supports_tools('test'))

    def test_unsolicited_tool_calls_cannot_become_actions(self):
        data=copy.deepcopy(OPENAI)
        data['choices'][0]['message']['tool_calls']=[{'id':'x','function':{'name':'execute','arguments':'{}'}}]
        with endpoint(lambda _:(200,data,HEADERS)) as (url,_):
            with self.assertRaises(ProviderError):adapter(url).chat(REQ)

    def test_endpoint_credentials_and_allowlist_validation(self):
        for kw in [{'api_key':''},{'api_key':'KEY\nsecret'},{'base_url':'http://remote.example/v1'},
                   {'base_url':'https://user:pass@example.com/v1'},{'base_url':'https://example.com/v1?q=secret'},
                   {'allowed_routes':[]},{'allowed_routes':['groq/test','groq/test']},
                   {'allowed_routes':['invalid']},{'allow_auto':'true'},{'timeout':float('nan')},{'timeout':True}]:
            with self.subTest(kw=kw),self.assertRaises(ProviderError):
                FreeLLMAPIAdapter(**{'api_key':'KEY','allowed_routes':['groq/test'],**kw})

    def test_http_errors_are_redacted_and_retryability_preserved(self):
        for status,code,retry in [(401,'authentication',False),(403,'authentication',False),(429,'rate_limit',True),(503,'server_error',True)]:
            with self.subTest(status=status),endpoint(lambda _:(status,{'error':'UPSTREAM SECRET'},{'Retry-After':'2'})) as (url,calls):
                with self.assertRaises(ProviderError) as ctx:adapter(url).chat(REQ)
                self.assertEqual(ctx.exception.code,code);self.assertEqual(ctx.exception.retryable,retry)
                self.assertNotIn('SECRET',str(ctx.exception));self.assertEqual(len(calls),1)

    def test_invalid_json_duplicate_keys_and_oversized_body(self):
        for body in [b'no json',b'{"choices":[],"choices":[]}',b'[]',b'X'*(MAX_RESPONSE+1)]:
            with self.subTest(size=len(body)),endpoint(lambda _:(200,body,HEADERS)) as (url,_):
                with self.assertRaises(ProviderError):adapter(url).chat(REQ)

    def test_redirect_does_not_forward_credentials(self):
        with endpoint(lambda _:(200,OPENAI,HEADERS)) as (target,leaks):
            with endpoint(lambda _:(302,{}, {'Location':target})) as (url,_):
                with self.assertRaises(ProviderError):adapter(url).chat(REQ)
            self.assertEqual(leaks,[])

    def test_timeout_is_bounded_and_releases_capacity(self):
        def delayed(_):time.sleep(.1);return 200,OPENAI,HEADERS
        with endpoint(delayed) as (url,_):
            with self.assertRaises(ProviderError) as ctx:adapter(url,timeout=.02).chat(REQ)
            self.assertEqual(ctx.exception.code,'timeout')
            self.assertEqual(adapter(url,timeout=1).chat(REQ).content,'ok')

    def test_async_chat_and_allowlisted_discovery(self):
        with endpoint(lambda r:(200,{'data':[{'id':'test'},{'id':'unapproved'}]} if r['path'].endswith('/models') else OPENAI,HEADERS)) as (url,_):
            a=adapter(url);self.assertEqual(a.list_models(),['test'])
            self.assertEqual(asyncio.run(a.achat(REQ)).content,'ok')

    def test_shared_backpressure_across_adapter_instances(self):
        ready=threading.Event();release=threading.Event();lock=threading.Lock();count=0
        def delayed(_):
            nonlocal count
            with lock:
                count+=1
                if count==2:ready.set()
            release.wait(3)
            return 200,OPENAI,HEADERS
        with endpoint(delayed) as (url,calls),ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(adapter(url).chat,REQ) for _ in range(2)]
            try:
                self.assertTrue(ready.wait(2))
                with self.assertRaises(ProviderError) as ctx:adapter(url).chat(REQ)
                self.assertEqual(ctx.exception.code,'rate_limit');self.assertEqual(len(calls),2)
            finally:release.set()
            self.assertEqual([f.result().content for f in futures],['ok','ok'])
            self.assertEqual(adapter(url).chat(REQ).content,'ok')

    def test_router_reports_hash_bound_gateway_metadata_without_prompts(self):
        with endpoint(lambda _:(200,OPENAI,HEADERS)) as (url,_):
            reg=Registry();reg.register('freellmapi',lambda:adapter(url));sink=InMemorySink();receipts=[]
            router=Router(reg,observation_bus=ObservationBus(sink),after_attempt=receipts.append)
            router.chat('freellmapi:test',REQ)
        self.assertIn('gateway',receipts[0]);self.assertTrue(verify_chain(sink.events))
        trace=canonical([e.to_dict() for e in sink.events])
        self.assertNotIn('Hello café',trace);self.assertNotIn('GATEWAY-SECRET',trace)


class GatewayStationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Station(self.tmp.name)
        self.pid=self.s.create(demo_spec(),demo=True,allow_cloud=True)['project_id']
    def tearDown(self):self.tmp.cleanup()
    def configure(self,url,fallbacks=None):
        save_settings(self.s.store,{'cloud':profile(url),'cloud_fallbacks':fallbacks or [],
            'provider_credentials':{'freellmapi':{'api_key':'GATEWAY-SECRET'}}})

    def test_settings_round_trip_and_never_local_placement(self):
        self.configure('http://127.0.0.1:3001/v1')
        s=public_settings(self.s.store)
        self.assertEqual(s['cloud']['kind'],'freellmapi');self.assertEqual(s['cloud']['output_token_field'],'max_tokens')
        self.assertEqual(s['cloud']['gateway_allowed_routes'],['groq/test'])
        self.assertNotIn('GATEWAY-SECRET',canonical(s))
        with self.assertRaises(ContractError):save_settings(self.s.store,{'local':profile('http://127.0.0.1:3001/v1')})
        with self.assertRaises(ContractError):normalize_profile({'kind':'ollama','model':'test','gateway_allowed_routes':['groq/test']},'local')

    def test_opt_in_configuration_requires_allowlist(self):
        for changes in [{'gateway_allowed_routes':[]},{'model':'auto'},{'gateway_allow_auto':'yes'},{'model':'unknown'}]:
            with self.subTest(changes=changes),self.assertRaises(ContractError):
                save_settings(self.s.store,{'cloud':{**profile('http://127.0.0.1:3001/v1'),**changes}})
        p=normalize_profile({**profile('http://127.0.0.1:3001/v1'),'model':'auto:batch','gateway_allow_auto':True},'remote')
        self.assertTrue(p['gateway_allow_auto'])

    def test_conservative_reservation_usage_and_receipt(self):
        with endpoint(lambda _:(200,OPENAI,{**HEADERS,'X-Fallback-Attempts':'2'})) as (url,calls):
            self.configure(url);result=model_call(self.s.store,self.pid,'runner',{},'system',placement='cloud')
        self.assertEqual(result['text'],'ok');self.assertEqual(result['usage']['source'],'unavailable')
        p=self.s.store.project(self.pid)
        self.assertEqual(p['calls_reserved'],20);self.assertEqual(p['cloud_calls_reserved'],20)
        self.assertEqual(p['request_bytes_reserved'],len(calls[0]['body']))
        metrics=self.s.metrics(self.pid);self.assertEqual(metrics['gateway_calls'],1)
        self.assertEqual(metrics['gateway_upstream_attempts_reported'],3)
        self.assertEqual(metrics['unreported_calls'],1);self.assertEqual(metrics['cloud_output'],0)
        self.assertEqual(self.s.store.observation_summary(self.pid)['integrity'],'verified')

    def test_atomic_budget_failure_does_not_dispatch_or_partially_reserve(self):
        with endpoint(lambda _:(200,OPENAI,HEADERS)) as (url,calls):
            self.configure(url);model_call(self.s.store,self.pid,'runner',{},'s',placement='cloud')
            with self.assertRaisesRegex(ContractError,'budget'):
                model_call(self.s.store,self.pid,'runner',{},'s',placement='cloud')
            self.assertEqual(len(calls),1)
        self.assertEqual(self.s.store.project(self.pid)['calls_reserved'],20)

    def test_concurrent_reservations_cannot_overspend(self):
        with endpoint(lambda _:(200,OPENAI,HEADERS)) as (url,calls),ThreadPoolExecutor(max_workers=2) as pool:
            self.configure(url)
            fs=[pool.submit(model_call,self.s.store,self.pid,'runner',{},'s',placement='cloud') for _ in range(2)]
            successes=0
            for f in fs:
                try:f.result();successes+=1
                except ContractError:pass
            self.assertEqual(successes,1);self.assertEqual(len(calls),1)
            self.assertEqual(self.s.store.project(self.pid)['calls_reserved'],20)

    def test_cloud_disabled_and_approval_review_never_dispatch(self):
        with endpoint(lambda _:(200,OPENAI,HEADERS)) as (url,calls):
            self.configure(url);pid=self.s.create(demo_spec(),demo=True)['project_id']
            with self.assertRaisesRegex(ContractError,'disabled'):model_call(self.s.store,pid,'runner',{},'s',placement='cloud')
            with self.assertRaisesRegex(ContractError,'approval review'):model_call(self.s.store,self.pid,'reviewer',{},'s',placement='cloud')
            self.assertEqual(calls,[])

    def test_retryable_gateway_failure_uses_explicit_direct_fallback(self):
        with endpoint(lambda _:(503,{'error':'SECRET'},{})) as (one,calls1),endpoint(lambda _:(200,ANTHROPIC,{})) as (two,calls2):
            self.configure(one,[{'kind':'anthropic','model':'backup','base_url':two}])
            self.assertEqual(model_call(self.s.store,self.pid,'runner',{},'s',placement='cloud')['text'],'ok')
            self.assertEqual(len(calls1),1);self.assertEqual(len(calls2),1)
            self.assertNotIn('GATEWAY-SECRET',repr(calls2))
        self.assertEqual(self.s.store.project(self.pid)['calls_reserved'],21)

    def test_provenance_refusal_does_not_silently_fallback(self):
        with endpoint(lambda _:(200,OPENAI,{})) as (one,_),endpoint(lambda _:(200,ANTHROPIC,{})) as (two,calls2):
            self.configure(one,[{'kind':'anthropic','model':'backup','base_url':two}])
            with self.assertRaises(ProviderError):model_call(self.s.store,self.pid,'runner',{},'s',placement='cloud')
            self.assertEqual(calls2,[])

    def test_cli_factory_and_prices_never_claim_zero_cost(self):
        with endpoint(lambda _:(200,OPENAI,HEADERS)) as (url,_):
            config={**profile(url),'placement':'remote','api_key_env':'TEST_GATEWAY_KEY','prices':{'input_per_million':0,'output_per_million':0}}
            with patch.dict('os.environ',{'TEST_GATEWAY_KEY':'GATEWAY-SECRET'}):
                provider=provider_from(config,registry_from({}));reply=provider.generate({},77)
            self.assertEqual(reply.text,'ok');self.assertIsNone(provider.prices.cost(reply.usage))

    def test_candidate_must_pass_existing_checks_and_direct_review(self):
        self.s.triage(self.pid)
        with self.s.store.transaction() as c:
            p=self.s.store._project(c,self.pid);p['mode']='live'
            c.execute('UPDATE projects SET value=? WHERE id=?',(canonical(p),self.pid))
        self.s.store.update_task(self.pid,'OPS-101',route='cloud')
        candidate=copy.deepcopy(OPENAI);candidate['choices'][0]['message']['content']=canonical({'files':DEMO_FILES['OPS-101']})
        reviewer=copy.deepcopy(OLLAMA);reviewer['message']['content']=canonical({'approved':True,'findings':[]})
        with endpoint(lambda _:(200,candidate,HEADERS)) as (url,calls),endpoint(lambda _:(200,reviewer,{})) as (local,review_calls):
            self.configure(url)
            save_settings(self.s.store,{'local':{'kind':'ollama','model':'test','base_url':local}})
            self.s.run_one(self.pid,'OPS-101')
            self.assertEqual(self.s.store.task(self.pid,'OPS-101')['state'],'review_ready')
            self.s.review(self.pid,'OPS-101');self.s.integrate(self.pid,'OPS-101')
            self.assertEqual(self.s.store.task(self.pid,'OPS-101')['state'],'integrated')
            self.assertEqual(len(calls),1);self.assertEqual(len(review_calls),1)
        self.assertNotEqual(self.s.store.task(self.pid,'OPS-103')['state'],'integrated')

    def test_parallel_dag_wave_correlates_tasks_and_unknown_usage_stops_expansion(self):
        from residual.station.control import run_controlled_batch
        self.s.triage(self.pid)
        with self.s.store.transaction() as c:
            p=self.s.store._project(c,self.pid);p.update(mode='live',cloud_call_limit=100)
            c.execute('UPDATE projects SET value=? WHERE id=?',(canonical(p),self.pid))
        for tid in DEMO_FILES:self.s.store.update_task(self.pid,tid,route='cloud')
        seen=[]
        def generate(request):
            packet=json.loads(json.loads(request['body'])['messages'][-1]['content'])
            tid=packet['task_id'];seen.append(tid)
            # Deliberately change completion order; association uses task_id.
            if tid=='OPS-101':time.sleep(.03)
            data=copy.deepcopy(OPENAI);data['choices'][0]['message']['content']=canonical({'files':DEMO_FILES[tid]})
            return 200,data,HEADERS
        reviewer=copy.deepcopy(OLLAMA);reviewer['message']['content']=canonical({'approved':True,'findings':[]})
        with endpoint(generate) as (url,_),endpoint(lambda _:(200,reviewer,{})) as (local,_):
            self.configure(url)
            save_settings(self.s.store,{'local':{'kind':'ollama','model':'test','base_url':local},'workers':2})
            # Triage already occurred against the same immutable manifest.
            with patch.object(self.s,'triage',return_value=None):
                result=run_controlled_batch(self.s,self.pid,lambda *a:None)
        self.assertCountEqual(seen,['OPS-101','OPS-102'])
        self.assertEqual(result['integrated'],2)
        self.assertEqual(result['control']['outcome'],'aborted')
        self.assertEqual(result['control']['passes'],1)
        self.assertIsNone(result['control']['tokens'])
        self.assertIn('usage_unknown_or_invalid',result['control']['trip_reasons'])
        self.assertNotEqual(self.s.store.task(self.pid,'OPS-103')['state'],'integrated')

    def test_no_gateway_configuration_or_credentials_is_not_implicitly_enabled(self):
        from ai_providers.registry import _default_registry
        with patch.dict('os.environ',{},clear=True):
            with self.assertRaises(ProviderError):_default_registry().get('freellmapi')
        self.assertNotEqual(public_settings(self.s.store)['cloud']['kind'],'freellmapi')
