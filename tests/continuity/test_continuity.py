import json
import time
from collections import Counter
from dataclasses import asdict
from unittest.mock import patch

import pytest
from ai_providers import ChatRequest, ChatResponse, Message, Role, ProviderError
from ai_providers.adapters._http import map_http_error
from residual.continuity import Continuity, classification
from residual.continuity import admission
from residual.continuity.vendor import bl006
from residual.core import ContractError
from residual.modular import normalize_profile
from residual.station.store import Store


class Crash(BaseException):
    pass


def context(model):
    # Explicit synthetic inputs only in tests/fixture qualification.
    return {'manifest': asdict(bl006.create_manifest(model, 'test', 'fixture/1', 'fixture',
            100, 1, 8192, 10, footprint_class='MEASURED', kv_class='MEASURED')),
            'telemetry': asdict(bl006.create_telemetry(1000000, None, 0, 4)),
            'host_identity': 'fixture', 'requested_context_tokens': 8192, 'requested_max_tokens': 4096}


def profiles():
    return [normalize_profile({'route_id': r, 'kind': 'openai_compatible', 'model': r + '-model',
                               'base_url': 'http://127.0.0.1:8888/v1'}, 'remote')
            for r in ('primary-cloud', 'freellmapi')]


class Probe:
    def chat(self, request):
        return ChatResponse(request.model, '{"ready":true}')


@pytest.fixture
def harness(tmp_path):
    store = Store(tmp_path)
    journal = Continuity(store)
    routes = profiles()
    request = ChatRequest('primary-cloud-model', (Message(Role.USER, 'fixture'),), max_tokens=64)
    for profile in routes:
        journal.qualify(profile, context(profile['model']), Probe(), request, lambda r: None)
    calls = Counter()
    def invoke(profile, req):
        calls[profile['route_id']] += 1
        return ChatResponse(req.model, '{"ok":true}')
    args = dict(invocation_id='invocation-1', project_id='project', task_id='task', role='runner',
                profiles=routes, mode='AUTOMATIC_ELIGIBLE', request=request,
                invoke=invoke, authority=lambda: None, validate=lambda r: json.loads(r.content))
    return journal, args, calls


def failing(args, calls, code):
    original = args['invoke']
    def invoke(profile, req):
        if profile['route_id'] == 'primary-cloud':
            calls[profile['route_id']] += 1
            raise ProviderError(code=code)
        return original(profile, req)
    args['invoke'] = invoke


def receipts(journal):
    with journal.store.connect() as c:
        return [json.loads(row[0]) for row in c.execute('SELECT value FROM provider_decisions ORDER BY seq')]


def test_primary_success_never_calls_fallback(harness):
    journal, args, calls = harness
    journal.run(**args)
    assert calls == {'primary-cloud': 1}


@pytest.mark.parametrize('code', ['quota_exhausted', 'credit_exhausted', 'provider_unavailable'])
def test_exact_eligible_matrix(harness, code):
    journal, args, calls = harness
    failing(args, calls, code)
    journal.run(**args)
    assert calls == {'primary-cloud': 1, 'freellmapi': 1}
    last = receipts(journal)[-1]
    assert last['classification'] == code
    assert last['requested_route'] == 'primary-cloud'
    assert last['selected_route'] == 'freellmapi'
    assert last['placement'] == 'remote'
    assert last['readiness_receipt'] and last['admission_receipt']['receipt_digest']
    assert last['result_digest'] and last['provider_side_exactly_once'] is False


@pytest.mark.parametrize('code', ['invalid_response', 'authentication', 'model_not_found', 'content_filter',
    'rate_limit', 'invalid_request', 'config', 'response_too_large', 'redirect_refused'])
def test_negative_matrix(harness, code):
    journal, args, calls = harness
    failing(args, calls, code)
    with pytest.raises(ContractError):
        journal.run(**args)
    assert calls == {'primary-cloud': 1}
    assert receipts(journal)[-1]['classification'] == code


@pytest.mark.parametrize('historical', ['AUTH_EXPIRY', 'RATE_LIMIT_EXHAUSTED', 'PROVIDER_TIMEOUT',
                                       'PROVIDER_5XX', 'INVALID_REQUEST', 'VERIFIER_REJECTION'])
def test_historical_classes_are_not_policy_authority(historical):
    from residual.continuity import ELIGIBLE
    class Historical:
        code = historical
    assert classification(Historical()) not in ELIGIBLE


@pytest.mark.parametrize('mode', ['OFF', 'ASK'])
def test_policy_modes_do_not_automatically_failover(harness, mode):
    journal, args, calls = harness
    args['mode'] = mode
    failing(args, calls, 'quota_exhausted')
    with pytest.raises(ContractError): journal.run(**args)
    assert calls == {'primary-cloud': 1}


