"""Offline FCC wire, failover, policy and accounting contracts. No real quota."""
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
from ai_providers.adapters.free_claude_code_adapter import FreeClaudeCodeAdapter, validate_fcc_config
from ai_providers.adapters.openai_adapter import OpenAIAdapter
from observation_layer import ObservationBus, verify_chain
from observation_layer.sinks import InMemorySink
from residual.core import ContractError, canonical
from residual.modular import ModularProvider, normalize_profile
from residual.station.models import model_call, public_settings, save_settings
from residual.station.service import Station, demo_spec, DEMO_FILES
from tests.modular.test_adapters import endpoint, REQ, OPENAI, ANTHROPIC, OLLAMA

MODEL = 'groq/test'
FCC = {**ANTHROPIC, 'model': MODEL, 'type': 'message', 'role': 'assistant'}
REQUEST = replace(REQ, model=MODEL)


def profile(url):
    return {'kind': 'free_claude_code', 'model': MODEL, 'base_url': url,
            'gateway_allowed_routes': [MODEL], 'fcc_standby_confirmed': True}


def adapter(url, **kw):
    return FreeClaudeCodeAdapter('FCC-PROXY-SECRET', url, [MODEL], True, **kw)


def router(primary, standby, receipts=None, bus=None):
    reg = Registry()
    reg.register('openai', lambda: primary)
    reg.register('free_claude_code', lambda: standby)
    return Router(registry=reg, after_attempt=receipts.append if receipts is not None else None, observation_bus=bus)


