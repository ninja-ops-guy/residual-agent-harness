"""Durable, bounded provider continuity. Provider results remain evidence."""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from dataclasses import asdict, replace

from ai_providers import ChatResponse, ProviderError
from ai_providers.core import ToolCall
from residual.core import ContractError, canonical, digest
from . import admission

ELIGIBLE = frozenset({'quota_exhausted', 'credit_exhausted', 'provider_unavailable'})
MODES = frozenset({'OFF', 'ASK', 'AUTOMATIC_ELIGIBLE'})
READINESS = frozenset({'NOT_CONFIGURED', 'CONFIGURED_NOT_VERIFIED', 'READY', 'DEGRADED', 'UNAVAILABLE'})
SCHEMA = '''
CREATE TABLE IF NOT EXISTS provider_invocations(id TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS provider_readiness(route TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS provider_readiness_receipts(digest TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS provider_breakers(route TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS provider_breaker_events(seq INTEGER PRIMARY KEY AUTOINCREMENT,
    route TEXT NOT NULL, value TEXT NOT NULL, digest TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS provider_decisions(seq INTEGER PRIMARY KEY AUTOINCREMENT,
    invocation TEXT NOT NULL, value TEXT NOT NULL, digest TEXT NOT NULL);
'''


def identity(profile):
    return dict(profile)


def classification(error):
    # Raw adapter code is retained separately; retryable is never policy authority.
    return {'connection': 'provider_unavailable', 'timeout': 'provider_unavailable',
            'server_error': 'provider_unavailable'}.get(error.code, error.code)



def denial_class(error):
    message = str(error)
    if message in {'authority_rescinded', 'dispatch_expired', 'admission_failure', 'user_cancelled'}:
        return message
    if 'budget' in message or message == 'usage_unknown_or_invalid':
        return 'budget_exhaustion'
    return 'policy_denial'


def unpack(value):
    return ChatResponse(**{**value, 'tool_calls': tuple(ToolCall(**t) for t in value['tool_calls'])})


