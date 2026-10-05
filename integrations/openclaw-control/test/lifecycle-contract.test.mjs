import test from 'node:test';
import assert from 'node:assert/strict';
import { buildCancelPlan,verifyCancel,buildRestartPlan,verifyRestart } from '../lifecycle-contract.mjs';

const hex=c=>'0'.repeat(63)+c;
const identity=(id='i1',extra={})=>({runtime_id:'r1',instance_id:id,host_version:'2026.6.1',
  config_digest:hex('1'),plugin_source_sha256:hex('2'),evidence_head:{sequence:id==='i1'?4:6,sha256:id==='i1'?hex('3'):hex('4')},
  observed_process_start_ms:id==='i1'?1000:2000,control_connected:id==='i1',...extra});
const cli={exit_code:0,stdout_sha256:hex('5'),stderr_sha256:hex('6')};

test('cancel plan exposes no token and fixes exact target twice',()=>{
  const p=buildCancelPlan({operation_id:'op1',state:'RUNNING',session_key:'agent:a:s',run_id:'run1'},'ws://127.0.0.1:18789');
  assert.equal(p.steps.length,3);assert.equal(p.steps[0].argv[2],'chat.abort');assert.deepEqual(p.steps[0].argv,p.steps[2].argv);
  assert(!JSON.stringify(p).includes('Bearer'));assert.equal(p.credential_transport,'OPENCLAW_GATEWAY_TOKEN_ENV_ONLY');
});
test('cancel ACK, revocation and absence remain unverified control observations',()=>{
  const status={operation_id:'op1',state:'RUNNING',session_key:'agent:a:s',run_id:'run1'};
  const p=buildCancelPlan(status,'ws://127.0.0.1:18789');
  const r=verifyCancel({plan:p,beforeIdentity:identity(),afterIdentity:identity(),beforeStatus:status,
    firstAbort:{ok:true,aborted:true,runIds:['run1']},firstCli:cli,
    revokedStatus:{operation_id:'op1',state:'REVOKED',revoked:true},
    secondAbort:{ok:true,aborted:false,runIds:[]},secondCli:cli});
  assertUnverified(r,'cancel');
});
test('cancel never verifies revoke-only evidence',()=>{
  const status={operation_id:'op1',state:'RUNNING',session_key:'agent:a:s',run_id:'run1'},p=buildCancelPlan(status,'ws://127.0.0.1:18789');
  assert.throws(()=>verifyCancel({plan:p,beforeIdentity:identity(),afterIdentity:identity(),beforeStatus:status,
    firstAbort:{ok:true,aborted:false,runIds:[]},firstCli:cli,
    revokedStatus:{operation_id:'op1',state:'REVOKED',revoked:true},
    secondAbort:{ok:true,aborted:false,runIds:[]},secondCli:cli}));
});
test('restart plan is safe-only and carries no credential argument',()=>{
  const p=buildRestartPlan(identity(),{wait:'30s'});
  assert.deepEqual(p.argv,['gateway','restart','--safe','--wait','30s','--json']);
  assert(!JSON.stringify(p).includes('token'));
});
test('restart instance change, continuity and authority reset remain unverified observations',()=>{
  const before=identity(),after=identity('i2',{control_connected:false});
  const p=buildRestartPlan(before);
  const r=verifyRestart({plan:p,beforeIdentity:before,afterIdentity:after,cli,
    evidenceDelta:{sequence:6,sha256:hex('4'),observations:[{type:'runtime.started',instance_id:'i2'}]}});
  assertUnverified(r,'restart');
});
test('restart rejects the same plugin instance or missing runtime.started',()=>{
  const before=identity(),p=buildRestartPlan(before);
  assert.throws(()=>verifyRestart({plan:p,beforeIdentity:before,afterIdentity:{...before,control_connected:false},cli,
    evidenceDelta:{sequence:4,sha256:hex('3'),observations:[]}}));
  const after=identity('i2',{control_connected:false});
  assert.throws(()=>verifyRestart({plan:p,beforeIdentity:before,afterIdentity:after,cli,
    evidenceDelta:{sequence:6,sha256:hex('4'),observations:[]}}));
});

