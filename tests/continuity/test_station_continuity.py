import json
from collections import Counter
from unittest.mock import patch

import pytest
from ai_providers import ChatResponse, ProviderError
from residual.continuity import Continuity
from residual.core import ContractError
from residual.station.models import model_call, save_settings
from residual.station.store import Store
from tests.continuity.test_continuity import profiles, context, Probe, Crash, receipts
from residual.continuity.__main__ import probe_request


def setup(store):
    a, b = profiles()
    raw = lambda p: {k: v for k, v in p.items() if k != 'placement'}
    save_settings(store, {'cloud': raw(a), 'cloud_fallbacks': [raw(b)], 'fallback_mode': 'AUTOMATIC_ELIGIBLE'})
    for p in (a, b):
        Continuity(store).qualify(p, context(p['model']), Probe(), probe_request(p['model']), lambda _: None)


@pytest.mark.parametrize('fallback', [False, True])
def test_station_model_call_reuses_recorded_result_after_restart(tmp_path, fallback):
    store = Store(tmp_path)
    setup(store)
    calls = Counter()
    class Adapter:
        name = 'openai_compatible'
        def __init__(self, route): self.route = route
        def wire_bytes(self, req, stream=False): return b'fixture'
        def chat(self, req):
            calls[self.route] += 1
            if fallback and self.route == 'primary-cloud': raise ProviderError(code='quota_exhausted')
            return ChatResponse(req.model, '{"ok":true}')
    original = Continuity.run
    def crash(stage):
        if stage == 'provider_result_recorded': raise Crash()
    def cut(self, **kw): return original(self, **kw, hook=crash)
    def run(store):
        return model_call(store, None, 'fixture', {}, 'fixture', schema={'type': 'object'},
                          placement='cloud', invocation_id='stable-dispatch')
    with patch('residual.station.models.make_adapter', side_effect=lambda p, c: Adapter(p['route_id'])):
        with patch.object(Continuity, 'run', cut), pytest.raises(Crash): run(store)
        expected = dict(calls)
        assert run(Store(tmp_path)) == {'ok': True}
        assert run(Store(tmp_path)) == {'ok': True}
    assert calls == expected
    assert calls['freellmapi'] == int(fallback)
    assert sum(r['event'] == 'accepted' for r in receipts(Continuity(store))) == 1


def test_credentials_edit_invalidates_ready_receipt(tmp_path):
    store = Store(tmp_path)
    setup(store)
    journal = Continuity(store)
    route = profiles()[1]
    assert journal.readiness(route)['readiness_state'] == 'READY'
    save_settings(store, {'provider_credentials': {'freellmapi': {'api_key': 'ROTATED-SECRET'}}})
    assert journal.readiness(route)['readiness_state'] != 'READY'
    assert 'ROTATED-SECRET' not in json.dumps(journal.inspect(profiles(), 'AUTOMATIC_ELIGIBLE'))
