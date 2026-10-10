import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {deriveTimeline,reconstructState,diffStates} from '../demo/vm/mission-control-timetravel.js';

const base={schema_version:'1.0',session_id:'ses_a',release:{commit:'abc'}};
const event=(type,mono,context={},extra={})=>({...base,event_id:`evt_${mono}`,trace_id:'run_a',run_id:'run_a',mission_id:'m-'+'a'.repeat(32),timestamp:`2026-09-19T00:00:${String(mono).padStart(2,'0')}.000Z`,monotonic_ms:mono,component:type.split('.')[0],event_type:type,severity:'info',context,...extra});

test('time travel orders deterministically without mutating the input',()=>{
  const source=[event('mission.finished',3,{status:'passed'}),event('mission.submitted',1,{mode:'audit'}),event('mission.started',2,{status:'running'})];
  const before=JSON.stringify(source),ordered=deriveTimeline(source,'run_a');
  assert.deepEqual(ordered.map(x=>x.event_type),['mission.submitted','mission.started','mission.finished']);
  assert.equal(JSON.stringify(source),before);
});

test('reconstruction is point-in-time and does not bleed future state backward',()=>{
  const events=[event('mission.submitted',1,{mode:'build'}),event('runtime.health_changed',2,{health:'ready'}),event('evidence.projected',3,{sequence:7,evidence_kind:'verification'}),event('mission.finished',4,{status:'passed',execution:'generated_artifacts'})];
  const past=reconstructState(events,1),future=reconstructState(events,3);
  assert.equal(past.mission.status,'submitted');assert.equal(past.runtime.health,'ready');assert.equal(past.evidence.count,0);
  assert.equal(future.mission.status,'passed');assert.equal(future.mission.execution,'generated_artifacts');assert.equal(future.evidence.count,1);assert.equal(future.evidence.last_kind,'verification');
});

test('state diff reports only changed flattened fields',()=>{
  const a={mission:{status:'running'},runtime:{health:'ready'}},b={mission:{status:'passed'},runtime:{health:'ready'}};
  assert.deepEqual(diffStates(a,b),[{field:'mission.status',from:'running',to:'passed'}]);
});

test('Mission Control diagnostics mounts the debugger and the WebVM installer ships it',()=>{
  const diagnostics=readFileSync(new URL('../demo/vm/mission-control-diagnostics.js',import.meta.url),'utf8');
  const installer=readFileSync(new URL('../demo/vm/install_workbench.py',import.meta.url),'utf8');
  const mission=readFileSync(new URL('../demo/vm/mission-control.js',import.meta.url),'utf8');
  assert.match(diagnostics,/mission-control-timetravel\.js/);assert.match(diagnostics,/mountTimeTravelDebug\(root,diagnostics\)/);assert.match(installer,/mission-control-timetravel\.js/);
});


test('time travel dashboard exposes the interactive 16-bit controls',()=>{
  const source=readFileSync(new URL('../demo/vm/mission-control-timetravel.js',import.meta.url),'utf8');
  assert.match(source,/CLICK DELOREAN TO ENTER TIMELINE/);
  assert.match(source,/JUMP TO FAILURE/);
  assert.match(source,/JUMP TO EVIDENCE/);
  assert.match(source,/DIFF VIEW/);
  assert.match(source,/image-rendering:pixelated/);
  assert.match(source,/radial-gradient\(#9dffb2/);
  assert.match(source,/READ-ONLY RECONSTRUCTION/);
});

test('full session never blends independent run mission/provider/evidence state',()=>{
  const events=[event('mission.finished',1,{status:'failed',failure_code:'old-failure'}),event('provider.request_requested',2,{model:'old-model'}),event('evidence.projected',3,{sequence:9,evidence_kind:'verification'}),event('mission.submitted',4,{mode:'audit'},{run_id:'run_b',mission_id:'m-'+'b'.repeat(32)})];
  const state=reconstructState(events,3);
  assert.equal(state.run_id,'run_b');assert.equal(state.mission.status,'submitted');assert.equal(state.mission.failure_code,null);assert.equal(state.provider.model,null);assert.equal(state.evidence.count,0);
});

test('ordering survives monotonic clock restart and retains stable ties',()=>{
  const before=event('mission.started',500,{}, {timestamp:'2026-10-09T00:00:00Z'}),after=event('mission.finished',1,{}, {timestamp:'2026-10-09T00:01:00Z'});
  assert.deepEqual(deriveTimeline([after,before]).map(x=>x.event_type),['mission.started','mission.finished']);
  assert.deepEqual(deriveTimeline([{...before,event_id:'a'},{...before,event_id:'b'}]).map(x=>x.event_id),['a','b']);
});

test('transport completion cannot overwrite a verified terminal result',()=>{
  const state=reconstructState([event('mission.finished',1,{status:'passed'}),event('mission.host_run_completed',2,{run_status:'unknown'})]);
  assert.equal(state.mission.status,'passed');
});

test('empty, invalid and out-of-range history is safe; returned events are isolated',()=>{
  assert.deepEqual(deriveTimeline(null),[]);assert.equal(reconstructState([],99).event_index,-1);
  const source=[null,event('mission.submitted',1,{mode:'audit'})];const timeline=deriveTimeline(source);timeline[0].context.mode='changed';assert.equal(source[1].context.mode,'audit');
  assert.equal(reconstructState(timeline,900).event_index,0);
});

test('rejection evidence is a failure target without granting acceptance authority',async()=>{
  const {isFailure}=await import('../demo/vm/mission-control-timetravel.js');
  assert.equal(isFailure(event('evidence.projected',1,{evidence_kind:'counterexample'})),true);
  assert.equal(isFailure(event('evidence.projected',1,{evidence_kind:'obligation_accepted'})),false);
  assert.equal(reconstructState([event('evidence.projected',1,{evidence_kind:'obligation_accepted'})]).mission.status,'unknown');
});