function assertUnverified(receipt,action){
  assert.equal(receipt.schema,'residual.openclaw.lifecycle_receipt.v2');
  assert.equal(receipt.result,action==='cancel'?'NATIVE_CANCEL_UNVERIFIED':'RESTART_UNVERIFIED');
  assert.equal(receipt.capture_validation,'CONSISTENT');
  assert.equal(receipt.physical_outcome_verified,false);
  assert.equal(receipt.trust,'CALLER_SUPPLIED_CONTROL_CAPTURES');
  assert.equal(receipt.acceptance,'NOT_EVALUATED');assert.equal(receipt.qualification,'NOT_ESTABLISHED');
  assert.equal(receipt.release_admissible,false);assert.equal(receipt.promotion_authority,false);
  assert.match(receipt.plan_sha256,/^[a-f0-9]{64}$/);
  assert.equal(receipt.reason,action==='cancel'?'INDEPENDENT_NATIVE_CESSATION_PROOF_UNAVAILABLE':'INDEPENDENT_PROCESS_REPLACEMENT_PROOF_UNAVAILABLE');
}
// Pure fabricated fixtures only: no OpenClaw run, process, CLI or supervisor is started by this file.
function cancelFixture(){
  const status={operation_id:'op1',state:'RUNNING',session_key:'agent:a:s',run_id:'run1'};
  return {plan:buildCancelPlan(status,'ws://127.0.0.1:18789'),beforeStatus:status,
    beforeIdentity:identity(),afterIdentity:identity(),firstAbort:{ok:true,aborted:true,runIds:['run1']},firstCli:{...cli},
    revokedStatus:{operation_id:'op1',state:'REVOKED',revoked:true},secondAbort:{ok:true,aborted:false,runIds:[]},secondCli:{...cli}};
}
function restartFixture(){
  const before=identity(),after=identity('i2',{control_connected:false});
  return {plan:buildRestartPlan(before),beforeIdentity:before,afterIdentity:after,cli:{...cli},
    evidenceDelta:{sequence:6,sha256:hex('4'),observations:[{type:'runtime.started',instance_id:'i2'}]}};
}
for(const [action,fixture,verify] of [['cancel',cancelFixture,verifyCancel],['restart',restartFixture,verifyRestart]]){
  test(`${action} rejects missing/null input`,()=>{
    for(const input of [undefined,null,{},[]])assert.throws(()=>verify(input));
  });
  for(const field of Object.keys(fixture()))test(`${action} rejects missing ${field}`,()=>{
    const input=fixture();delete input[field];assert.throws(()=>verify(input));
  });
  for(const proof of [null,true,{verified:true},{trusted:true,sha256:hex('a')},
    {run_id:'foreign',operation_id:'op1',cessation:true},
    {runtime_id:'r1',instance_id:'old',observed_at_ms:0,verified:true},
    {pid:123,start_ticks:'100',boot_id:'boot-fixture',supervisor_id:'self-reported',replaced:true}]){
    test(`${action} rejects unsupported self-asserted proof ${JSON.stringify(proof)}`,()=>{
      assert.throws(()=>verify({...fixture(),independentProof:proof}),{code:'CAPTURE_INVALID'});
    });
  }
  for(const flag of ['verified','physical_outcome_verified','trusted','supervisorVerified']){
    test(`${action} rejects caller ${flag} flag`,()=>{
      assert.throws(()=>verify({...fixture(),[flag]:true}),{code:'CAPTURE_INVALID'});
    });
  }
  for(const field of ['host_version','config_digest','plugin_source_sha256']){
    test(`${action} rejects changed ${field}`,()=>{
      const input=fixture();input.afterIdentity[field]='different';assert.throws(()=>verify(input));
    });
  }
  test(`${action} rejects stale evidence head`,()=>{
    const input=fixture();input.afterIdentity.evidence_head.sequence=3;assert.throws(()=>verify(input));
  });
  test(`${action} rejects conflicting evidence at same sequence`,()=>{
    const input=fixture();input.afterIdentity.evidence_head={sequence:4,sha256:hex('9')};assert.throws(()=>verify(input));
  });
}
for(const field of ['run_id','session_key','operation_id'])test(`cancel rejects foreign ${field} even with matching abort ACKs`,()=>{
  const input=cancelFixture();input.beforeStatus[field]='foreign';
  if(field==='run_id')input.firstAbort.runIds=['foreign'];
  if(field==='operation_id')input.revokedStatus.operation_id='foreign';
  assert.throws(()=>verifyCancel(input),{code:'CANCEL_CAPTURE_MISMATCH'});
});
for(const [label,change] of [
  ['digest',p=>p.params_sha256=hex('9')],
  ['second abort target',p=>p.steps[2].argv[6]='{"runId":"other","sessionKey":"agent:a:s"}'],
  ['revoke operation',p=>p.steps[1].body.operation_id='other'],
  ['abort executor',p=>p.steps[0].executor='other'],
  ['abort verb',p=>p.steps[0].argv[2]='other'],
  ['extra step',p=>p.steps.push({id:'extra'})],
  ['gateway',p=>p.steps[0].argv[4]='https://example.invalid'],
])test(`cancel rejects altered plan ${label}`,()=>{
  const input=cancelFixture();change(input.plan);assert.throws(()=>verifyCancel(input));
});
test('cancel rejects missing native target and non-running status',()=>{
  for(const change of [s=>s.run_id=null,s=>s.session_key='',s=>s.state='COMPLETED']){
    const input=cancelFixture();change(input.beforeStatus);assert.throws(()=>verifyCancel(input));
  }
});
test('cancel retained synthetic ACK/absence counterexample never proves cessation',()=>{
  // Same capture tuple as the historical counterexample, without spawning its unrelated heartbeat child.
  const input=cancelFixture();input.afterIdentity={...input.afterIdentity,pid:123,start_ticks:'100',
    boot_id:'fixture-boot',native_cessation_verified:true};
  assertUnverified(verifyCancel(input),'cancel');
});
for(const field of ['config_digest','plugin_source_sha256','runtime_id','instance_id']){
  test(`restart rejects stale plan ${field}`,()=>{
    const input=restartFixture();input.plan.before[field]='foreign';assert.throws(()=>verifyRestart(input),{code:'PLAN_STALE'});
  });
}
test('restart plan copies its evidence head rather than sharing mutable capture state',()=>{
  const input=restartFixture();input.beforeIdentity.evidence_head.sequence=5;
  assert.equal(input.plan.before.evidence_head.sequence,4);assert.throws(()=>verifyRestart(input),{code:'PLAN_STALE'});
});
test('restart rejects stale plan evidence hash',()=>{
  const input=restartFixture();input.plan.before.evidence_head.sha256=hex('9');
  assert.throws(()=>verifyRestart(input),{code:'PLAN_STALE'});
});
test('restart rejects altered command and unsupported plan fields',()=>{
  for(const change of [p=>p.argv[2]='--force',p=>p.before.approved=true,p=>p.argv.push('--token','not-a-token')]){
    const input=restartFixture();change(input.plan);assert.throws(()=>verifyRestart(input));
  }
});
for(const value of [undefined,null,NaN,Infinity,-1,999,'2000'])test(`restart rejects invalid/lower process time ${String(value)}`,()=>{
  const input=restartFixture();input.afterIdentity.observed_process_start_ms=value;
  assert.throws(()=>verifyRestart(input),{code:'RESTART_PROCESS_TIME_INVALID'});
});
test('restart rejects non-advanced evidence despite a claimed runtime.started event',()=>{
  const input=restartFixture();input.afterIdentity.evidence_head={...input.beforeIdentity.evidence_head};
  input.evidenceDelta={...input.evidenceDelta,...input.afterIdentity.evidence_head};
  assert.throws(()=>verifyRestart(input),{code:'RESTART_EVIDENCE_NOT_ADVANCED'});
});
test('restart rejects foreign/null runtime.started observations',()=>{
  for(const observations of [[null],[{type:'runtime.started',instance_id:'foreign'}],[]]){
    const input=restartFixture();input.evidenceDelta.observations=observations;
    assert.throws(()=>verifyRestart(input),{code:'RESTART_EVENT_MISSING'});
  }
});
test('restart rejects conflicting evidence digest and surviving authority',()=>{
  const conflict=restartFixture();conflict.evidenceDelta.sha256=hex('9');assert.throws(()=>verifyRestart(conflict));
  const authority=restartFixture();authority.afterIdentity.control_connected=true;assert.throws(()=>verifyRestart(authority));
});
for(const [label,beforeProcess,afterProcess] of [
  ['same PID/start ticks/boot with plugin reload',{pid:123,start_ticks:'100',boot_id:'boot-1'},{pid:123,start_ticks:'100',boot_id:'boot-1'}],
  ['changed PID only',{pid:123},{pid:124}],
  ['PID reused with claimed newer start ticks',{pid:123,start_ticks:'100'},{pid:123,start_ticks:'200'}],
  ['claimed supervisor-bound process replacement',{pid:123,start_ticks:'100',boot_id:'boot-1',supervisor_id:'fixture-supervisor'},
    {pid:124,start_ticks:'200',boot_id:'boot-1',supervisor_id:'fixture-supervisor',process_replacement_verified:true}],
])test(`restart ${label} cannot manufacture independent proof`,()=>{
  const input=restartFixture();Object.assign(input.beforeIdentity,beforeProcess);Object.assign(input.afterIdentity,afterProcess);
  assertUnverified(verifyRestart(input),'restart');
});
test('restart retained same-start-time plugin reload counterexample remains UNVERIFIED',()=>{
  const input=restartFixture();input.beforeIdentity.pid=input.afterIdentity.pid=123;
  input.afterIdentity.observed_process_start_ms=input.beforeIdentity.observed_process_start_ms;
  assertUnverified(verifyRestart(input),'restart');
});