class FCCAdapterTests(unittest.TestCase):
    def test_wire_and_receipt_do_not_misrepresent_model_echo_or_total_usage(self):
        data = copy.deepcopy(FCC)
        data['content'].append({'type': 'thinking', 'thinking': 'PRIVATE-THINKING'})
        data['metadata'] = {'gateway': {'actual_provider': 'forged', 'secret': 'DO-NOT-LOG'}}
        with endpoint(lambda _: (200, data, {})) as (url, calls):
            result = adapter(url).chat(REQUEST)
        self.assertEqual(calls[0]['path'], '/v1/messages')
        self.assertEqual(calls[0]['headers']['Authorization'], 'Bearer FCC-PROXY-SECRET')
        self.assertNotIn('X-Api-Key', calls[0]['headers'])
        self.assertEqual(calls[0]['headers']['Cache-Control'], 'no-store')
        body = json.loads(calls[0]['body'])
        self.assertFalse(body['stream']); self.assertEqual(body['model'], MODEL)
        self.assertEqual(body['max_tokens'], 77)
        self.assertEqual(result.content, 'ok'); self.assertEqual(result.usage, {})
        self.assertIsNone(result.raw)
        report = result.metadata['gateway']; unsigned = dict(report)
        digest = unsigned.pop('receipt_sha256')
        self.assertEqual(digest, hashlib.sha256(b'residual.gateway-report.v1\n' + encode(unsigned)).hexdigest())
        self.assertEqual(report['request_sha256'], hashlib.sha256(calls[0]['body']).hexdigest())
        self.assertEqual(report['response_sha256'], hashlib.sha256(encode(data)).hexdigest())
        for key in ('actual_provider', 'actual_model', 'upstream_attempts_reported', 'usage_estimated'):
            self.assertIsNone(report[key])
        self.assertFalse(report['accounting_complete']); self.assertFalse(report['transformations_verified'])
        self.assertEqual(report['reserved_attempts'], 5)
        self.assertEqual(report['reported_usage']['prompt_tokens'], 11)
        self.assertNotIn('PRIVATE', canonical(report)); self.assertNotIn('DO-NOT-LOG', canonical(report))

    def test_explicit_standby_and_direct_route_validation(self):
        for routes, confirmed in [([], True), ([MODEL], False), ([MODEL], 1), ([MODEL], 'true'),
                                   ([MODEL, MODEL], True), (['claude-opus'], True),
                                   (['openai_codex/gpt'], True), (['unknown/test'], True),
                                   (['groq/test\n'], True), (['groq/'], True)]:
            with self.subTest(routes=routes, confirmed=confirmed), self.assertRaises(ProviderError):
                validate_fcc_config(routes, confirmed)
        self.assertEqual(validate_fcc_config(['llamacpp/model', 'lmstudio/model'], True), ('llamacpp/model', 'lmstudio/model'))

    def test_endpoint_key_and_timeout_validation(self):
        for changes in [{'api_key': ''}, {'api_key': 'freecc'}, {'api_key': 'x\ny'}, {'api_key': 'clé'},
                        {'base_url': 'http://remote.example'}, {'base_url': 'https://user:pass@example.com'},
                        {'base_url': 'https://example.com?key=x'}, {'base_url': 'http://127.0.0.1:8082/v1'},
                        {'timeout': 0}, {'timeout': 61}, {'timeout': float('nan')}, {'timeout': True}]:
            with self.subTest(changes=changes), self.assertRaises(ProviderError):
                FreeClaudeCodeAdapter(**{'api_key': 'KEY', 'allowed_routes': [MODEL], 'standby_confirmed': True, **changes})

    def test_unsupported_requests_do_not_dispatch(self):
        invalid = [replace(REQUEST, model='claude-opus'), replace(REQUEST, model='groq/other'),
                   replace(REQUEST, max_tokens=None), replace(REQUEST, max_tokens=16001),
                   replace(REQUEST, seed=1), replace(REQUEST, extra={'reasoning_effort': 'high'}),
                   replace(REQUEST, tools=(ToolSpec('run', 'run', {}),)),
                   replace(REQUEST, messages=(Message(Role.TOOL, 'result', tool_call_id='1'),)),
                   replace(REQUEST, messages=(Message(Role.ASSISTANT, '', tool_calls=(ToolCall('1', 'run', '{}'),)),))]
        with endpoint(lambda _: (200, FCC, {})) as (url, calls):
            a = adapter(url)
            for req in invalid:
                with self.assertRaises(ProviderError): a.chat(req)
            with self.assertRaises(ProviderError): list(a.stream(REQUEST))
            async def stream(): return [c async for c in a.astream(REQUEST)]
            with self.assertRaises(ProviderError): asyncio.run(stream())
            self.assertFalse(a.supports_tools(MODEL)); self.assertEqual(a.list_models(), [MODEL])
            self.assertEqual(calls, [])

    def test_invalid_response_tool_blocks_and_wrong_model_fail_closed(self):
        variants = [{'model': 'test'}, {'type': 'other'}, {'role': 'user'}, {'content': []},
                    {'content': [{'type': 'text', 'text': 12}]}, {'content': [{'type': 'text', 'text': ''}]},
                    {'content': [{'type': 'server_tool_use', 'name': 'web_fetch'}]},
                    {'content': [{'type': 'tool_use', 'id': '1', 'name': 'run', 'input': {}}]},
                    {'stop_reason': 'tool_use'}, {'stop_reason': 'refusal'}, {'error': 'SECRET'},
                    {'usage': {'input_tokens': -1}}, {'usage': {'output_tokens': True}}]
        for change in variants:
            with self.subTest(change=change), endpoint(lambda _: (200, {**FCC, **change}, {})) as (url, _):
                with self.assertRaises(ProviderError) as caught: adapter(url).chat(REQUEST)
                self.assertEqual(caught.exception.code, 'invalid_response')
                self.assertFalse(caught.exception.retryable)

    def test_duplicate_json_oversize_and_redirects(self):
        for status, body, headers, code in [(200, b'{"x":1,"x":2}', {}, 'invalid_response'),
                                           (200, b'x' * (MAX_RESPONSE + 1), {}, 'response_too_large'),
                                           (302, b'', {'Location': 'https://example.com'}, 'redirect_refused')]:
            with endpoint(lambda _: (status, body, headers)) as (url, calls):
                with self.assertRaises(ProviderError) as caught: adapter(url).chat(REQUEST)
                self.assertEqual(caught.exception.code, code); self.assertEqual(len(calls), 1)

    def test_shared_concurrency_cap_and_cleanup(self):
        release = threading.Event(); entered = threading.Event(); count = []; lock = threading.Lock()
        def respond(_):
            with lock:
                count.append(1)
                if len(count) == 2: entered.set()
            release.wait(3)
            return 200, FCC, {}
        with endpoint(respond) as (url, calls), ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(adapter(url).chat, REQUEST) for _ in range(2)]
            try:
                self.assertTrue(entered.wait(2))
                with self.assertRaises(ProviderError) as caught: adapter(url).chat(REQUEST)
                self.assertEqual(caught.exception.code, 'rate_limit'); self.assertEqual(len(calls), 2)
            finally: release.set()
            for future in futures: self.assertEqual(future.result().content, 'ok')
            self.assertEqual(adapter(url).chat(REQUEST).content, 'ok')

    def test_http_errors_are_redacted_and_not_retried_by_adapter(self):
        for status in (401, 403, 404, 429, 500, 503, 504):
            with self.subTest(status=status), endpoint(lambda _: (status, {'error': 'PROVIDER-SECRET'}, {})) as (url, calls):
                with self.assertRaises(ProviderError) as caught: adapter(url).chat(REQUEST)
                self.assertEqual(len(calls), 1)
                self.assertEqual(caught.exception.retryable, status == 429 or status >= 500)
                self.assertNotIn('PROVIDER-SECRET', str(caught.exception))


