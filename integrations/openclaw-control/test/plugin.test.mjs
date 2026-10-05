import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { generateKeyPairSync } from 'node:crypto';
import { mkdtempSync,rmSync,existsSync,readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import plugin,{ROUTE,sourceDigest} from '../index.mjs';
import { ControllerClient } from '../client.mjs';
import { verifyEvidence,MAX_WIRE_BYTES } from '../protocol.mjs';

// This is a native-API-shape fixture, NOT an installed OpenClaw gateway.
async function setup(t,{version='2026.6.1',badOutput=false,registrationMode='full',
  plugins={entries:{'residual-control':{hooks:{allowConversationAccess:true}}}},beforeOutput}={}) {
  const stateDir=mkdtempSync(join(tmpdir(),'oc-plugin-'));
  const keys=generateKeyPairSync('ed25519');const hooks={},errors=[];let service,route,active,calls=0;
  const token='fixture-only-not-a-real-token';
  const api={id:'residual-control',registrationMode,pluginConfig:{runtimeId:'fixture-runtime',agentId:'residual-worker',
    controllerKeys:{owner:keys.publicKey.export({type:'spki',format:'pem'})},controlEnabled:true,hostVersions:['2026.6.1']},
    config:{agents:{list:[{id:'residual-worker',model:'test/model'}]},plugins},
    // Mirrors the external-plugin conversation policy in OpenClaw v2026.6.1
    // src/plugins/registry.ts. api.on returns no registration acknowledgement.
    on(name,handler){
      if(['before_agent_run','llm_input','llm_output','agent_end'].includes(name) &&
        !effectiveConversationAccess)return;
      hooks[name]=handler;
    },registerService(value){service=value;},registerHttpRoute(value){route=value;},runtime:{version}};
  // The host passes raw api.config but normalized entry.hooks to its registrar.
  // Model v2026.6.1's relevant rules: trim unknown IDs, merge duplicate entries,
  // and replace the previous hooks object when a later boolean policy is present.
  const normalizedEntries={};
  for(const [key,entry] of Object.entries(api.config.plugins?.entries??{})){
    const id=key.trim();if(!id)continue;
    if(!entry || typeof entry!=='object' || Array.isArray(entry)){normalizedEntries[id]={};continue;}
    const hooks=entry.hooks;
    const normalizedHooks=hooks && typeof hooks==='object' && !Array.isArray(hooks)
      ? Object.fromEntries(['allowConversationAccess','allowPromptInjection'].filter(k=>typeof hooks[k]==='boolean').map(k=>[k,hooks[k]])) : {};
    normalizedEntries[id]={hooks:Object.keys(normalizedHooks).length?normalizedHooks:normalizedEntries[id]?.hooks};
  }
  const effectiveConversationAccess=normalizedEntries[api.id]?.hooks?.allowConversationAccess===true;
  api.runtime.config={current:()=>api.config};
  api.runtime.subagent={run:async p=>{
    calls++;const ctx={agentId:'residual-worker',sessionKey:p.sessionKey};
    assert.equal(p.deliver,false);
    if(hooks.before_agent_run)assert.equal(hooks.before_agent_run({prompt:p.message},ctx).outcome,'pass');
    assert.equal(hooks.before_tool_call({toolName:'exec'},ctx).block,true);
    active={runId:'native-fixture-run',p,ctx};return {runId:active.runId};},
    waitForRun:async()=>{await beforeOutput?.(api);hooks.llm_output?.({runId:badOutput?'wrong-run':active.runId,provider:'test',model:'model',assistantTexts:['fixture response']},active.ctx);return {status:'ok'};}};
  plugin.register(api);assert(!existsSync(join(stateDir,'residual-control')),'registration must not write state');
  if(hooks.before_agent_run){const beforeStart=hooks.before_agent_run({prompt:'unsigned'},{agentId:'residual-worker'});assert.equal(beforeStart.outcome,'block');}
  await service.start({stateDir,config:api.config,logger:console});
  assert.equal(route.auth,'gateway');assert.equal(route.match,'exact');
  const server=createServer((req,res)=>{
    // The fixture authenticates this layer; production relies on OpenClaw's native auth= gateway.
    if(req.headers.authorization!==`Bearer ${token}`){res.statusCode=401;res.end();return;}
    route.handler(req,res).catch(()=>{res.statusCode=500;res.end();});
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const endpoint=`http://127.0.0.1:${server.address().port}`;
  t.after(async()=>{await service.stop();await new Promise(resolve=>server.close(resolve));rmSync(stateDir,{recursive:true,force:true});});
  const client=new ControllerClient({endpoint,token,privateKey:keys.privateKey,keyId:'owner',fetchImpl:async(...args)=>{
    const response=await fetch(...args);
    if(response.status!==200)errors.push((await response.clone().json()).error?.code);
    return response;
  }});
  return {api,hooks,errors,route,service,client,endpoint,token,get calls(){return calls;}};
}
async function finish(client,id){
  for(let i=0;i<30;i++){
    const status=await client.command('dispatch.inspect',{operation_id:id});
    if(['COMPLETED','FAILED','INDETERMINATE','REVOKED'].includes(status.state))return status;
    await new Promise(resolve=>setTimeout(resolve,5));
  }
  assert.fail('fixture did not reach a terminal state');
}
test('registered plugin + authenticated loopback HTTP + external signing client round-trip',async t=>{
  const f=await setup(t);const identity=await f.client.inspect();assert.equal(identity.qualification,'NOT_ESTABLISHED');
  assert.equal(identity.plugin_source_sha256,sourceDigest());await f.client.command('lease.renew',{});
  const dispatch=await f.client.command('dispatch.submit',{provider:'test',model:'model',timeout_ms:1000,prompt:'fixture task'});
  const status=await finish(f.client,dispatch.operation_id);assert.equal(status.state,'COMPLETED');assert.equal(status.acceptance,'NOT_EVALUATED');assert.equal(f.calls,1);
  const output=await f.client.command('dispatch.result',{operation_id:dispatch.operation_id});assert.equal(output.output_text,'fixture response');
  const {events}=await f.client.command('evidence.read',{after:0,limit:100});let previous={sequence:0,sha256:'0'.repeat(64)};
  for(const row of events){verifyEvidence(row,previous);previous=row;}
});
test('native output with another run ID cannot become a completed result',async t=>{
  const f=await setup(t,{badOutput:true});await f.client.command('lease.renew',{});
  const r=await f.client.command('dispatch.submit',{provider:'test',model:'model',timeout_ms:1000,prompt:'fixture task'});
  const result=await finish(f.client,r.operation_id);assert.equal(result.state,'INDETERMINATE');assert.equal(result.reason,'OUTPUT_PROVENANCE_MISSING');
});
test('native hook policy that is not full stays observation-only',async t=>{
  const f=await setup(t,{registrationMode:'external'});assert.equal((await f.client.inspect()).compatibility,'OBSERVE_ONLY');
  await assert.rejects(f.client.command('lease.renew',{}));assert.equal(f.calls,0);
});
const deniedHookPolicies=[
  ['missing plugins',undefined],
  ['missing own entry',{entries:{}}],
  ['missing hooks',{entries:{'residual-control':{}}}],
  ['omitted opt-in',{entries:{'residual-control':{hooks:{}}}}],
  ['explicit false',{entries:{'residual-control':{hooks:{allowConversationAccess:false}}}}],
  ['truthy string',{entries:{'residual-control':{hooks:{allowConversationAccess:'true'}}}}],
  ['another plugin opt-in',{entries:{other:{hooks:{allowConversationAccess:true}}}}],
];
for(const [label,plugins] of deniedHookPolicies)for(const action of ['dispatch.submit','provider.probe']) {
  test(`full registration with ${label} rejects ${action} before native invocation`,async t=>{
    // null also represents the absent optional plugins object without setup's default.
    const f=await setup(t,{plugins:plugins??null});
    assert.equal(f.hooks.before_agent_run,undefined);assert.equal(f.hooks.llm_output,undefined);
    const lease=await f.client.command('lease.renew',{}).catch(error=>error);
    const body={provider:'test',model:'model',timeout_ms:1000,...(action==='dispatch.submit'?{prompt:'fixture task'}:{})};
    const result=await f.client.command(action,body).catch(error=>error);
    assert.equal(f.calls,0,'No native run may start when its conversation admission hook was filtered out');
    assert.equal(lease.code,'CONTROL_REQUEST_FAILED');assert.equal(result.code,'CONTROL_REQUEST_FAILED');
    assert.deepEqual(f.errors,['OBSERVE_ONLY','OBSERVE_ONLY']);
    const identity=await f.client.inspect();assert.equal(identity.compatibility,'OBSERVE_ONLY');
    assert.equal(identity.capabilities.signed_dispatch,false);assert.equal(identity.capabilities.provider_probe,false);
  });
}
for(const [label,entries] of [
  ['later trimmed-key denial',{'residual-control':{hooks:{allowConversationAccess:true}},' residual-control ':{hooks:{allowConversationAccess:false}}}],
  ['later trimmed-key hook replacement',{'residual-control':{hooks:{allowConversationAccess:true}},' residual-control ':{hooks:{allowPromptInjection:false}}}],
  ['later trimmed-key malformed entry',{'residual-control':{hooks:{allowConversationAccess:true}},' residual-control ':null}],
])for(const action of ['dispatch.submit','provider.probe']){
  test(`${label} blocks ${action} before native invocation`,async t=>{
    const f=await setup(t,{plugins:{entries}});
    assert.equal(f.hooks.before_agent_run,undefined);assert.equal(f.hooks.llm_output,undefined);
    await f.client.command('lease.renew',{}).catch(()=>{});
    await f.client.command(action,action==='provider.probe'?{provider:'test',model:'model',timeout_ms:1000}:{provider:'test',model:'model',timeout_ms:1000,prompt:'fixture task'}).catch(()=>{});
    assert.equal(f.calls,0,'Raw opt-in cannot override the native normalized hook denial');
    assert.deepEqual(f.errors,['OBSERVE_ONLY','OBSERVE_ONLY']);
  });
}
test('ambiguous equivalent entry names remain denied even when both opt in',async t=>{
  const f=await setup(t,{plugins:{entries:{' residual-control ':{hooks:{allowConversationAccess:true}},'residual-control':{hooks:{allowConversationAccess:true}}}}});
  assert.equal((await f.client.inspect()).compatibility,'OBSERVE_ONLY');
  await assert.rejects(f.client.command('lease.renew',{}));assert.equal(f.calls,0);
});
test('adding a normalized-key collision fences current and in-flight authority',async t=>{
  const f=await setup(t,{beforeOutput:api=>{api.config.plugins.entries[' residual-control ']={hooks:{allowConversationAccess:false}};}});
  await f.client.command('lease.renew',{});
  const r=await f.client.command('dispatch.submit',{provider:'test',model:'model',timeout_ms:1000,prompt:'fixture task'});
  const result=await finish(f.client,r.operation_id);assert.equal(result.state,'INDETERMINATE');assert.equal(result.reason,'CONFIG_DRIFT');
  const identity=await f.client.inspect();assert.equal(identity.compatibility,'OBSERVE_ONLY');assert.equal(identity.config_state,'DRIFT_DETECTED');
});
test('later opt-in cannot enable hooks omitted at registration',async t=>{
  const f=await setup(t,{plugins:{entries:{}}});
  f.api.config.plugins.entries['residual-control']={hooks:{allowConversationAccess:true}};
  assert.equal((await f.client.inspect()).compatibility,'OBSERVE_ONLY');
  await assert.rejects(f.client.command('lease.renew',{}),error=>error.code==='CONTROL_REQUEST_FAILED');
  assert.deepEqual(f.errors,['OBSERVE_ONLY']);assert.equal(f.calls,0);
});
test('current hook-policy revocation fences both dispatch and provider probe',async t=>{
  const f=await setup(t);await f.client.command('lease.renew',{});
  f.api.config.plugins.entries['residual-control'].hooks.allowConversationAccess=false;
  const identity=await f.client.inspect();assert.equal(identity.compatibility,'OBSERVE_ONLY');
  assert.equal(identity.config_state,'DRIFT_DETECTED');
  for(const action of ['dispatch.submit','provider.probe']){
    const body={provider:'test',model:'model',timeout_ms:1000,...(action==='dispatch.submit'?{prompt:'fixture task'}:{})};
    await assert.rejects(f.client.command(action,body),error=>error.code==='CONTROL_REQUEST_FAILED');
  }
  assert.deepEqual(f.errors,['OBSERVE_ONLY','OBSERVE_ONLY']);assert.equal(f.calls,0);
});
test('hook-policy revocation while running prevents result admission',async t=>{
  const f=await setup(t,{beforeOutput:api=>{api.config.plugins.entries['residual-control'].hooks.allowConversationAccess=false;}});
  await f.client.command('lease.renew',{});
  const r=await f.client.command('dispatch.submit',{provider:'test',model:'model',timeout_ms:1000,prompt:'fixture task'});
  const result=await finish(f.client,r.operation_id);
  assert.equal(f.calls,1);assert.equal(result.state,'INDETERMINATE');assert.equal(result.reason,'CONFIG_DRIFT');
  assert.equal(result.output_sha256,undefined);
});
test('unknown native runtime stays observation-only over real HTTP',async t=>{
  const f=await setup(t,{version:'unsupported'});assert.equal((await f.client.inspect()).compatibility,'OBSERVE_ONLY');
  await assert.rejects(f.client.command('lease.renew',{}));assert.equal(f.calls,0);
});
test('gateway-auth, unsigned requests, browser Origin and query variants are refused',async t=>{
  const f=await setup(t);assert.equal((await fetch(f.endpoint+ROUTE)).status,401);
  const headers={Authorization:`Bearer ${f.token}`,'Content-Type':'application/json'};
  const unsigned=await fetch(f.endpoint+ROUTE,{method:'POST',headers,body:JSON.stringify({action:'dispatch.submit'})});assert.equal(unsigned.status,400);
  assert.equal((await fetch(f.endpoint+ROUTE,{headers:{...headers,Origin:'https://attacker.invalid'}})).status,400);
  assert.equal((await fetch(f.endpoint+ROUTE+'?token=hidden',{headers})).status,400);
  assert.equal((await fetch(f.endpoint+ROUTE,{method:'DELETE',headers})).status,405);assert.equal(f.calls,0);
});
test('HTTP request size and content type are bounded',async t=>{
  const f=await setup(t);const auth={Authorization:`Bearer ${f.token}`};
  const huge=await fetch(f.endpoint+ROUTE,{method:'POST',headers:{...auth,'Content-Type':'application/json'},body:' '.repeat(MAX_WIRE_BYTES+1)});
  assert.equal(huge.status,400);assert.equal((await huge.json()).error.code,'REQUEST_TOO_LARGE');
  assert.equal((await fetch(f.endpoint+ROUTE,{method:'POST',headers:{...auth,'Content-Type':'text/plain'},body:'{}'})).status,400);
});
test('client denies non-loopback/credential-bearing endpoints and redirects',async()=>{
  for(const endpoint of ['http://example.com','https://127.0.0.1','http://127.0.0.1/v1','http://u:p@127.0.0.1','http://127.0.0.1?x=secret'])
    assert.throws(()=>new ControllerClient({endpoint,token:'fixture-long-token'}));
  let seen;const c=new ControllerClient({endpoint:'http://127.0.0.1',token:'fixture-long-token',fetchImpl:async(_url,opts)=>{seen=opts;return new Response('',{status:302});}});
  await assert.rejects(c.inspect());assert.equal(seen.redirect,'error');
});
test('client rejects oversized response bodies',async()=>{
  const c=new ControllerClient({endpoint:'http://127.0.0.1',token:'fixture-long-token',fetchImpl:async()=>new Response('x'.repeat(1024*1024+1))});
  await assert.rejects(c.inspect(),error=>error.code==='RESPONSE_TOO_LARGE');
});
test('manifest and package keep default mutations off and accidental publishing disabled',()=>{
  const manifest=JSON.parse(readFileSync(new URL('../openclaw.plugin.json',import.meta.url)));
  const pkg=JSON.parse(readFileSync(new URL('../package.json',import.meta.url)));
  assert.equal(pkg.private,true);assert.deepEqual(pkg.openclaw.extensions,['./index.mjs']);assert.equal(manifest.id,'residual-control');
  assert.equal(manifest.configSchema.additionalProperties,false);assert.equal(manifest.configSchema.properties.controlEnabled.default,false);
  assert.equal(Object.keys(pkg.dependencies||{}).length,0);
});
