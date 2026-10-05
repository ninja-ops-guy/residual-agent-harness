import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync,rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { OpenClawStationWorker,normalizeCandidate } from '../station-worker.mjs';
import { canonical,sha256 } from '../protocol.mjs';

function row(sequence,previous,type,instance='instance-1'){
  const body={sequence,previous_sha256:previous,runtime_id:'runtime-1',instance_id:instance,
    observed_at_ms:1700000000000+sequence,type,payload:{},trust:'RUNTIME_REPORTED',acceptance:'NOT_EVALUATED'};
  const bytes=Buffer.from(canonical(body));return {sequence,body:bytes.toString('base64url'),sha256:sha256(bytes),previous_sha256:previous};
}
function fixture(t,{output='{"files":{"a.py":"x=1\\n"}}',allowCloud=true,placement='local',brokenChain=false}={}){
  const dir=mkdtempSync(join(tmpdir(),'oc-station-worker-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));
  const first=row(1,'0'.repeat(64),'control.lease');const second=row(2,first.sha256,'invocation.started');
  const third=row(3,brokenChain?'f'.repeat(64):second.sha256,'execution.result');
  const events=[first,second,third];
  const baseline={runtime_id:'runtime-1',instance_id:'instance-1',plugin_version:'0.2.0',host_version:'2026.6.1',
    config_digest:'1'.repeat(64),config_state:'MATCH',compatibility:'DECLARED_CANDIDATE',
    plugin_source_sha256:'2'.repeat(64),evidence_head:{sequence:0,sha256:'0'.repeat(64)}};
  const post={...baseline,evidence_head:{sequence:3,sha256:third.sha256}};
  const packet={project_goal:'goal',task_id:'OPS-1',instruction:'write a.py',writable_files:['a.py'],files:{'a.py':'x=0\n'},
    checks:[],repair_findings:[],prior_candidate_files:{},spec_hash:'3'.repeat(64),base_commit:'4'.repeat(40),parent_receipts:[]};
  const work={project_id:'p-test',task_id:'OPS-1',attempt:1,lease:'lease-secret',packet,allow_cloud:allowCloud};
  const station={results:[],heartbeats:0,claims:0,
    async claim(){this.claims++;return {work};},
    async heartbeat(){this.heartbeats++;return {ok:true};},
    async result(_state,response,evidence){this.results.push({response,evidence});return {task_id:'OPS-1',state:'review_ready'};}};
  let inspectCount=0;const calls=[];
  const outputHash=sha256(Buffer.from(output));
  const controller={
    async inspect(){return inspectCount++===0?baseline:post;},
    async command(action,body,options={}){
      calls.push({action,body,options});
      if(action==='lease.renew')return {state:'RECORDED'};
      if(action==='dispatch.submit')return {operation_id:options.operationId,state:'INVOCATION_STARTED'};
      if(action==='dispatch.inspect')return {operation_id:body.operation_id,state:'COMPLETED',input_sha256:'5'.repeat(64),
        output_sha256:outputHash,route_matched:true,provider:'test',model:'model'};
      if(action==='dispatch.result')return {operation_id:body.operation_id,state:'COMPLETED',input_sha256:'5'.repeat(64),
        output_sha256:outputHash,route_matched:true,output_text:output,provider:'test',model:'model'};
      if(action==='evidence.read')return {events:events.filter(e=>e.sequence>body.after).slice(0,body.limit)};
      throw new Error('unexpected action '+action);
    }};
  const config={projectId:'p-test',name:'worker',provider:'test',model:'model',placement,timeoutMs:1000,pollMs:25,stateDir:dir};
  const worker=new OpenClawStationWorker({config,station,controller,stateFile:join(dir,'pending.json')});
  return {worker,station,controller,calls,packet,events,baseline,post};
}

test('bridge returns only candidate + non-authoritative evidence to Station',async t=>{
  const f=fixture(t);assert.equal(await f.worker.runOnce(),true);assert.equal(f.station.results.length,1);
  const {response,evidence}=f.station.results[0];assert.deepEqual(response,{files:{'a.py':'x=1\n'}});
  assert.equal(evidence.schema,'residual.remote_execution_evidence.v1');
  assert.equal(evidence.acceptance,'NOT_EVALUATED');assert.equal(evidence.qualification,'NOT_ESTABLISHED');
  assert.equal(evidence.trust,'CONTROLLER_OBSERVED_RUNTIME_REPORTED');
  assert.equal(evidence.station_packet_sha256,sha256(Buffer.from(canonical(f.packet))));
  assert.equal(evidence.station_response_sha256,sha256(Buffer.from(canonical(response))));
  assert.equal(evidence.evidence_tip_sha256,f.events.at(-1).sha256);
  assert(f.calls.some(x=>x.action==='dispatch.submit'));assert(!f.calls.some(x=>x.action==='result.accept'));
});

test('cloud execution is denied before OpenClaw dispatch when Station disallows it',async t=>{
  const f=fixture(t,{allowCloud:false,placement:'cloud'});
  await assert.rejects(f.worker.runOnce(),error=>error.code==='CLOUD_NOT_AUTHORIZED');
  assert.equal(f.calls.length,0);assert.equal(f.station.results.length,0);
});

test('candidate paths outside Station writable_files fail closed to an empty proposal',async t=>{
  const f=fixture(t,{output:'{"files":{"../escape":"owned"}}'});
  assert.equal(await f.worker.runOnce(),true);
  assert.deepEqual(f.station.results[0].response,{files:{}});
  assert.equal(f.station.results[0].evidence.state,'COMPLETED');
  assert.equal(f.station.results[0].evidence.acceptance,'NOT_EVALUATED');
});

test('evidence-chain discontinuity prevents Station submission',async t=>{
  const f=fixture(t,{brokenChain:true});
  await assert.rejects(f.worker.runOnce(),error=>error.code==='EVIDENCE_GAP');
  assert.equal(f.station.results.length,0);
});

test('candidate normalizer rejects extra root fields and non-string content',()=>{
  assert.throws(()=>normalizeCandidate('{"files":{"a.py":"x"},"approved":true}',['a.py']));
  assert.throws(()=>normalizeCandidate('{"files":{"a.py":42}}',['a.py']));
});
