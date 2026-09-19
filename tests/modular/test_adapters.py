import asyncio
import contextlib
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from ai_providers import *
from ai_providers.adapters.openai_adapter import OpenAIAdapter, OpenAICompatibleAdapter
from ai_providers.adapters.arena_adapter import ArenaAdapter
from ai_providers.adapters.anthropic_adapter import AnthropicAdapter
from ai_providers.adapters.azure_adapter import AzureAdapter
from ai_providers.adapters.google_adapter import GoogleAdapter
from ai_providers.adapters.bedrock_adapter import BedrockAdapter
from ai_providers.adapters.ollama_adapter import OllamaAdapter
from ai_providers.adapters._http import encode, map_http_error
from observation_layer import ObservationBus, ObservationKind, verify_chain
from observation_layer.sinks import InMemorySink


@contextlib.contextmanager
def endpoint(responder):
    requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*a): pass
        def do_GET(self): self.do_POST()
        def do_POST(self):
            raw=self.rfile.read(int(self.headers.get('Content-Length','0')))
            req={'path':self.path,'headers':dict(self.headers),'body':raw};requests.append(req)
            status,body,headers=responder(req)
            raw=body if isinstance(body,bytes) else encode(body)
            self.send_response(status)
            self.send_header('Content-Length',str(len(raw)))
            for k,v in headers.items():self.send_header(k,v)
            self.end_headers()
            try:self.wfile.write(raw)
            except BrokenPipeError:pass
    http=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=lambda:http.serve_forever(poll_interval=.02),daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{http.server_port}',requests
    finally:http.shutdown();http.server_close();thread.join()


def sse(*events): return ''.join('data: '+(e if isinstance(e,str) else json.dumps(e))+'\n\n' for e in events).encode()
REQ=ChatRequest('test',(Message(Role.SYSTEM,'System'),Message(Role.USER,'Hello café')),max_tokens=77)
OPENAI={'model':'test','choices':[{'message':{'content':'ok'},'finish_reason':'stop'}],'usage':{'prompt_tokens':11,'completion_tokens':7}}
ANTHROPIC={'model':'test','content':[{'type':'text','text':'ok'}],'stop_reason':'end_turn','usage':{'input_tokens':8,'output_tokens':7,'cache_creation_input_tokens':1,'cache_read_input_tokens':2}}
GOOGLE={'candidates':[{'content':{'parts':[{'text':'ok'}]},'finishReason':'STOP'}],'usageMetadata':{'promptTokenCount':11,'candidatesTokenCount':4,'thoughtsTokenCount':3,'totalTokenCount':18}}
BEDROCK={'output':{'message':{'content':[{'text':'ok'}]}},'stopReason':'end_turn','usage':{'inputTokens':11,'outputTokens':7,'totalTokens':18}}
OLLAMA={'model':'test','message':{'content':'ok'},'done':True,'done_reason':'stop','prompt_eval_count':11,'eval_count':7}


def adapters(base):
    return [OpenAIAdapter('KEY',base),OpenAICompatibleAdapter('KEY',base),AnthropicAdapter('KEY',base),GoogleAdapter('KEY',base),AzureAdapter('KEY',base),BedrockAdapter('ACCESS','SECRET',session_token='SESSION',base_url=base),OllamaAdapter(base)]