class FCCRouterTests(unittest.TestCase):
    def test_availability_failover_is_correlated_and_primary_recovers(self):
        for status in (429, 500, 502, 503, 504):
            state = {'status': status}; receipts = []; sink = InMemorySink()
            with endpoint(lambda _: (state['status'], OPENAI, {})) as (one, primary_calls), endpoint(lambda _: (200, FCC, {})) as (two, standby_calls):
                r = router(OpenAIAdapter('PRIMARY-SECRET', one), adapter(two), receipts, ObservationBus(sink=sink))
                self.assertEqual(r.chat('openai:test', REQ, ['free_claude_code:' + MODEL]).content, 'ok')
                state['status'] = 200
                self.assertEqual(r.chat('openai:test', REQ, ['free_claude_code:' + MODEL]).content, 'ok')
                self.assertEqual(len(primary_calls), 2); self.assertEqual(len(standby_calls), 1)
                self.assertNotIn('PRIMARY-SECRET', repr(standby_calls)); self.assertNotIn('FCC-PROXY-SECRET', repr(primary_calls))
            self.assertEqual(receipts[0]['request_id'], receipts[1]['request_id'])
            self.assertNotEqual(receipts[1]['request_id'], receipts[2]['request_id'])
            self.assertEqual(receipts[1]['attempt'], 2)
            self.assertEqual(receipts[1]['fallback_trigger'], 'rate_limit' if status == 429 else 'server_error')
            self.assertTrue(verify_chain(sink.events))

    def test_connection_and_timeout_fail_over_once(self):
        for code in ('connection', 'timeout'):
            class Failed:
                name = 'openai'
                def chat(self, req): raise ProviderError(provider=self.name, code=code, retryable=True)
            with endpoint(lambda _: (200, FCC, {})) as (url, calls):
                self.assertEqual(router(Failed(), adapter(url)).chat('openai:test', REQ, ['free_claude_code:' + MODEL]).content, 'ok')
                self.assertEqual(len(calls), 1)

    def test_terminal_primary_errors_never_reach_standby(self):
        for status, body in [(400, {}), (401, {}), (403, {}), (404, {}), (200, {'bad': 'shape'})]:
            with endpoint(lambda _: (status, body, {})) as (one, _), endpoint(lambda _: (200, FCC, {})) as (two, calls):
                with self.assertRaises(ProviderError): router(OpenAIAdapter('KEY', one), adapter(two)).chat('openai:test', REQ, ['free_claude_code:' + MODEL])
                self.assertEqual(calls, [])

    def test_primary_or_nonavailability_retry_cannot_use_fcc(self):
        class WrongRetry:
            name = 'openai'
            def chat(self, req): raise ProviderError(provider=self.name, code='invalid_response', retryable=True)
        with endpoint(lambda _: (200, FCC, {})) as (url, calls):
            r = router(WrongRetry(), adapter(url))
            with self.assertRaises(ProviderError): r.chat('free_claude_code:' + MODEL, REQ)
            with self.assertRaises(ProviderError): r.chat('openai:test', REQ, ['free_claude_code:' + MODEL])
            self.assertEqual(calls, [])

    def test_unhealthy_standby_does_not_loop_and_later_direct_fallback_can_run(self):
        with endpoint(lambda _: (503, {}, {})) as (one, first), endpoint(lambda _: (503, {}, {})) as (two, second), endpoint(lambda _: (200, ANTHROPIC, {})) as (three, third):
            from ai_providers.adapters.anthropic_adapter import AnthropicAdapter
            r = router(OpenAIAdapter('KEY', one), adapter(two))
            r.registry.register('anthropic', lambda: AnthropicAdapter('THIRD-KEY', three))
            self.assertEqual(r.chat('openai:test', REQ, ['free_claude_code:' + MODEL, 'anthropic:test']).content, 'ok')
            self.assertEqual([len(first), len(second), len(third)], [1, 1, 1])

    def test_timeout_is_bounded_and_releases_slot(self):
        def slow(_):
            time.sleep(.08)
            return 200, FCC, {}
        with endpoint(slow) as (url, _):
            a = adapter(url, timeout=.01)
            with self.assertRaises(ProviderError) as caught: a.chat(REQUEST)
            self.assertEqual(caught.exception.code, 'timeout')
            a.timeout = 1
            self.assertEqual(a.chat(REQUEST).content, 'ok')


class FCCStationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.s = Station(self.tmp.name)
        self.pid = self.s.create(demo_spec(), demo=True, allow_cloud=True)['project_id']
    def tearDown(self): self.tmp.cleanup()
    def configure(self, primary, standby, key=True):
        save_settings(self.s.store, {'cloud': {'kind': 'openai', 'model': 'test', 'base_url': primary},
            'cloud_fallbacks': [profile(standby)], 'provider_credentials': {
                'openai': {'api_key': 'PRIMARY-SECRET'}, 'free_claude_code': {'api_key': 'FCC-PROXY-SECRET'} if key else {'clear': True}}})
    def call(self, **kw):
        return model_call(self.s.store, self.pid, 'runner', {}, 'system', placement='cloud', **kw)

    def test_settings_optin_redaction_and_fallback_only(self):
        self.configure('https://primary.example/v1', 'http://127.0.0.1:8082')
        public = public_settings(self.s.store)
        self.assertTrue(public['cloud_fallbacks'][0]['fcc_standby_confirmed'])
        self.assertNotIn('SECRET', canonical(public))
        for data in [{'cloud': profile('http://127.0.0.1:8082')}, {'local': profile('http://127.0.0.1:8082')},
                     {'cloud_fallbacks': [{**profile('http://127.0.0.1:8082'), 'fcc_standby_confirmed': False}]},
                     {'cloud_fallbacks': [profile('http://127.0.0.1:8082')] * 2}]:
            with self.assertRaises(ContractError): save_settings(self.s.store, data)
        with self.assertRaises(ContractError): normalize_profile({'kind': 'ollama', 'model': 'test', 'fcc_standby_confirmed': True}, 'local')
        with self.assertRaises(ContractError): ModularProvider({**profile('http://127.0.0.1:8082'), 'placement': 'remote'})

    def test_missing_standby_key_cannot_poison_healthy_primary(self):
        with patch.dict('os.environ', {}, clear=True), endpoint(lambda _: (200, OPENAI, {})) as (one, calls):
            self.configure(one, 'http://127.0.0.1:1', key=False)
            self.assertEqual(self.call()['text'], 'ok'); self.assertEqual(len(calls), 1)

    def test_missing_key_fails_closed_when_standby_is_needed(self):
        with patch.dict('os.environ', {}, clear=True), endpoint(lambda _: (503, {}, {})) as (one, _), endpoint(lambda _: (200, FCC, {})) as (two, calls):
            self.configure(one, two, key=False)
            with self.assertRaises(ProviderError) as caught: self.call()
            self.assertEqual(caught.exception.code, 'config'); self.assertEqual(calls, [])

    def test_correlated_receipts_reservations_and_unknown_cost_metrics(self):
        with endpoint(lambda _: (503, {}, {})) as (one, _), endpoint(lambda _: (200, FCC, {})) as (two, _):
            self.configure(one, two); self.assertEqual(self.call()['text'], 'ok')
        self.assertEqual(self.s.store.project(self.pid)['calls_reserved'], 6)
        events = [e['data'] for e in self.s.store.events(self.pid) if e['event_type'] == 'usage.recorded']
        self.assertEqual(events[0]['request_id'], events[1]['request_id'])
        self.assertEqual(events[1]['fallback_trigger'], 'server_error')
        self.assertEqual(events[1]['source'], 'unavailable')
        self.assertNotIn('SECRET', canonical(events))
        metrics = self.s.metrics(self.pid)
        self.assertEqual(metrics['continuity_fallback_calls'], 1)
        self.assertEqual(metrics['gateway_attempts_unknown'], 1)
        self.assertEqual(metrics['gateway_upstream_attempts_reported'], 0)
        self.assertEqual(metrics['gateway_accounting_incomplete'], 1)

    def test_project_sharing_and_review_gates_survive_failover(self):
        with endpoint(lambda _: (503, {}, {})) as (one, first), endpoint(lambda _: (200, FCC, {})) as (two, second):
            self.configure(one, two)
            pid = self.s.create(demo_spec(), demo=True)['project_id']
            with self.assertRaisesRegex(ContractError, 'disabled'):
                model_call(self.s.store, pid, 'runner', {}, 's', placement='cloud')
            self.assertEqual(first, []); self.assertEqual(second, [])
            with self.assertRaisesRegex(ContractError, 'approval review'):
                model_call(self.s.store, self.pid, 'reviewer', {}, 's', placement='cloud')
            self.assertEqual(len(first), 1); self.assertEqual(second, [])

    def test_budget_is_reserved_before_standby_dispatch(self):
        with self.s.store.transaction() as c:
            p = self.s.store._project(c, self.pid); p['cloud_call_limit'] = 5
            c.execute('UPDATE projects SET value=? WHERE id=?', (canonical(p), self.pid))
        with endpoint(lambda _: (503, {}, {})) as (one, first), endpoint(lambda _: (200, FCC, {})) as (two, second):
            self.configure(one, two)
            with self.assertRaises(ContractError): self.call()
            self.assertEqual(len(first), 1); self.assertEqual(second, [])

    def test_default_registry_is_optin(self):
        from ai_providers.registry import _default_registry
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ProviderError): _default_registry().get('free_claude_code')
        with patch.dict('os.environ', {'FCC_PROXY_API_KEY': 'KEY', 'FCC_ALLOWED_ROUTES': MODEL, 'FCC_STANDBY_CONFIRMED': '1'}):
            self.assertEqual(_default_registry().get('free_claude_code').list_models(), [MODEL])

    def test_freellmapi_primary_outage_uses_fcc_with_combined_reservation(self):
        from tests.modular.test_freellmapi import profile as free_profile
        with endpoint(lambda _: (503, {}, {})) as (one, first), endpoint(lambda _: (200, FCC, {})) as (two, second):
            save_settings(self.s.store, {'cloud': free_profile(one), 'cloud_fallbacks': [profile(two)],
                'provider_credentials': {'freellmapi': {'api_key': 'FREE-PRIMARY-SECRET'},
                                         'free_claude_code': {'api_key': 'FCC-PROXY-SECRET'}}})
            self.assertEqual(self.call()['text'], 'ok')
            self.assertEqual(len(first), 1); self.assertEqual(len(second), 1)
            self.assertEqual(self.s.store.project(self.pid)['calls_reserved'], 25)
            self.assertNotIn('FREE-PRIMARY-SECRET', repr(second))
            self.assertNotIn('FCC-PROXY-SECRET', repr(first))
        self.assertEqual(self.s.metrics(self.pid)['gateway_accounting_incomplete'], 2)

    def test_freellmapi_provenance_failure_cannot_be_bypassed_by_fcc(self):
        from tests.modular.test_freellmapi import profile as free_profile
        with endpoint(lambda _: (200, OPENAI, {})) as (one, _), endpoint(lambda _: (200, FCC, {})) as (two, second):
            save_settings(self.s.store, {'cloud': free_profile(one), 'cloud_fallbacks': [profile(two)],
                'provider_credentials': {'freellmapi': {'api_key': 'FREE-PRIMARY-SECRET'},
                                         'free_claude_code': {'api_key': 'FCC-PROXY-SECRET'}}})
            with self.assertRaises(ProviderError) as caught: self.call()
            self.assertEqual(caught.exception.code, 'invalid_response')
            self.assertEqual(second, [])

    def test_fallback_proposals_still_need_checks_and_independent_review(self):
        self.s.triage(self.pid)
        with self.s.store.transaction() as c:
            p = self.s.store._project(c, self.pid); p['mode'] = 'live'
            c.execute('UPDATE projects SET value=? WHERE id=?', (canonical(p), self.pid))
        self.s.store.update_task(self.pid, 'OPS-101', route='cloud')
        candidate = copy.deepcopy(FCC); candidate['content'][0]['text'] = canonical({'files': DEMO_FILES['OPS-101']})
        reviewer = copy.deepcopy(OLLAMA); reviewer['message']['content'] = canonical({'approved': True, 'findings': []})
        with endpoint(lambda _: (503, {}, {})) as (one, _), endpoint(lambda _: (200, candidate, {})) as (two, calls), endpoint(lambda _: (200, reviewer, {})) as (local, reviews):
            self.configure(one, two)
            save_settings(self.s.store, {'local': {'kind': 'ollama', 'model': 'test', 'base_url': local}})
            self.s.run_one(self.pid, 'OPS-101')
            self.assertEqual(self.s.store.task(self.pid, 'OPS-101')['state'], 'review_ready')
            self.s.review(self.pid, 'OPS-101'); self.s.integrate(self.pid, 'OPS-101')
            self.assertEqual(self.s.store.task(self.pid, 'OPS-101')['state'], 'integrated')
            self.assertEqual(len(calls), 1); self.assertEqual(len(reviews), 1)

    def test_unknown_fallback_usage_stops_next_batch_wave(self):
        from residual.station.control import run_controlled_batch
        self.s.triage(self.pid)
        with self.s.store.transaction() as c:
            p = self.s.store._project(c, self.pid); p.update(mode='live', cloud_call_limit=100)
            c.execute('UPDATE projects SET value=? WHERE id=?', (canonical(p), self.pid))
        for tid in DEMO_FILES: self.s.store.update_task(self.pid, tid, route='cloud')
        seen = []
        def generate(request):
            body = json.loads(request['body'])
            packet = json.loads(body['messages'][-1]['content'][0]['text'])
            tid = packet['task_id']; seen.append(tid)
            if tid == 'OPS-101': time.sleep(.03)
            data = copy.deepcopy(FCC); data['content'][0]['text'] = canonical({'files': DEMO_FILES[tid]})
            return 200, data, {}
        reviewer = copy.deepcopy(OLLAMA); reviewer['message']['content'] = canonical({'approved': True, 'findings': []})
        with endpoint(lambda _: (503, {}, {})) as (one, _), endpoint(generate) as (two, _), endpoint(lambda _: (200, reviewer, {})) as (local, _):
            self.configure(one, two)
            save_settings(self.s.store, {'local': {'kind': 'ollama', 'model': 'test', 'base_url': local}, 'workers': 2})
            with patch.object(self.s, 'triage', return_value=None):
                result = run_controlled_batch(self.s, self.pid, lambda *a: None)
        self.assertCountEqual(seen, ['OPS-101', 'OPS-102'])
        self.assertEqual(result['integrated'], 2)
        self.assertEqual(result['control']['outcome'], 'aborted')
        self.assertIn('usage_unknown_or_invalid', result['control']['trip_reasons'])
        self.assertIsNone(result['control']['tokens'])
        self.assertNotEqual(self.s.store.task(self.pid, 'OPS-103')['state'], 'integrated')

    def test_concurrent_budget_reservations_allow_only_one_standby(self):
        with self.s.store.transaction() as c:
            p = self.s.store._project(c, self.pid); p['cloud_call_limit'] = 7
            c.execute('UPDATE projects SET value=? WHERE id=?', (canonical(p), self.pid))
        barrier = threading.Barrier(2)
        def unavailable(_):
            barrier.wait(3)
            return 503, {}, {}
        with endpoint(unavailable) as (one, first), endpoint(lambda _: (200, FCC, {})) as (two, second), ThreadPoolExecutor(max_workers=2) as pool:
            self.configure(one, two)
            futures = [pool.submit(self.call) for _ in range(2)]
            successes = 0
            for future in futures:
                try: future.result(); successes += 1
                except ContractError: pass
            self.assertEqual(successes, 1); self.assertEqual(len(first), 2); self.assertEqual(len(second), 1)
            self.assertEqual(self.s.store.project(self.pid)['calls_reserved'], 7)
