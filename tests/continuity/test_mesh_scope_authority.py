"""Current project membership governs replay of recorded provider evidence."""
import json
from unittest.mock import patch

import pytest
from ai_providers import ProviderError
from residual.continuity import Continuity
from residual.core import ContractError, canonical
from residual.station.mesh_continuity import mesh_model_call
from residual.station.store import Store
from tests.continuity.test_continuity import Crash
from tests.continuity.test_mesh_composition import joined


def _journal(store):
    with store.connect() as connection:
        invocations = [json.loads(row[0]) for row in connection.execute(
            'SELECT value FROM provider_invocations ORDER BY id')]
        decisions = [json.loads(row[0]) for row in connection.execute(
            'SELECT value FROM provider_decisions ORDER BY seq')]
    return invocations, decisions


def _persist(joined, state, fallback):
    station, work, calls, behavior, run = joined
    if fallback:
        behavior['failure'] = ProviderError(code='quota_exhausted')
    if state == 'recorded':
        original = Continuity.run
        def crash(stage):
            if stage == 'provider_result_recorded':
                raise Crash()
        def interrupted(self, **kwargs):
            return original(self, **kwargs, hook=crash)
        with patch.object(Continuity, 'run', interrupted), pytest.raises(Crash):
            run()
    else:
        assert run() == {'ok': True}
    invocations, _ = _journal(station.store)
    assert len(invocations) == 1
    assert invocations[0]['state'] == ('PROVIDER_RESULT_RECORDED' if state == 'recorded' else 'ACCEPTED')
    assert calls == ({'primary-cloud': 1, 'freellmapi': 1} if fallback else {'primary-cloud': 1})


@pytest.mark.parametrize('state', ['recorded', 'accepted'])
@pytest.mark.parametrize('fallback', [False, True])
@pytest.mark.parametrize('handle', ['cached', 'fresh'])
def test_removed_current_scope_denies_replay_without_io_or_charge(joined, state, fallback, handle):
    station, work, calls, _, run = joined
    _persist(joined, state, fallback)
    with station.store.transaction() as connection:
        worker = json.loads(connection.execute(
            "SELECT value FROM mesh_workers WHERE worker_id='claw-a'").fetchone()[0])
        worker['project_ids'] = []
        # Only this disposable fixture changes persisted enrollment scope.
        connection.execute("UPDATE mesh_workers SET value=? WHERE worker_id='claw-a'",
                           (canonical(worker),))
    reopened = Store(station.store.root)
    before_calls = dict(calls)
    before_project = reopened.project(work['project_id'])
    before_journal = _journal(reopened)
    with pytest.raises(ContractError, match='not authorized for this project'):
        if handle == 'cached':
            run(reopened)
        else:
            mesh_model_call(reopened, worker, work, 'fixture', {'type': 'object'})
    assert calls == before_calls
    assert reopened.project(work['project_id']) == before_project
    assert _journal(reopened) == before_journal


@pytest.mark.parametrize('state', ['recorded', 'accepted'])
@pytest.mark.parametrize('fallback', [False, True])
def test_unchanged_scope_reuses_result_without_io_or_double_charge(joined, state, fallback):
    station, work, calls, _, run = joined
    _persist(joined, state, fallback)
    reopened = Store(station.store.root)
    before_calls = dict(calls)
    before_project = reopened.project(work['project_id'])
    assert run(reopened) == {'ok': True}
    assert run(reopened) == {'ok': True}
    assert calls == before_calls
    assert reopened.project(work['project_id']) == before_project
    invocations, decisions = _journal(reopened)
    assert invocations[0]['state'] == 'ACCEPTED'
    assert sum(row['event'] == 'accepted' for row in decisions) == 1


def test_current_membership_cannot_expand_supplied_handle_scope(joined):
    station, work, _, _, _ = joined
    with station.store.connect() as connection:
        current = json.loads(connection.execute(
            "SELECT value FROM mesh_workers WHERE worker_id='claw-a'").fetchone()[0])
    assert work['project_id'] in current['project_ids']
    restricted = {**current, 'project_ids': []}
    with pytest.raises(ContractError, match='not authorized for this project'):
        station.mesh.authorize(restricted, work['project_id'])
