"""Joined native journal/mesh tests. All providers and readiness are synthetic."""
from collections import Counter
from unittest.mock import patch

import pytest
from ai_providers import ChatResponse, ProviderError
from ai_providers.adapters._http import map_http_error
from residual.continuity import Continuity
from residual.core import ContractError
from residual.station.mesh_continuity import mesh_model_call
from residual.station.service import Station, demo_spec
from residual.station.store import Store
from tests.continuity.test_station_continuity import setup
from tests.continuity.test_continuity import Crash
from tests.station.test_sc_mesh_001 import enrollment


@pytest.fixture
def joined(tmp_path):
    station = Station(tmp_path)
    store = station.store
    pid = station.create(demo_spec(), demo=True)['project_id']
    station.triage(pid)
    store.project_update(pid, allow_cloud=True)
    store.update_task(pid, 'OPS-101', route='cloud')
    setup(store)
    entry = station.mesh.enroll(enrollment(pid, capabilities=['model.remote', 'files.propose', 'evidence.submit']),
                               allowed_capabilities=store.settings()['mesh_allowed_capabilities'])
    worker = station.mesh.authenticate(entry['token'])
    station.mesh.snapshot(worker, pid)
    prepared = station.prepare(pid, 'mesh:claw-a', 'OPS-101', reserve_budget=True)
    task = prepared['task']
    work = dict(project_id=pid, task_id=task['id'], generation=1, attempt=task['attempt'],
                fencing_token=task['fencing_token'], lease_id=prepared['lease'],
                route='cloud', packet=prepared['packet'])
    calls = Counter()
    behavior = {'failure': None, 'after_primary': lambda: None}
    class Adapter:
        name = 'openai_compatible'
        def __init__(self, route): self.route = route
        def wire_bytes(self, req, stream=False): return b'fixture'
        def chat(self, req):
            calls[self.route] += 1
            if self.route == 'primary-cloud':
                behavior['after_primary']()
                if behavior['failure']: raise behavior['failure']
            return ChatResponse(req.model, '{"ok":true}', usage={'prompt_tokens': 1, 'completion_tokens': 1})
    def run(reopened=None, claimed=None):
        return mesh_model_call(reopened or store, worker, claimed or work, 'fixture', {'type': 'object'})
    with patch('residual.station.models.make_adapter', side_effect=lambda p, c: Adapter(p['route_id'])):
        yield station, work, calls, behavior, run


@pytest.mark.parametrize('status,body', [(429, '{"error":{"code":"insufficient_quota"}}'),
    (402, '{"error":{"code":"credit_exhausted"}}'), (503, '{}')])
def test_eligible_http_failure_uses_admitted_fallback(joined, status, body):
    station, work, calls, behavior, run = joined
    behavior['failure'] = map_http_error('fixture', status, body)
    assert run() == {'ok': True}
    assert calls == {'primary-cloud': 1, 'freellmapi': 1}
    p = station.store.project(work['project_id'])
    assert p['calls_reserved'] == 2
    assert p['mesh_assignments_reserved'] == 0
    assert run() == {'ok': True}
    assert calls == {'primary-cloud': 1, 'freellmapi': 1}
    assert station.store.project(work['project_id'])['calls_reserved'] == 2


@pytest.mark.parametrize('status,body', [(429, '{}'), (429, '[]'), (429, 'null'), (401, '{}'), (403, '{}'),
    (429, '{"error":{"code":["insufficient_quota"]}}'),
    (429, '{"error":{"type":"insufficient_quota"}}')])
def test_ineligible_http_failure_never_falls_back(joined, status, body):
    _, _, calls, behavior, run = joined
    behavior['failure'] = map_http_error('fixture', status, body)
    with pytest.raises(ContractError): run()
    assert calls == {'primary-cloud': 1}


@pytest.mark.parametrize('change', ['expiry', 'revoke', 'generation', 'fence', 'attempt', 'budget'])
def test_authority_and_budget_rechecked_between_attempts(joined, change):
    station, work, calls, behavior, run = joined
    store, pid, tid = station.store, work['project_id'], work['task_id']
    def mutate():
        if change == 'expiry': store.update_task(pid, tid, lease_until=0)
        elif change == 'revoke': station.mesh.revoke('claw-a')
        elif change == 'generation': store.advance_generation(pid, 'fixture')
        elif change == 'fence': store.update_task(pid, tid, fencing_token=work['fencing_token'] + 1)
        elif change == 'attempt': store.update_task(pid, tid, attempt=work['attempt'] + 1)
        else: store.project_update(pid, call_limit=1)
    behavior.update(failure=ProviderError(code='quota_exhausted'), after_primary=mutate)
    with pytest.raises(ContractError): run()
    assert calls == {'primary-cloud': 1}
    assert store.project(pid)['calls_reserved'] == 1


@pytest.mark.parametrize('stage', ['invocation_started', 'before_result_persistence', 'provider_result_recorded'])
@pytest.mark.parametrize('fallback', [False, True])
def test_interrupted_calls_and_recorded_recovery_do_not_repeat(joined, stage, fallback):
    station, work, calls, behavior, run = joined
    if fallback: behavior['failure'] = ProviderError(code='quota_exhausted')
    original = Continuity.run
    def crash(at):
        if at == stage and (not fallback or calls['primary-cloud'] == 1): raise Crash()
    def cut(self, **kw): return original(self, **kw, hook=crash)
    with patch.object(Continuity, 'run', cut), pytest.raises(Crash): run()
    counts = dict(calls)
    reopened = Store(station.store.root)
    if stage == 'provider_result_recorded':
        assert run(reopened) == {'ok': True}
        assert run(reopened) == {'ok': True}
    else:
        with pytest.raises(ContractError, match='INDETERMINATE_PROVIDER_OUTCOME'): run(reopened)
    assert calls == counts


def test_whole_plan_admission_cannot_be_double_charged(joined):
    station, work, calls, _, run = joined
    station.store.reserve_mesh_execution(work['project_id'], work['task_id'], work['lease_id'],
        work['fencing_token'], work['generation'],
        [{'placement': 'remote', 'model': 'fixture', 'request_bytes': 100}], attempt=work['attempt'])
    before = station.store.project(work['project_id'])
    with pytest.raises(ContractError, match='Whole-plan'): run()
    assert not calls
    assert station.store.project(work['project_id']) == before


def test_unbound_model_call_cannot_bypass_mesh_admission(joined):
    from residual.station.models import model_call
    station, work, calls, _, _ = joined
    with pytest.raises(ContractError, match='attempt-bound'):
        model_call(station.store, work['project_id'], 'runner', work['packet'],
                   'fixture', placement='cloud', tid=work['task_id'])
    assert not calls


@pytest.mark.parametrize('kind', ['not_ready', 'off', 'ask'])
def test_readiness_and_policy_are_required(joined, kind):
    from residual.station.models import save_settings
    station, work, calls, behavior, run = joined
    behavior['failure'] = ProviderError(code='quota_exhausted')
    if kind == 'not_ready':
        with station.store.transaction() as c:
            c.execute("DELETE FROM provider_readiness WHERE route='freellmapi'")
    else:
        save_settings(station.store, {'fallback_mode': kind.upper()})
    with pytest.raises(ContractError): run()
    assert calls == {'primary-cloud': 1}
