"""Durable observation adapter. SQLite owns cross-thread/process sequencing and checkpoints."""
from __future__ import annotations
import json
import uuid
from observation_layer import Observation, ObservationBus, ObservationKind, ObservationSequencer, verify_chain
from residual.core import canonical, ContractError


class StationBus(ObservationBus):
    """ObservationBus interface backed by an atomic store transaction, not an in-memory head."""
    def __init__(self,store,trace,tags=None):
        super().__init__(trace_id=trace)
        self.store,self.trace,self.tags=store,trace,tags or {}
    def emit(self,kind,payload,*,tags=None,source='unknown'):
        try:
            with self.store.transaction() as c:
                if not self.store._observations_enabled(c): return None
                obs=self.store._append_observation(c,self.trace,kind,payload,{**self.tags,**(tags or {})},source)
            self.emitted+=1
            return obs
        except Exception:
            self.errors+=1; self.last_error='observation_delivery_failed'
            self.store.observation_failures+=1
            return None


class ObservationStore:
    def init_observations(self,c):
        self.observation_failures=0
        c.executescript('''
        CREATE TABLE IF NOT EXISTS observations(seq INTEGER PRIMARY KEY AUTOINCREMENT,
            trace TEXT NOT NULL, kind TEXT NOT NULL, provider TEXT, value TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS observation_trace ON observations(trace,seq);
        CREATE TABLE IF NOT EXISTS observation_heads(trace TEXT PRIMARY KEY, head TEXT NOT NULL, count INTEGER NOT NULL);
        ''')

    def _observations_enabled(self,c):
        row=c.execute("SELECT value FROM settings WHERE id='observations_enabled'").fetchone()
        return row is None or json.loads(row[0]) is True

    def observation_bus(self,pid=None,**tags):
        if not self.settings().get('observations_enabled',True): return None
        # Model Workshop also gets a durable trace, without fabricating a project.
        return StationBus(self,pid or 'station',tags)

    def _append_observation(self,c,trace,kind,payload,tags,source):
        row=c.execute('SELECT head,count FROM observation_heads WHERE trace=?',(trace,)).fetchone()
        seq=ObservationSequencer(trace,row['head'] if row else 'GENESIS',row['count'] if row else 0)
        obs=seq.next(kind,payload,tags=tags,source=source)
        c.execute('INSERT INTO observations(trace,kind,provider,value) VALUES(?,?,?,?)',(trace,obs.kind.value,tags.get('provider'),canonical(obs.to_dict())))
        c.execute('INSERT OR REPLACE INTO observation_heads VALUES(?,?,?)',(trace,obs.digest,seq.count))
        return obs

    def observe_workflow(self,c,event,event_hash):
        # Mirrors metadata in the same transaction. Diagnostics cannot veto an LDD admission.
        if not self._observations_enabled(c): return
        try:
            c.execute('SAVEPOINT observation_write')
            et=event['event_type']
            kind=ObservationKind.STATE_TRANSITION if et=='task.transition' else ObservationKind.HANDOFF if et in {'task.claimed','integration.completed'} else ObservationKind.CHECKPOINT
            payload={'event_id':event['event_id'],'event_type':et,'event_hash':event_hash,'task_id':event['task_id'],'attempt':event['attempt']}
            if et=='task.transition': payload.update({k:event['data'][k] for k in ('from','to')})
            self._append_observation(c,event['project_id'],kind,payload,{'actor':event['actor']},'residual.ldd')
            c.execute('RELEASE observation_write')
        except Exception:
            c.execute('ROLLBACK TO observation_write'); c.execute('RELEASE observation_write')
            self.observation_failures+=1

    def observations(self,trace='station',after=0,limit=100,kind='',provider=''):
        if kind and kind not in {x.value for x in ObservationKind}: raise ContractError('Unknown observation kind')
        if type(after) is not int or after<0 or type(limit) is not int or not 1<=limit<=500: raise ContractError('Invalid observation page')
        where=['trace=?','seq>?'];params=[trace,after]
        if kind: where.append('kind=?');params.append(kind)
        if provider: where.append('provider=?');params.append(provider)
        with self.connect() as c:
            rows=list(c.execute('SELECT seq,value FROM observations WHERE '+' AND '.join(where)+' ORDER BY seq LIMIT ?',[*params,limit+1]))
        events=[{'seq':r['seq'],**json.loads(r['value'])} for r in rows[:limit]]
        return {'events':events,'has_more':len(rows)>limit,'next_cursor':events[-1]['seq'] if events else after}

    def observation_summary(self,trace='station'):
        # One read transaction binds validation and the checkpoint to the same snapshot.
        with self.connect() as c:
            c.execute('BEGIN')
            head=c.execute('SELECT head,count FROM observation_heads WHERE trace=?',(trace,)).fetchone()
            expected=head['head'] if head else 'GENESIS'; count=head['count'] if head else 0
            rows=c.execute('SELECT value FROM observations WHERE trace=? ORDER BY seq',(trace,))
            try: valid=verify_chain((Observation(**json.loads(r[0])) for r in rows),expected_head=expected,expected_count=count)
            except (ValueError,TypeError,KeyError): valid=False
            counts={r[0]:r[1] for r in c.execute('SELECT kind,count(*) FROM observations WHERE trace=? GROUP BY kind',(trace,))}
        return {'trace_id':trace,'event_count':count,'head_hash':expected,'integrity':'verified' if valid else 'failed',
                'counts':counts,'delivery_failures':self.observation_failures,'enabled':self.settings().get('observations_enabled',True),
                'schema':'1.1.0','anchor_scope':'Local checkpoint; not an external signature'}

    def observation_export(self,trace):
        summary=self.observation_summary(trace)
        if summary['integrity']!='verified': raise ContractError('Observation chain failed verification; inspect diagnostics')
        with self.connect() as c:
            # Bind the export to the verified head even if new observations arrive concurrently.
            rows=list(c.execute('SELECT value FROM observations WHERE trace=? ORDER BY seq LIMIT ?',(trace,summary['event_count'])))
        events=[Observation(**json.loads(r[0])) for r in rows]
        if not verify_chain(events,expected_head=summary['head_hash'],expected_count=summary['event_count']): raise ContractError('Observation trace changed during export')
        return '\n'.join(canonical(x.to_dict()) for x in events)+'\n'
