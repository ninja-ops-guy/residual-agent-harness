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
test('cancel receipt requires native abort, revocation and cessation proof',()=>{
  const status={operation_id:'op1',state:'RUNNING',session_key:'agent:a:s',run_id:'run1'};
  const p=buildCancelPlan(status,'ws://127.0.0.1:18789');
  const r=verifyCancel({plan:p,beforeIdentity:identity(),afterIdentity:identity(),beforeStatus:status,
    firstAbort:{ok:true,aborted:true,runIds:['run1']},firstCli:cli,
    revokedStatus:{operation_id:'op1',state:'REVOKED',revoked:true},
    secondAbort:{ok:true,aborted:false,runIds:[]},secondCli:cli});
  assert.equal(r.result,'NATIVE_CANCEL_VERIFIED');assert.equal(r.acceptance,'NOT_EVALUATED');
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
test('restart verification requires replacement, continuity and authority reset',()=>{
  const before=identity(),after=identity('i2',{control_connected:false});
  const p=buildRestartPlan(before);
  const r=verifyRestart({plan:p,beforeIdentity:before,afterIdentity:after,cli,
    evidenceDelta:{sequence:6,sha256:hex('4'),observations:[{type:'runtime.started',instance_id:'i2'}]}});
  assert.equal(r.result,'RESTART_VERIFIED');assert.equal(r.qualification,'NOT_ESTABLISHED');
});
test('restart cannot verify same process generation or missing runtime.started',()=>{
  const before=identity(),p=buildRestartPlan(before);
  assert.throws(()=>verifyRestart({plan:p,beforeIdentity:before,afterIdentity:{...before,control_connected:false},cli,
    evidenceDelta:{sequence:4,sha256:hex('3'),observations:[]}}));
  const after=identity('i2',{control_connected:false});
  assert.throws(()=>verifyRestart({plan:p,beforeIdentity:before,afterIdentity:after,cli,
    evidenceDelta:{sequence:6,sha256:hex('4'),observations:[]}}));
});
