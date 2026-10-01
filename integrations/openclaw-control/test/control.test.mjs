import test from 'node:test';
import assert from 'node:assert/strict';
import { generateKeyPairSync,sign } from 'node:crypto';
import { chmodSync,readFileSync,writeFileSync,mkdtempSync,rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { DatabaseSync } from 'node:sqlite';
import { canonical,keyId,sha256,signCommand,verifyEvidence,decode64 } from '../protocol.mjs';
import { Journal } from '../journal.mjs';
import { fixture,isCode,deferred } from './helpers.mjs';

test('canonical encoding is stable; invalid numbers and values are rejected',()=>{
  assert.equal(canonical({z:[true,null],a:'é'}),'{"a":"é","z":[true,null]}');
  for(const value of [undefined,NaN,Infinity,1.5,9007199254740992,new Date()])assert.throws(()=>canonical(value));
  assert.throws(()=>decode64('a===',10));
  const pair=generateKeyPairSync('ed25519');assert.equal(keyId(pair.publicKey),keyId(pair.privateKey));
});
test('valid signed work completes without becoming accepted or qualified',async t=>{
  const f=fixture(t);await f.lease();const r=await f.send('dispatch.submit',f.task());await f.plane.settle();
  const status=f.plane.status(r.operation_id);assert.equal(status.state,'COMPLETED');assert.equal(status.start_admitted,true);
  assert.equal(status.acceptance,'NOT_EVALUATED');assert.equal(status.qualification,'NOT_ESTABLISHED');assert.equal(f.calls,1);
  assert.equal(status.output_text,undefined);assert.equal(f.plane.status(r.operation_id,true).output_text,'result');
});
for(const [label,change,code] of [
  ['wrong runtime',{runtime_id:'other'},'STALE_INSTANCE'],['old instance',{instance_id:'old'},'STALE_INSTANCE'],
  ['wrong configuration',{config_digest:'0'.repeat(64)},'CONFIG_DRIFT'],['wrong protocol',{protocol:'other'},'PROTOCOL_MISMATCH'],
  ['expired',{expires_at_ms:1699999999999},'AUTHORITY_EXPIRED'],['future',{issued_at_ms:1700000005000},'AUTHORITY_EXPIRED'],
  ['excessive lifetime',{expires_at_ms:1700000100000},'AUTHORITY_EXPIRED'],['extra authority field',{accepted:true},'SCHEMA_INVALID'],
  ['unsafe identifier',{operation_id:'../x'},'INVALID_ID']]) {
  test(`authorization rejects ${label} before host invocation`,async t=>{
    const f=fixture(t);await assert.rejects(f.send('dispatch.submit',f.task(),change),isCode(code));assert.equal(f.calls,0);
  });
}
test('untrusted signer and signed-body tampering are rejected',async t=>{
  const f=fixture(t);const e=f.envelope('lease.renew',{});e.key_id='intruder';await assert.rejects(f.plane.command(e),isCode('AUTHORITY_DENIED'));
  const changed=f.envelope('lease.renew',{});changed.body=Buffer.from(canonical(f.command('provider.probe',{}))).toString('base64url');
  await assert.rejects(f.plane.command(changed),isCode('AUTHORITY_DENIED'));assert.equal(f.calls,0);
});
test('signed duplicate JSON keys are rejected rather than ambiguously interpreted',async t=>{
  const f=fixture(t);const normal=canonical(f.command('lease.renew',{}));
  const bytes=Buffer.from(normal.replace('"action":"lease.renew"','"action":"bad","action":"lease.renew"'));
  const e={key_id:'owner',body:bytes.toString('base64url'),signature:sign(null,bytes,f.keys.privateKey).toString('base64url')};
  await assert.rejects(f.plane.command(e),isCode('NONCANONICAL_COMMAND'));
});
test('duplicate concurrent signed commands execute once; conflicting IDs fail',async t=>{
  const f=fixture(t);await f.lease();const e=f.envelope('dispatch.submit',f.task());
  const results=await Promise.all([f.plane.command(e),f.plane.command(e),f.plane.command(e)]);await f.plane.settle();
  assert.equal(new Set(results.map(x=>x.operation_id)).size,1);assert.equal(f.calls,1);
  await assert.rejects(f.send('dispatch.submit',f.task({prompt:'different'}),{operation_id:results[0].operation_id}),isCode('IDEMPOTENCY_CONFLICT'));
});
test('no lease and expired lease both deny new work',async t=>{
  const f=fixture(t);await assert.rejects(f.send('dispatch.submit',f.task()),isCode('CONTROL_PLANE_DISCONNECTED'));
  await f.lease();f.advance(20001);await assert.rejects(f.send('dispatch.submit',f.task()),isCode('CONTROL_PLANE_DISCONNECTED'));assert.equal(f.calls,0);
});
test('clock rollback fences new work even when wall-clock lease looks current',async t=>{
  const f=fixture(t);await f.lease();f.advance(-1);await assert.rejects(f.send('dispatch.submit',f.task()),isCode('CLOCK_ROLLBACK'));assert.equal(f.calls,0);
});

test('detected wall-clock rollback fences a pending result before completion',async t=>{
  const d=deferred();const f=fixture(t);await f.lease();
  f.host.dispatch=async p=>{const decision=f.plane.beforeAgent({prompt:p.prompt},{agentId:f.config.agentId,sessionKey:p.sessionKey});
    assert.equal(decision?.outcome,'pass');p.onRun('run-'+p.operationId);await d.promise;return {text:'result',provider:p.provider,model:p.model};};
  const r=await f.send('dispatch.submit',f.task());f.advanceWall(-1);d.resolve();await f.plane.settle();
  const status=f.plane.status(r.operation_id);assert.equal(status.state,'INDETERMINATE');assert.equal(status.reason,'OUTCOME_AFTER_FENCE');
  assert.equal(status.output_sha256,undefined);assert.equal(status.acceptance,'NOT_EVALUATED');
});
test('monotonic budget expiry fences a result even when wall clock remains inside deadline',async t=>{
  const d=deferred();const f=fixture(t);await f.lease();
  f.host.dispatch=async p=>{const decision=f.plane.beforeAgent({prompt:p.prompt},{agentId:f.config.agentId,sessionKey:p.sessionKey});
    assert.equal(decision?.outcome,'pass');p.onRun('run-'+p.operationId);await d.promise;return {text:'result',provider:p.provider,model:p.model};};
  const r=await f.send('dispatch.submit',f.task({timeout_ms:100}));f.advanceMono(150);d.resolve();await f.plane.settle();
  const status=f.plane.status(r.operation_id);assert.equal(status.state,'INDETERMINATE');assert.equal(status.reason,'OUTCOME_AFTER_FENCE');
  assert.equal(status.output_sha256,undefined);assert.equal(status.acceptance,'NOT_EVALUATED');
});

test('unknown version and default observe-only cannot authorize mutation',async t=>{
  const f=fixture(t,{config:{controlEnabled:false}});assert.equal(f.plane.identity().compatibility,'OBSERVE_ONLY');
  await assert.rejects(f.lease(),isCode('OBSERVE_ONLY'));f.config.controlEnabled=true;f.host.version='2026.unknown';
  await assert.rejects(f.lease(),isCode('OBSERVE_ONLY'));assert.equal(f.calls,0);
});
test('provider endpoint drift blocks dispatch and does not leak embedded credentials',async t=>{
  const f=fixture(t);await f.lease();f.runtimeConfig.models.providers.test.baseUrl='http://secret-user:secret-pass@127.0.0.2:9999/v1?api_key=secret-key';
  assert.equal(f.plane.identity().config_state,'DRIFT_DETECTED');
  await assert.rejects(f.send('dispatch.submit',f.task()),isCode('CONFIG_DRIFT'));
  const projection=JSON.stringify((await f.send('config.inspect',{})).projection);for(const x of ['secret-user','secret-pass','secret-key'])assert(!projection.includes(x));
});
test('credential values are outside config projection, with coverage explicitly false',async t=>{
  const f=fixture(t);const digest=f.plane.configDigest();f.runtimeConfig.models.providers.test.apiKey='CANARY_TOKEN';
  assert.equal(f.plane.configDigest(),digest);assert.equal(f.plane.identity().secret_rotation_coverage,false);
  assert(!JSON.stringify(f.plane.projection()).includes('CANARY_TOKEN'));
});
test('configured fallback route cannot silently broaden the candidate profile',async t=>{
  const f=fixture(t);f.runtimeConfig.agents.defaults={model:{primary:'test/model',fallbacks:['other/model']}};
  f.plane.close();f.open();await f.lease();await assert.rejects(f.send('dispatch.submit',f.task()),isCode('UNQUALIFIED_FALLBACK_CONFIG'));
});
test('native cancellation, restart, shell and acceptance are unsupported, not simulated successes',async t=>{
  const f=fixture(t);for(const action of ['gateway.restart','agent.cancel','host.exec','result.accept'])
    await assert.rejects(f.send(action,{}),isCode('UNSUPPORTED_CAPABILITY'));assert.equal(f.calls,0);
});
test('native gate blocks unsigned entry, prompt substitution, repeated admission and missing identity',async t=>{
  const f=fixture(t);await f.lease();const ctx={agentId:f.config.agentId,sessionKey:'agent:residual-worker:residual:unbound'};
  assert.equal(f.plane.beforeAgent({prompt:'unsigned'},ctx).outcome,'block');
  assert.equal(f.plane.beforeAgent({prompt:'unsigned'},{}).outcome,'block');
  assert.equal(f.plane.beforeAgent({prompt:'unmanaged'},{agentId:'other',sessionKey:'agent:other:s'}),undefined);
  f.host.dispatch=async p=>{
    assert.equal(f.plane.beforeAgent({prompt:'changed'}, {agentId:p.agentId,sessionKey:p.sessionKey}).outcome,'block');
    assert.equal(f.plane.beforeAgent({prompt:p.prompt},{agentId:p.agentId,sessionKey:p.sessionKey}).outcome,'pass');
    assert.equal(f.plane.beforeAgent({prompt:p.prompt},{agentId:p.agentId,sessionKey:p.sessionKey}).outcome,'block');
    return {text:'ok',provider:p.provider,model:p.model};
  };
  const r=await f.send('dispatch.submit',f.task());await f.plane.settle();assert.equal(f.plane.status(r.operation_id).state,'COMPLETED');
});
test('all managed tools are blocked; identified unmanaged agent is untouched',t=>{
  const f=fixture(t);for(const ctx of [{agentId:f.config.agentId},{sessionKey:'agent:residual-worker:x'},{}])
    assert.equal(f.plane.beforeTool({toolName:'exec'},ctx).block,true);
  assert.equal(f.plane.beforeTool({toolName:'exec'},{agentId:'other'}),undefined);
});
test('native completion without admission evidence remains indeterminate',async t=>{
  const f=fixture(t,{host:{dispatch:async p=>({text:'fake success',provider:p.provider,model:p.model})}});await f.lease();
  const r=await f.send('dispatch.submit',f.task());await f.plane.settle();const status=f.plane.status(r.operation_id);
  assert.equal(status.state,'INDETERMINATE');assert.equal(status.reason,'NATIVE_ADMISSION_UNPROVEN');assert.equal(status.acceptance,'NOT_EVALUATED');
});
test('provider probe checks nonce response and actual route through native admission without issuing QUALIFIED',async t=>{
  const f=fixture(t);await f.lease();const r=await f.send('provider.probe',{provider:'test',model:'model',timeout_ms:1000});await f.plane.settle();
  const status=f.plane.status(r.operation_id);assert.equal(status.probe_observation,'CHALLENGE_MATCHED');assert.equal(status.start_admitted,true);
  assert.equal(status.qualification,'NOT_ESTABLISHED');
});
test('provider route substitution fails the observation',async t=>{
  const f=fixture(t);f.host.dispatch=async p=>{
    const decision=f.plane.beforeAgent({prompt:p.prompt},{agentId:f.config.agentId,sessionKey:p.sessionKey});
    assert.equal(decision?.outcome,'pass');p.onRun('run-'+p.operationId);return {text:'wrong',provider:'other',model:'other'};
  };await f.lease();
  const r=await f.send('provider.probe',{provider:'test',model:'model',timeout_ms:1000});await f.plane.settle();
  assert.equal(f.plane.status(r.operation_id).state,'FAILED');assert.equal(f.plane.status(r.operation_id).route_matched,false);
});
test('ambiguous provider failure is durable and never automatically replayed',async t=>{
  let calls=0;const f=fixture(t,{host:{dispatch:async()=>{calls++;throw new Error('SECRET_PROVIDER_ERROR');}}});await f.lease();
  const e=f.envelope('provider.probe',{provider:'test',model:'model',timeout_ms:1000});const r=await f.plane.command(e);await f.plane.settle();
  assert.equal(f.plane.status(r.operation_id).state,'INDETERMINATE');await f.plane.command(e);assert.equal(calls,1);
  assert(!JSON.stringify(f.plane.journal.events(0,100)).includes('SECRET_PROVIDER_ERROR'));
  await assert.rejects(f.send('dispatch.submit',f.task()),isCode('RUNTIME_NOT_IDLE'));
});
test('revoke rejects late result but does not falsely claim native stop',async t=>{
  const d=deferred();const f=fixture(t,{host:{dispatch:async()=>d.promise}});await f.lease();
  const r=await f.send('provider.probe',{provider:'test',model:'model',timeout_ms:1000});
  await f.send('dispatch.revoke',{operation_id:r.operation_id});d.resolve({text:'late',provider:'test',model:'model'});await f.plane.settle();
  assert.equal(f.plane.status(r.operation_id).state,'REVOKED');assert.equal(f.plane.status(r.operation_id).output_sha256,undefined);
  const evidence=f.plane.journal.events(0,100).map(row=>verifyEvidence(row));
  assert.equal(evidence.find(row=>row.type==='dispatch.revoked').payload.native_stop_verified,false);
});
test('a replacement process fences the old instance and preserves unknown outcome',async t=>{
  const d=deferred();const f=fixture(t,{host:{dispatch:async()=>d.promise}});await f.lease();const old=f.plane;
  const r=await f.send('provider.probe',{provider:'test',model:'model',timeout_ms:1000});const e=f.envelope('runtime.inspect',{});
  f.open();assert.throws(()=>old.identity(),isCode('STALE_INSTANCE'));
  await assert.rejects(f.plane.command(e),isCode('STALE_INSTANCE'));
  assert.equal(f.plane.status(r.operation_id).reason,'PROCESS_REPLACED');assert.equal(f.plane.identity().control_connected,false);
  d.resolve({text:'late',provider:'test',model:'model'});await old.settle();old.close();assert.equal(f.plane.status(r.operation_id).state,'INDETERMINATE');
});
test('real child-process exit after committed intent is recovered as indeterminate',t=>{
  const directory=mkdtempSync(join(tmpdir(),'oc-crash-'));t.after(()=>rmSync(directory,{recursive:true,force:true}));
  const journalUrl=new URL('../journal.mjs',import.meta.url).href;
  const code=`import {Journal} from ${JSON.stringify(journalUrl)};const j=new Journal(${JSON.stringify(directory)},'runtime');j.transaction(()=>{j.insert('op','abc',{operation_id:'op',state:'INVOCATION_STARTED'});j.event('invocation.started',{operation_id:'op'});});process.exit(23);`;
  const r=spawnSync(process.execPath,['--input-type=module','-e',code],{encoding:'utf8'});assert.equal(r.status,23,r.stderr);
  const j=new Journal(directory,'runtime');try{assert.equal(j.existing('op').record.state,'INDETERMINATE');assert.equal(j.existing('op').record.reason,'PROCESS_REPLACED');}finally{j.close();}
});
test('event chain is byte-verified and tampering/gaps fail',async t=>{
  const f=fixture(t);await f.lease();const rows=f.plane.journal.events(0,100);let previous={sequence:0,sha256:'0'.repeat(64)};
  for(const row of rows){verifyEvidence(row,previous);previous=row;}
  assert.throws(()=>verifyEvidence({...rows[0],sha256:'f'.repeat(64)}),isCode('INTEGRITY_FAILURE'));
  assert.throws(()=>verifyEvidence(rows[1],{sequence:0,sha256:'0'.repeat(64)}),isCode('EVIDENCE_GAP'));
});
for(const [label,sql] of [['event corruption',"UPDATE events SET digest='bad' WHERE seq=1"],['tail truncation','DELETE FROM events WHERE seq=(SELECT MAX(seq) FROM events)'],['operation corruption',"UPDATE operations SET record='{}' WHERE id=(SELECT id FROM operations LIMIT 1)"]]){
  test(`durable ${label} prevents startup`,async t=>{
    const f=fixture(t);await f.lease();f.plane.close();const db=new DatabaseSync(join(f.directory,'control.sqlite'));db.exec(sql);db.close();
    assert.throws(()=>f.open()); // No repair, truncation or manufactured success.
    f.plane.close=()=>{};
  });
}
test('evidence storage saturation fails atomically before native I/O',async t=>{
  const f=fixture(t,{maxEvents:2});await f.lease();await assert.rejects(f.send('dispatch.submit',f.task()),isCode('EVIDENCE_CAPACITY'));
  assert.equal(f.calls,0);assert.equal(f.plane.journal.all().filter(x=>x.action==='dispatch.submit').length,0);
});
test('prompt and native error strings never enter ordinary evidence',async t=>{
  const f=fixture(t);await f.lease();const r=await f.send('dispatch.submit',f.task({prompt:'SECRET_PROMPT_CANARY'}));await f.plane.settle();
  f.plane.observe('openclaw.agent_end',{success:true,prompt:'SECRET_PROMPT_CANARY',error:'SECRET_TOKEN_CANARY'}, {agentId:f.config.agentId,sessionKey:f.plane.status(r.operation_id).session_key});
  const serialized=JSON.stringify(f.plane.journal.events(0,100).map(row=>verifyEvidence(row)));
  assert(!serialized.includes('SECRET_PROMPT_CANARY'));assert(!serialized.includes('SECRET_TOKEN_CANARY'));
});
test('unsafe state permissions reject startup on POSIX',{skip:process.platform==='win32'},t=>{
  const directory=mkdtempSync(join(tmpdir(),'oc-mode-'));t.after(()=>rmSync(directory,{recursive:true,force:true}));chmodSync(directory,0o755);
  assert.throws(()=>new Journal(directory,'runtime'),isCode('UNSAFE_STATE_PERMISSIONS'));
});