class AdapterTests(unittest.TestCase):
    def test_all_seven_routes_send_exact_framing_and_preserve_usage(self):
        responses=[OPENAI,OPENAI,ANTHROPIC,GOOGLE,OPENAI,BEDROCK,OLLAMA]
        for index,response in enumerate(responses):
            with self.subTest(index=index),endpoint(lambda _: (200,response,{})) as (url,requests):
                a=adapters(url)[index];resp=a.chat(REQ)
                self.assertEqual(resp.content,'ok');self.assertEqual(resp.usage['prompt_tokens'],11);self.assertEqual(resp.usage['completion_tokens'],7)
                self.assertEqual(a.wire_bytes(REQ),requests[0]['body'])
                body=json.loads(requests[0]['body']);self.assertNotIn('KEY',requests[0]['body'].decode())
                self.assertNotIn('KEY',requests[0]['path'])
                self.assertIn('77',requests[0]['body'].decode())
                if a.name=='azure':self.assertNotIn('model',body)
                if a.name=='bedrock':self.assertIn('SignedHeaders=content-type;host;x-amz-date;x-amz-security-token',requests[0]['headers']['Authorization'])

    def test_arena_disables_gateway_fallback_and_preserves_safe_provenance(self):
        headers = {
            "X-Arena-Resolved-Model": "resolved-model",
            "X-Arena-Trace-ID": "arena-trace-123",
        }
        with endpoint(lambda _:(200,OPENAI,headers)) as (url,requests):
            adapter = ArenaAdapter("ARENA-SECRET", url)
            response = adapter.chat(REQ)
            body = json.loads(requests[0]["body"])
            self.assertIs(body["allow_fallbacks"], False)
            self.assertNotIn("fallbacks", body)
            self.assertNotIn("fallback_on", body)
            self.assertEqual(requests[0]["headers"]["Authorization"], "Bearer ARENA-SECRET")
            self.assertEqual(response.metadata["arena_resolved_model"], "resolved-model")
            self.assertEqual(response.metadata["arena_trace_id"], "arena-trace-123")
            self.assertIs(response.metadata["arena_fallback_used"], False)
            self.assertNotIn("ARENA-SECRET", json.dumps(response.metadata))
        with endpoint(lambda _:(200,OPENAI,{
            "X-Arena-Resolved-Model":"backup-model",
            "X-Arena-Trace-ID":"arena-trace-456",
            "X-Arena-Fallback-Index":"1",
            "X-Arena-Fallback-Reason":"503",
        })) as (url,_):
            with self.assertRaises(ProviderError) as error:
                ArenaAdapter("KEY", url).chat(REQ)
            self.assertEqual(error.exception.code, "invalid_response")

    def test_arena_stream_rejects_fallback_headers_before_content(self):
        body = sse(
            {'choices':[{'delta':{'content':'ok'},'finish_reason':'stop'}]},
            '[DONE]',
        )
        with endpoint(lambda _:(200,body,{
            'X-Arena-Resolved-Model':'model-a',
            'X-Arena-Trace-ID':'trace-stream-ok',
        })) as (url,_):
            chunks=list(ArenaAdapter('KEY',url).stream(REQ))
            self.assertEqual(''.join(chunk.content or '' for chunk in chunks),'ok')
        with endpoint(lambda _:(200,body,{
            'X-Arena-Resolved-Model':'backup-model',
            'X-Arena-Trace-ID':'trace-stream-bad',
            'X-Arena-Fallback-Index':'1',
            'X-Arena-Fallback-Reason':'transport_error',
        })) as (url,_):
            stream=ArenaAdapter('KEY',url).stream(REQ)
            with self.assertRaises(ProviderError) as error:
                next(stream)
            self.assertEqual(error.exception.code,'invalid_response')

    def test_arena_model_discovery_uses_bearer_auth_and_sorted_openai_shape(self):
        with endpoint(lambda _:(200,{"data":[{"id":"model-z"},{"id":"model-a"}]},{})) as (url,requests):
            models = ArenaAdapter("ARENA-SECRET", url).list_models()
            self.assertEqual(models, ["model-a", "model-z"])
            self.assertEqual(requests[0]["path"], "/models")
            self.assertEqual(requests[0]["headers"]["Authorization"], "Bearer ARENA-SECRET")
            self.assertEqual(requests[0]["body"], b"")

    def test_unknown_usage_is_not_zero_and_invalid_usage_is_rejected(self):
        responses=[{**OPENAI,'usage':None},{**ANTHROPIC,'usage':None},{k:v for k,v in GOOGLE.items() if k!='usageMetadata'}, {**BEDROCK,'usage':None},{k:v for k,v in OLLAMA.items() if k not in {'prompt_eval_count','eval_count'}}]
        for cls,data in zip([OpenAIAdapter,AnthropicAdapter,GoogleAdapter,BedrockAdapter,OllamaAdapter],responses):
            with self.subTest(provider=cls.name):
                a=cls(); self.assertEqual(a._parse(data,'test').usage,{})
        with endpoint(lambda _:(200,{**OPENAI,'usage':{'prompt_tokens':-1,'completion_tokens':True}},{})) as (url,_):
            with self.assertRaises(ProviderError) as error:OpenAIAdapter(base_url=url).chat(REQ)
            self.assertEqual(error.exception.code,'invalid_response')

    def test_structured_errors_ignore_every_shape_of_upstream_body(self):
        for body in ['<html>SECRET</html>','{"error":"SECRET"}','[]','{"error":{"message":"SECRET"}}']:
            for code,error_type in [(401,AuthenticationError),(403,AuthenticationError),(404,ModelNotFoundError),(429,RateLimitError),(503,ProviderError)]:
                error=map_http_error('google',code,body,{'Retry-After':'12'})
                self.assertIsInstance(error,error_type);self.assertNotIn('SECRET',str(error));self.assertIsNotNone(error.code)
                if code==429:self.assertEqual(error.retry_after,12)

    def test_redirect_bad_json_duplicate_keys_oversize_and_incomplete_ollama(self):
        cases=[(302,{}, {'Location':'https://evil.example'},'redirect_refused'),(200,b'[]',{},'invalid_response'),(200,b'{"choices":[],"choices":[]}',{},'invalid_response'),(200,b'x'*2000001,{},'response_too_large')]
        for status,body,headers,code in cases:
            with endpoint(lambda _:(status,body,headers)) as (url,requests):
                with self.assertRaises(ProviderError) as error:OpenAIAdapter(base_url=url).chat(REQ)
                self.assertEqual(error.exception.code,code);self.assertEqual(len(requests),1)
        with endpoint(lambda _:(200,{**OLLAMA,'done':False},{})) as (url,_):
            with self.assertRaises(ProviderError): OllamaAdapter(url).chat(REQ)

    def test_native_options_cannot_override_routing_or_budget(self):
        for adapter in adapters('http://localhost:1234'):
            for extra in [{'model':'other'},{'messages':[]},{'max_tokens':9999},{'options':{'num_predict':9999}},{'generationConfig':{'maxOutputTokens':9999}}]:
                with self.subTest(provider=adapter.name,extra=extra),self.assertRaises(ProviderError):
                    adapter.wire_bytes(ChatRequest('test',REQ.messages,max_tokens=77,extra=extra))

    def test_sync_and_async_streams_retain_text_usage_and_multiple_tool_calls(self):
        events=sse({'choices':[{'delta':{'content':'a','tool_calls':[{'index':0,'id':'one','function':{'name':'alpha','arguments':'{"a":'}},{'index':1,'id':'two','function':{'name':'beta','arguments':'{}'}}]}}]},
                   {'choices':[{'delta':{'tool_calls':[{'index':0,'function':{'arguments':'1}'}}]},'finish_reason':'tool_calls'}]},
                   {'choices':[],'usage':{'prompt_tokens':11,'completion_tokens':7}},'[DONE]')
        for cls in (OpenAIAdapter,AzureAdapter):
            with endpoint(lambda _:(200,events,{})) as (url,_):
                a=cls(base_url=url) if cls is OpenAIAdapter else cls(endpoint=url)
                sync=list(a.stream(REQ))
                async def read(): return [chunk async for chunk in a.astream(REQ)]
                self.assertEqual(asyncio.run(read()),sync)
                calls=[c.tool_call for c in sync if c.tool_call];self.assertEqual(len(calls),2)
                self.assertEqual(json.loads(calls[0].arguments),{'a':1});self.assertEqual(sync[-1].usage['completion_tokens'],7)

    def test_anthropic_google_ollama_stream_usage_and_finish(self):
        streams=[sse({'type':'message_start','message':{'usage':{'input_tokens':11}}}, {'type':'content_block_delta','index':0,'delta':{'type':'text_delta','text':'ok'}},{'type':'message_delta','delta':{'stop_reason':'max_tokens'},'usage':{'output_tokens':7}},{'type':'message_stop'}),sse(GOOGLE),encode(OLLAMA)+b'\n']
        for cls,body in zip([AnthropicAdapter,GoogleAdapter,OllamaAdapter],streams):
            with endpoint(lambda _:(200,body,{})) as (url,_):
                a=cls(base_url=url);chunks=list(a.stream(REQ))
                self.assertEqual(''.join(c.content or '' for c in chunks),'ok')
                self.assertEqual(chunks[-1].usage['prompt_tokens'],11);self.assertEqual(chunks[-1].usage['completion_tokens'],7)
                if cls is AnthropicAdapter:self.assertEqual(chunks[-1].finish_reason,'length')
                async def read():return [c async for c in a.astream(REQ)]
                self.assertEqual(asyncio.run(read()),chunks)

    def test_bedrock_async_chat_works_and_streaming_fails_explicitly(self):
        with endpoint(lambda _:(200,BEDROCK,{})) as (url,_):
            a=BedrockAdapter('ACCESS','SECRET',base_url=url)
            self.assertEqual(asyncio.run(a.achat(REQ)).content,'ok')
            with self.assertRaises(ProviderError) as error:list(a.stream(REQ))
            self.assertEqual(error.exception.code,'not_implemented')
            async def read(): return [c async for c in a.astream(REQ)]
            with self.assertRaises(ProviderError):asyncio.run(read())

    def test_tools_roundtrip_and_gemini_signatures_are_preserved(self):
        call=ToolCall('id','lookup','{"x":1}')
        req=ChatRequest('test',(Message(Role.USER,'Find'),Message(Role.ASSISTANT,'',tool_calls=(call,)),Message(Role.TOOL,'answer',name='lookup',tool_call_id='id')),tools=(ToolSpec('lookup','Lookup',{'type':'object'}),))
        for a in adapters('http://localhost:1234'):
            body=a.wire_bytes(req).decode();self.assertIn('lookup',body);self.assertIn('answer',body)
        data={'candidates':[{'content':{'parts':[{'functionCall':{'id':'x','name':'lookup','args':{}},'thoughtSignature':'opaque'}]},'finishReason':'STOP'}]}
        a=GoogleAdapter();resp=a._parse(data,'test')
        body=a._build_body(ChatRequest('test',(Message(Role.USER,'Find'),resp.as_message())))
        self.assertEqual(body['contents'][1]['parts'][0]['thoughtSignature'],'opaque')
        o=OllamaAdapter()._parse({**OLLAMA,'message':{'tool_calls':[{'function':{'name':'lookup','arguments':{'x':1}}}]}},'test')
        self.assertEqual(json.loads(o.tool_calls[0].arguments),{'x':1})

    def test_provider_names_roles_and_models_are_closed(self):
        with self.assertRaises(ValueError): Message('hacker','x')
        with self.assertRaises(ValueError): Registry().register('random',lambda:None)
        with self.assertRaises(ProviderError): ModelRef.parse('random:model')
        self.assertEqual(ModelRef.parse('ollama:llama3.3:70b').model,'llama3.3:70b')
        for cls in (OpenAIAdapter,GoogleAdapter,OllamaAdapter):
            with self.assertRaises(ProviderError):cls(base_url='http://remote.example')

    def test_bedrock_sigv4_matches_botocore_reference_vector(self):
        from datetime import datetime,timezone
        from urllib.parse import urlsplit
        a=BedrockAdapter('AKIDEXAMPLE','secret-example',session_token='session-example')
        url=a._url('arn:aws:bedrock:us-east-1:123456789012:inference-profile/test:0')
        with patch('ai_providers.adapters.bedrock_adapter.datetime') as clock:
            clock.now.return_value=datetime(2026,9,13,12,0,0,tzinfo=timezone.utc)
            h=a._sign('POST',urlsplit(url).path,'',{'Content-Type':'application/json'},b'{"messages":[]}')
        # Generated independently with AWS botocore SigV4Auth, same input and date.
        self.assertTrue(h['Authorization'].endswith('Signature=a7f7a4399c9c658f1a1d57807d487550c2b4e56d269e03efa1ac72534cfddeae'))
        self.assertIn('%3A',url)

    def test_bedrock_cache_reads_and_writes_are_included_in_input_usage(self):
        data={**BEDROCK,'usage':{'inputTokens':5,'outputTokens':7,'cacheReadInputTokens':1000,'cacheWriteInputTokens':2000}}
        usage=BedrockAdapter()._parse(data,'test').usage
        self.assertEqual(usage['prompt_tokens'],3005)
        self.assertEqual(usage['total_tokens'],3012)
        self.assertEqual(usage['cache_write_prompt_tokens'],2000)
        from residual.modular import normalized_usage
        from residual.providers import Prices
        self.assertIsNone(Prices(1,2).cost(normalized_usage(usage)))