@pytest.mark.parametrize('state', ['NOT_CONFIGURED', 'CONFIGURED_NOT_VERIFIED', 'DEGRADED', 'UNAVAILABLE'])
def test_nonready_never_invoked(harness, state):
    journal, args, calls = harness
    failing(args, calls, 'quota_exhausted')
    with journal.store.transaction() as c:
        row = journal._get(c, 'provider_readiness', 'freellmapi')
        row['readiness_state'] = state
        journal._put(c, 'provider_readiness', 'freellmapi', row)
    with pytest.raises(ContractError, match='fallback_not_ready'): journal.run(**args)
    assert calls == {'primary-cloud': 1}


def test_authority_rescinded_before_call(harness):
    journal, args, calls = harness
    def deny(): raise ContractError('authority_rescinded')
    args['authority'] = deny
    with pytest.raises(ContractError): journal.run(**args)
    assert not calls


def test_authority_lost_between_attempts(harness):
    journal, args, calls = harness
    failing(args, calls, 'quota_exhausted')
    def authority():
        if calls: raise ContractError('authority_rescinded')
    args['authority'] = authority
    with pytest.raises(ContractError): journal.run(**args)
    assert calls == {'primary-cloud': 1}


@pytest.mark.parametrize('fallback', [False, True])
def test_f1_recorded_result_restart_and_duplicate_acceptance(harness, fallback):
    journal, args, calls = harness
    if fallback: failing(args, calls, 'credit_exhausted')
    def crash(stage):
        if stage == 'provider_result_recorded': raise Crash()
    with pytest.raises(Crash): journal.run(**args, hook=crash)
    before = dict(calls)
    restarted = Continuity(Store(journal.store.root))
    assert restarted.run(**args).content == '{"ok":true}'
    assert restarted.run(**args).content == '{"ok":true}'
    assert calls == before
    if fallback: assert calls['freellmapi'] == 1
    assert sum(r['event'] == 'accepted' for r in receipts(journal)) == 1


def test_indeterminate_external_call_escape_never_replays(harness):
    journal, args, calls = harness
    def crash(stage):
        if stage == 'before_result_persistence': raise Crash()
    with pytest.raises(Crash): journal.run(**args, hook=crash)
    restarted = Continuity(Store(journal.store.root))
    with pytest.raises(ContractError, match='INDETERMINATE_PROVIDER_OUTCOME'):
        restarted.run(**args)
    assert calls == {'primary-cloud': 1}
    assert receipts(journal)[-1]['terminal_outcome'] == 'INDETERMINATE_PROVIDER_OUTCOME'


def test_boundary_a_planned_is_safe_to_invoke(harness):
    journal, args, calls = harness
    def crash(stage):
        if stage == 'planned': raise Crash()
    with pytest.raises(Crash): journal.run(**args, hook=crash)
    assert not calls
    Continuity(Store(journal.store.root)).run(**args)
    assert calls == {'primary-cloud': 1}


@pytest.mark.parametrize('ready', [True, False])
def test_open_primary_breaker_selection(harness, ready):
    journal, args, calls = harness
    with journal.store.transaction() as c:
        journal._put(c, 'provider_breakers', 'primary-cloud',
                     {'state': 'OPEN', 'classification': 'provider_unavailable', 'probe': None})
        if not ready: c.execute('DELETE FROM provider_readiness WHERE route=?', ('freellmapi',))
    if ready:
        journal.run(**args)
        assert calls == {'freellmapi': 1}
    else:
        with pytest.raises(ContractError): journal.run(**args)
        assert not calls


def test_ready_does_not_replace_admission(harness):
    journal, args, calls = harness
    failing(args, calls, 'credit_exhausted')
    real = admission.consume
    def deny(store, profile, context, assignment, request=None):
        if profile['route_id'] == 'freellmapi': raise ContractError('admission_failure')
        return real(store, profile, context, assignment, request)
    with patch.object(admission, 'consume', side_effect=deny), pytest.raises(ContractError):
        journal.run(**args)
    assert calls == {'primary-cloud': 1}


def test_stale_or_changed_endpoint_readiness_not_admissible(harness):
    journal, args, calls = harness
    profile = args['profiles'][1]
    assert journal.readiness({**profile, 'base_url': 'http://127.0.0.1:9999/v1'})['readiness_state'] != 'READY'
    with patch('residual.continuity.time.time', return_value=time.time() + 61):
        assert journal.readiness(profile)['readiness_state'] == 'DEGRADED'


def test_receipts_exclude_response_metadata_and_content(harness):
    journal, args, calls = harness
    args['invoke'] = lambda p, r: ChatResponse(r.model, '{"secret":"DO-NOT-LOG"}',
                                             raw={'api_key': 'RAW-SECRET'}, metadata={'key': 'META-SECRET'})
    journal.run(**args)
    text = json.dumps(receipts(journal))
    for secret in ['DO-NOT-LOG', 'RAW-SECRET', 'META-SECRET']:
        assert secret not in text


def test_structured_output_failure_never_falls_back(harness):
    journal, args, calls = harness
    original = args['invoke']
    def malformed(p, r):
        original(p, r)
        return ChatResponse(r.model, 'not json')
    args['invoke'] = malformed
    with pytest.raises(ValueError): journal.run(**args)
    assert calls == {'primary-cloud': 1}