class Continuity:
    def __init__(self, store):
        self.store = store
        with store.connect() as c:
            c.executescript(SCHEMA)

    @staticmethod
    def _get(c, table, key, default=None):
        column = 'id' if table == 'provider_invocations' else 'route'
        row = c.execute(f'SELECT value FROM {table} WHERE {column}=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    @staticmethod
    def _put(c, table, key, value):
        c.execute(f'INSERT OR REPLACE INTO {table} VALUES (?,?)', (key, canonical(value)))

    def _breaker(self, c, route, value):
        prior = self._get(c, 'provider_breakers', route, {'state': 'CLOSED'})
        self._put(c, 'provider_breakers', route, value)
        event = {'route_id': route, 'from': prior['state'], **value}
        c.execute('INSERT INTO provider_breaker_events(route,value,digest) VALUES (?,?,?)',
                  (route, canonical(event), digest(event)))

    def _save(self, c, record, event):
        self._put(c, 'provider_invocations', record['invocation_id'], record)
        # Deliberate allowlist: response bodies, prompts, URLs, credentials and
        # exception messages cannot enter decision receipts.
        receipt = {k: record[k] for k in (
            'invocation_id', 'project_id', 'mission_id', 'task_id', 'role',
            'requested_route', 'selected_route', 'fallback_mode', 'classification',
            'raw_error_code', 'breaker_state', 'readiness_receipt', 'admission_receipt',
            'model_requested', 'model_observed', 'provider_observed', 'attempt_id',
            'placement', 'created_at', 'terminal_outcome', 'state', 'result_digest', 'provider_side_exactly_once')}
        receipt.update(event=event, timestamp=time.time(), fallback_eligible=record['classification'] in ELIGIBLE)
        c.execute('INSERT INTO provider_decisions(invocation,value,digest) VALUES (?,?,?)',
                  (record['invocation_id'], canonical(receipt), digest(receipt)))

    def readiness(self, profile):
        with self.store.connect() as c:
            row = self._get(c, 'provider_readiness', profile['route_id'])
        if not row or row['identity'] != identity(profile) or row['receipt_digest'] != digest({k: v for k, v in row.items() if k != 'receipt_digest'}):
            return {'readiness_state': 'CONFIGURED_NOT_VERIFIED', 'receipt_digest': None}
        if row['readiness_state'] == 'READY' and time.time() > row['expires_at']:
            return {**row, 'readiness_state': 'DEGRADED'}
        return row

    def qualify(self, profile, context, adapter, request, validate):
        """Explicit operator probe: BL-006 admission, full response validation, then READY.

        TCP/HTTP success alone is insufficient. Context is operator-supplied
        BL-006 manifest/telemetry, with actual collection time preserved.
        """
        try:
            admitted = admission.consume(self.store, profile, context, 'readiness:' + profile['route_id'], request)
            response = adapter.chat(replace(request, model=profile['model']))
            if not isinstance(response, ChatResponse):
                raise ContractError('malformed_response')
            validate(response)
        except Exception as error:
            row = {'identity': identity(profile), 'provider_kind': profile['kind'],
                   'readiness_state': 'UNAVAILABLE' if isinstance(error, ProviderError) else 'DEGRADED',
                   'verified_at': None, 'expires_at': time.time(), 'receipt_id': uuid.uuid4().hex,
                   'classification': classification(error) if isinstance(error, ProviderError) else 'admission_or_probe_failure'}
            row['receipt_digest'] = digest(row)
            with self.store.transaction() as c:
                self._put(c, 'provider_readiness', profile['route_id'], row)
                c.execute('INSERT INTO provider_readiness_receipts VALUES (?,?)', (row['receipt_digest'], canonical(row)))
            raise
        verified = time.time()
        row = {'identity': identity(profile), 'provider_kind': profile['kind'],
               'readiness_state': 'READY', 'verified_at': verified,
               'expires_at': min(verified + 60, datetime.fromisoformat(
                   context['telemetry']['collected_at'].replace('Z', '+00:00')).timestamp() + 60),
               'admission_receipt': admitted, 'context': context,
               'probe_digest': digest({'model': response.model, 'content': response.content,
                                       'finish_reason': response.finish_reason}),
               'receipt_id': uuid.uuid4().hex}
        row['receipt_digest'] = digest(row)
        with self.store.transaction() as c:
            self._put(c, 'provider_readiness', profile['route_id'], row)
            c.execute('INSERT INTO provider_readiness_receipts VALUES (?,?)', (row['receipt_digest'], canonical(row)))
        return {k: v for k, v in row.items() if k != 'context'}

    def breaker(self, route):
        with self.store.connect() as c:
            return self._get(c, 'provider_breakers', route,
                             {'state': 'CLOSED', 'classification': None, 'probe': None})

    def half_open(self, profile):
        """Explicit single-probe recovery; never a timer-driven retry loop."""
        ready = self.readiness(profile)
        if ready['readiness_state'] != 'READY':
            raise ContractError('fallback_not_ready')
        with self.store.transaction() as c:
            old = self._get(c, 'provider_breakers', profile['route_id'])
            if not old or old['state'] != 'OPEN':
                raise ContractError('breaker_not_open')
            self._breaker(c, profile['route_id'],
                      {**old, 'state': 'HALF_OPEN', 'probe': None,
                       'readiness_receipt': ready['receipt_digest'], 'changed_at': time.time()})

    def inspect(self, profiles, mode):
        with self.store.connect() as c:
            last = c.execute('SELECT value,digest FROM provider_decisions ORDER BY seq DESC LIMIT 1').fetchone()
        return {'primary_route': profiles[0]['route_id'] if profiles else None,
                'fallback_routes': [p['route_id'] for p in profiles[1:]], 'fallback_mode': mode,
                'routes': {p['route_id']: {'readiness': {k: v for k, v in self.readiness(p).items() if k != 'context'},
                                          'breaker': self.breaker(p['route_id'])} for p in profiles},
                'last_decision': {**json.loads(last[0]), 'receipt_digest': last[1]} if last else None}

    def run(self, *, invocation_id, project_id, task_id, role, profiles, mode, request,
            invoke, authority, validate, hook=lambda stage: None):
        """invoke(profile, request) must enforce budget and quarantine for each attempt.

        ACCEPTED means validated evidence delivered by this seam, never mission
        verification/integration. Those existing Station transitions stay separate.
        """
        if mode not in MODES or not profiles or len(profiles) > 4:
            raise ContractError('invalid_continuity_policy')
        binding = digest({'project': project_id, 'task': task_id, 'role': role,
                          'profiles': profiles, 'mode': mode, 'request': asdict(request)})
        with self.store.transaction() as c:
            record = self._get(c, 'provider_invocations', invocation_id)
            if record and record['binding'] != binding:
                raise ContractError('invocation_identity_mismatch')
            if not record:
                record = dict(invocation_id=invocation_id, binding=binding,
                              project_id=project_id, mission_id=project_id, task_id=task_id, role=role,
                              requested_route=profiles[0]['route_id'], selected_route=None,
                              fallback_mode=mode, classification=None, raw_error_code=None,
                              breaker_state=None, readiness_receipt=None, admission_receipt=None,
                              model_requested=profiles[0]['model'], model_observed=None,
                              provider_observed=None, attempt_id=None, placement=profiles[0]['placement'],
                              created_at=time.time(), terminal_outcome=None, state='PLANNED',
                              index=0, response=None, result_digest=None, provider_side_exactly_once=False)
                self._save(c, record, 'planned')
        while True:
            with self.store.connect() as c:
                record = self._get(c, 'provider_invocations', invocation_id)
            state = record['state']
            hook('planned') if state == 'PLANNED' else None
            if state == 'REJECTED':
                raise ContractError(record['terminal_outcome'])
            if state == 'INVOCATION_STARTED':
                # A live competing caller or a crash before response persistence.
                # Neither may replay the external effect automatically.
                with self.store.transaction() as c:
                    current = self._get(c, 'provider_invocations', invocation_id)
                    current['terminal_outcome'] = 'INDETERMINATE_PROVIDER_OUTCOME'
                    self._save(c, current, 'indeterminate_provider_outcome')
                raise ContractError('INDETERMINATE_PROVIDER_OUTCOME')
            if state in {'PROVIDER_RESULT_RECORDED', 'ACCEPTANCE_PENDING', 'ACCEPTED'}:
                authority()
                if digest(record['response']) != record['result_digest']:
                    raise ContractError('recorded_result_integrity_failure')
                response = unpack(record['response'])
                if state == 'ACCEPTED':
                    return response
                with self.store.transaction() as c:
                    current = self._get(c, 'provider_invocations', invocation_id)
                    if current['state'] == 'PROVIDER_RESULT_RECORDED':
                        current['state'] = 'ACCEPTANCE_PENDING'
                        self._save(c, current, 'acceptance_pending')
                try:
                    validate(response)
                    authority()
                except Exception as error:
                    reason = str(error) if str(error) in {'content_filter', 'structured_output_failure', 'malformed_provider_response', 'authority_rescinded', 'dispatch_expired'} else 'validation_failure'
                    self._reject(invocation_id, reason)
                    raise
                with self.store.transaction() as c:
                    current = self._get(c, 'provider_invocations', invocation_id)
                    if current['state'] == 'ACCEPTANCE_PENDING':
                        current.update(state='ACCEPTED', terminal_outcome='accepted_evidence')
                        self._save(c, current, 'accepted')
                    elif current['state'] != 'ACCEPTED':
                        raise ContractError('acceptance_conflict')
                return response
            index = record['index']
            if index >= len(profiles):
                self._reject(invocation_id, 'no_ready_fallback')
                raise ContractError('no_ready_fallback')
            profile = profiles[index]
            breaker = self.breaker(profile['route_id'])
            if index and (mode != 'AUTOMATIC_ELIGIBLE' or record['classification'] not in ELIGIBLE):
                reason = 'fallback_confirmation_required' if mode == 'ASK' else 'fallback_disabled'
                self._reject(invocation_id, reason)
                raise ContractError(reason)
            if breaker['state'] == 'OPEN' or (breaker['state'] == 'HALF_OPEN' and breaker['probe']):
                with self.store.transaction() as c:
                    current = self._get(c, 'provider_invocations', invocation_id)
                    if current['state'] != 'PLANNED' or current['index'] != index:
                        continue
                    current.update(index=index + 1, breaker_state=breaker['state'])
                    if index == 0:
                        current.update(classification=breaker['classification'])
                    self._save(c, current, 'breaker_open')
                continue
            ready = self.readiness(profile)
            # All continuity routes, including primary, require explicit admission.
            if ready['readiness_state'] != 'READY':
                self._reject(invocation_id, 'fallback_not_ready' if index else 'primary_not_ready')
                raise ContractError('fallback_not_ready' if index else 'primary_not_ready')
            try:
                authority()
                admitted = admission.consume(self.store, profile, ready['context'], invocation_id, request)
                authority()
            except Exception as error:
                self._reject(invocation_id, denial_class(error))
                raise
            with self.store.transaction() as c:
                current = self._get(c, 'provider_invocations', invocation_id)
                if current['state'] != 'PLANNED' or current['index'] != index:
                    continue
                current_ready = self._get(c, 'provider_readiness', profile['route_id'])
                if current_ready != ready or time.time() > ready['expires_at']:
                    current.update(state='REJECTED', terminal_outcome='readiness_changed')
                    self._save(c, current, 'rejected')
                    continue
                latest = self._get(c, 'provider_breakers', profile['route_id'], breaker)
                if latest['state'] == 'OPEN' or (latest['state'] == 'HALF_OPEN' and latest['probe']):
                    continue
                if latest['state'] == 'HALF_OPEN':
                    latest['probe'] = invocation_id
                    self._breaker(c, profile['route_id'], latest)
                current.update(state='INVOCATION_STARTED', selected_route=profile['route_id'],
                               attempt_id=f'{invocation_id}:{index + 1}',
                               breaker_state=latest['state'], readiness_receipt=ready['receipt_digest'],
                               admission_receipt=admitted, model_requested=profile['model'],
                               placement=profile['placement'])
                self._save(c, current, 'invocation_started')
            hook('invocation_started')
            try:
                authority()
                response = invoke(profile, replace(request, model=profile['model']))
                if not isinstance(response, ChatResponse):
                    raise ProviderError(code='invalid_response')
            except ProviderError as error:
                failure = classification(error)
                with self.store.transaction() as c:
                    current = self._get(c, 'provider_invocations', invocation_id)
                    current.update(classification=failure, raw_error_code=error.code,
                                   state='PLANNED' if failure in ELIGIBLE else 'REJECTED',
                                   index=index + 1, terminal_outcome=None if failure in ELIGIBLE else failure)
                    if failure in ELIGIBLE or latest['state'] == 'HALF_OPEN':
                        self._breaker(c, profile['route_id'],
                                  {'state': 'OPEN', 'classification': failure, 'probe': None,
                                   'changed_at': time.time(), 'invocation_id': invocation_id})
                    self._save(c, current, 'attempt_failed')
                continue
            except Exception as error:
                self._reject(invocation_id, denial_class(error))
                raise
            hook('before_result_persistence')
            # Exclude raw/metadata: those can include upstream credential material.
            result = {k: v for k, v in asdict(response).items() if k not in {'raw', 'metadata'}}
            with self.store.transaction() as c:
                current = self._get(c, 'provider_invocations', invocation_id)
                current.update(state='PROVIDER_RESULT_RECORDED', response=result,
                               model_observed=response.model, provider_observed=profile['kind'],
                               result_digest=digest(result), terminal_outcome=None)
                self._save(c, current, 'provider_result_recorded')
                self._breaker(c, profile['route_id'],
                          {'state': 'CLOSED', 'classification': None, 'probe': None,
                           'changed_at': time.time(), 'invocation_id': invocation_id})
            hook('provider_result_recorded')

    def _reject(self, invocation_id, reason):
        with self.store.transaction() as c:
            current = self._get(c, 'provider_invocations', invocation_id)
            if current['state'] not in {'ACCEPTED', 'REJECTED'}:
                current.update(state='REJECTED', terminal_outcome=reason)
                self._save(c, current, 'rejected')
