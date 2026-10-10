import test from 'node:test';
import assert from 'node:assert/strict';

import {
  DemoDiagnostics,
  DiagnosticBuffer,
  classifyFailure,
  sanitizeContext,
} from '../demo/vm/mission-control-diagnostics.js';

const mid = 'm-' + 'a'.repeat(32);
const rid = 'b'.repeat(32);

function diagnostics() {
  const value = new DemoDiagnostics();
  value.buffer.events.length = 0;
  return value;
}

test('context schema rejects prompt/content/credentials and arbitrary fields', () => {
  const safe = sanitizeContext({
    mission_id: mid,
    request_id: rid,
    model: 'gpt-5-nano',
    prompt: 'private user prompt',
    content: 'private provider output',
    authorization: 'Bearer top-secret-token',
    cookie: 'session=secret',
    arbitrary: {nested: 'secret'},
  });
  assert.deepEqual(safe, {mission_id: mid, request_id: rid, model: 'gpt-5-nano'});
});

test('sanitizer redacts credentials and strips URL query material from allowed errors', () => {
  const safe = sanitizeContext({
    error_name: 'ProviderError',
    error_message: 'Bearer abcdefghijklmnopqrstuvwxyz https://example.test/callback?token=supersecret&code=private',
  });
  assert.equal(safe.error_name, 'ProviderError');
  assert.equal(safe.error_message.includes('supersecret'), false);
  assert.equal(safe.error_message.includes('private'), false);
  assert.equal(safe.error_message.includes('abcdefghijklmnopqrstuvwxyz'), false);
  assert.match(safe.error_message, /\[REDACTED\]/);
  assert.match(safe.error_message, /https:\/\/example\.test\/callback/);
});

test('diagnostic ring buffer stays bounded', () => {
  const buffer = new DiagnosticBuffer(3);
  for (let i = 0; i < 8; i++) buffer.push({i});
  assert.deepEqual(buffer.snapshot(), [{i:5}, {i:6}, {i:7}]);
});

test('known failures are classified and unsupported causes remain unknown', () => {
  assert.equal(classifyFailure('provider_timeout'), 'ProviderTimeout');
  assert.equal(classifyFailure('service_worker_failure'), 'ServiceWorkerFailure');
  assert.equal(classifyFailure('some_new_failure'), 'UnknownFailure');
});

test('host wrapper preserves execution behavior and rethrows the original failure', async () => {
  const diag = diagnostics();
  const original = new Error('guest failed');
  let mailbox = null;
  const host = {
    ready: () => true,
    health: () => 'ready',
    restart: () => 'restart-result',
    focus: () => 'focus-result',
    mailbox: async (path, text) => { mailbox = {path, text}; return 'mailbox-result'; },
    run: async () => { throw original; },
  };
  const wrapped = diag.wrapHost(host);
  assert.equal(wrapped.ready(), true);
  assert.equal(wrapped.health(), 'ready');
  assert.equal(wrapped.restart(), 'restart-result');
  assert.equal(wrapped.focus(), 'focus-result');
  await assert.rejects(wrapped.run({id:mid, mode:'audit'}), error => error === original);
  assert.equal(await wrapped.mailbox(`/${mid}-${rid}.json`, '{"secret":"provider-payload"}'), 'mailbox-result');
  assert.equal(mailbox.text, '{"secret":"provider-payload"}');
  const retained = JSON.stringify(diag.bundle());
  assert.equal(retained.includes('provider-payload'), false);
  assert.equal(retained.includes('secret'), false);
});

test('run correlation does not retain prompt or provider message contents', () => {
  const diag = diagnostics();
  const runId = diag.startRun(mid, 'build');
  diag.consumeFrame({
    mission_id: mid,
    kind: 'inference_requested',
    data: {request_id: rid, model:'gpt-5-nano', max_output_tokens:512, messages:[{role:'user', content:'DO NOT RETAIN ME'}]},
  });
  diag.consumeFrame({
    mission_id: mid,
    kind: 'mission_finished',
    data: {status:'failed', execution:'generated_artifacts', result:{unresolved:{worker:{code:'provider_timeout'}}}},
  });
  const bundle = diag.bundle(runId);
  const retained = JSON.stringify(bundle);
  assert.equal(bundle.manifest.run_id, runId);
  assert.equal(bundle.manifest.authoritative_execution_evidence, false);
  assert.equal(retained.includes('DO NOT RETAIN ME'), false);
  assert.equal(retained.includes('provider_timeout'), true);
  assert.equal(retained.includes('ProviderTimeout'), true);
});

test('telemetry emitter rejects invalid event names instead of creating arbitrary log records', () => {
  const diag = diagnostics();
  assert.equal(diag.emit('not valid', {status:'bad'}), null);
  assert.equal(diag.buffer.snapshot().length, 0);
});

test('streamed guest frames survive every possible two-chunk boundary',()=>{
  const frame='\x1b]777;RESIDUAL;'+Buffer.from(JSON.stringify({mission_id:mid,kind:'mission_started',data:{}})).toString('base64')+'\x07';
  for(let split=1;split<frame.length;split++){
    const diag=diagnostics();diag.consumeOutput(frame.slice(0,split));diag.consumeOutput(frame.slice(split));
    assert.equal(diag.buffer.snapshot().filter(e=>e.event_type==='mission.started').length,1,`split ${split}`);
  }
});

test('malformed and oversized streaming frames recover without retaining payloads',()=>{
  const diag=diagnostics();diag.consumeOutput('\x1b]777;RESIDUAL;'+'x'.repeat(400001));assert.equal(diag.outputCarry,'');
  diag.consumeOutput('\x1b]777;RESIDUAL;INVALID\x07');
  diag.consumeOutput('\x1b]777;RESIDUAL;'+Buffer.from(JSON.stringify({mission_id:mid,kind:'mission_started',data:{}})).toString('base64')+'\x07');
  assert.equal(diag.buffer.snapshot().filter(e=>e.event_type==='mission.started').length,1);
});

test('restored session retains run correlation and does not invent a new run',()=>{
  const storage=new Map(),saved=globalThis.sessionStorage;
  globalThis.sessionStorage={getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)};
  try{
    const original=diagnostics(),run=original.startRun(mid,'audit');
    const restored=new DemoDiagnostics();assert.equal(restored.latestRunId,run);
    restored.consumeFrame({mission_id:mid,kind:'mission_started',data:{}});
    assert.equal(restored.buffer.snapshot().filter(e=>e.event_type==='mission.submitted').length,1);
    assert.equal(restored.buffer.snapshot().at(-1).run_id,run);
  }finally{if(saved===undefined)delete globalThis.sessionStorage;else globalThis.sessionStorage=saved}
});

test('mailbox lifecycle is bound to its mission without exposing payloads',async()=>{
  const diag=diagnostics(),run=diag.startRun(mid,'audit');
  const host=diag.wrapHost({ready:()=>true,mailbox:async()=>true});assert.equal(host.health(),'ready');
  await host.mailbox(`/${mid}-${rid}.json`,'private response');
  const writes=diag.buffer.snapshot().filter(e=>e.event_type.startsWith('provider.mailbox'));
  assert.equal(writes.length,2);assert(writes.every(e=>e.run_id===run&&e.mission_id===mid));assert(!JSON.stringify(writes).includes('private response'));
});