def test_quota_mapping_requires_explicit_code():
    assert map_http_error('openai_compatible', 429, b'{"error":{"code":"insufficient_quota"}}').code == 'quota_exhausted'
    assert map_http_error('openai_compatible', 402, b'{"error":{"code":"credit_exhausted"}}').code == 'credit_exhausted'
    assert map_http_error('openai_compatible', 429, b'{"error":"quota_exhausted secret"}').code == 'rate_limit'
    assert map_http_error('openai_compatible', 401, b'{"error":{"code":"insufficient_quota"}}').code == 'authentication'


def test_half_open_has_one_probe_and_closes_on_recorded_success(harness):
    journal, args, calls = harness
    with journal.store.transaction() as c:
        journal._put(c, 'provider_breakers', 'primary-cloud',
                     {'state': 'OPEN', 'classification': 'provider_unavailable', 'probe': None})
    journal.half_open(args['profiles'][0])
    journal.run(**args)
    assert calls == {'primary-cloud': 1}
    assert journal.breaker('primary-cloud')['state'] == 'CLOSED'
    assert any(r['breaker_state'] == 'HALF_OPEN' for r in receipts(journal))


def test_concurrent_resume_cannot_repeat_external_call(harness):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    journal, args, calls = harness
    entered, release = threading.Event(), threading.Event()
    original = args['invoke']
    def slow(profile, request):
        response = original(profile, request)
        entered.set()
        assert release.wait(5)
        return response
    args['invoke'] = slow
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(journal.run, **args)
        assert entered.wait(5)
        try:
            with pytest.raises(ContractError, match='INDETERMINATE_PROVIDER_OUTCOME'):
                Continuity(Store(journal.store.root)).run(**args)
        finally:
            release.set()
        assert first.result().content == '{"ok":true}'
    assert calls == {'primary-cloud': 1}
    assert sum(r['event'] == 'accepted' for r in receipts(journal)) == 1


def test_route_identity_credentials_are_isolated(tmp_path):
    from residual.station.models import save_settings, credentials_for, public_settings
    from residual.modular import make_adapter
    from ai_providers import Registry, Router
    store = Store(tmp_path)
    a, b = profiles()
    raw = lambda p: {k: v for k, v in p.items() if k != 'placement'}
    save_settings(store, {'cloud': raw(a), 'cloud_fallbacks': [raw(b)],
        'provider_credentials': {'primary-cloud': {'api_key': 'PRIMARY-SECRET'},
                                 'freellmapi': {'api_key': 'FALLBACK-SECRET'}}})
    settings = store.settings()
    registry = Registry()
    for p in (a, b):
        credentials = credentials_for(settings, p['kind'], credential_ref=p['credential_ref'])
        assert credentials['api_key'] == ('PRIMARY-SECRET' if p is a else 'FALLBACK-SECRET')
        adapter = make_adapter(p, credentials)
        registry.register_route(p['route_id'], p['kind'], lambda adapter=adapter: adapter)
    assert registry.get('primary-cloud') is not registry.get('freellmapi')
    assert 'SECRET' not in json.dumps(public_settings(store))
    with patch.dict('os.environ', {'LLM_API_KEY': 'AMBIENT-SECRET'}):
        assert 'Authorization' not in make_adapter(b, {})._headers()
    assert Router(registry, default_provider='primary-cloud').default_provider == 'primary-cloud'


def test_admission_warn_reject_and_route_context_mismatch_stop(harness):
    journal, args, calls = harness
    p = args['profiles'][1]
    for mutation in ['model', 'negative', 'warn', 'headroom', 'output']:
        ctx = context(p['model'])
        if mutation == 'model': ctx['manifest']['model_identity'] = 'different'
        if mutation == 'negative': ctx['manifest']['footprint_bytes'] = -100
        if mutation == 'warn': ctx['manifest']['footprint_class'] = 'CLAIMED'
        if mutation == 'headroom': ctx['telemetry']['available_ram_bytes'] = 0
        if mutation == 'output': ctx['requested_max_tokens'] = 1
        with pytest.raises(ContractError, match='admission_failure'):
            admission.consume(journal.store, p, ctx, 'assignment', args['request'])
    assert not calls


def test_result_reuse_bypasses_expired_readiness_and_admission_but_not_authority(harness):
    journal, args, calls = harness
    def crash(stage):
        if stage == 'provider_result_recorded': raise Crash()
    with pytest.raises(Crash): journal.run(**args, hook=crash)
    with journal.store.transaction() as c: c.execute('DELETE FROM provider_readiness')
    with patch.object(admission, 'consume', side_effect=AssertionError('must not readmit')):
        journal.run(**args)
    assert calls == {'primary-cloud': 1}


def test_failed_requalification_revokes_previous_ready(harness):
    journal, args, _ = harness
    class Down:
        def chat(self, req): raise ProviderError(code='provider_unavailable')
    route = args['profiles'][1]
    with pytest.raises(ProviderError):
        journal.qualify(route, context(route['model']), Down(), args['request'], lambda _: None)
    assert journal.readiness(route)['readiness_state'] != 'READY'
