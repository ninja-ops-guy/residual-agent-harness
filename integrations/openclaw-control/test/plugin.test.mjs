import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { generateKeyPairSync } from 'node:crypto';
import { mkdtempSync,rmSync,existsSync,readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import plugin,{ROUTE,sourceDigest} from '../index.mjs';
import { ControllerClient } from '../client.mjs';
import { verifyEvidence } from '../protocol.mjs';

// This is a native-API-shape fixture, NOT an installed OpenClaw gateway.
async function setup(t,{version='2026.6.1',badOutput=false}={}) {
  const stateDir=mkdtempSync(join(tmpdir(),'oc-plugin-'));
  const keys=generateKeyPairSync('ed25519');const hooks={};let service,route,active,calls=0;
  const token='fixture-only-not-a-real-token';
  const api={registrationMode:'full',pluginConfig:{runtimeId:'fixture-runtime',agentId:'residual-worker',
    controllerKeys:{owner:keys.publicKey.export({type:'spki',format:'pem'})},controlEnabled:true,hostVersions:['2026.6.1']},
    config:{agents:{list:[{id:'residual-worker',model:'test/model'}]}},
    on(name,handler){hooks[name]=handler;},registerService(value){service=value;},registerHttpRoute(value){route=value;},runtime:{version}};
  api.runtime.config={current:()=>api.config};
  api.runtime.subagent={run:async p=>{
    calls++;const ctx={agentId:'residual-worker',sessionKey:p.sessionKey};
    assert.equal(p.deliver,false);assert.equal(hooks.before_agent_run({prompt:p.message},ctx).outcome,'pass');
    assert.equal(hooks.before_tool_call({toolName:'exec'},ctx).block,true);
    active={runId:'native-fixture-run',p,ctx};return {runId:active.runId};},
    waitForRun:async()=>{hooks.llm_output({runId:badOutput?'wrong-run':active.runId,provider:'test',model:'model',assistantTexts:['fixture response']},active.ctx);return {status:'ok'};}};
  api.runtime.llm={complete:async p=>({text:p.messages[0].content.split(': ').at(-1),provider:'test',model:'model'})};
  plugin.register(api);assert(!existsSync(join(stateDir,'residual-control')),'registration must not write state');
  const beforeStart=hooks.before_agent_run({prompt:'unsigned'},{agentId:'residual-worker'});assert.equal(beforeStart.outcome,'block');
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
  const client=new ControllerClient({endpoint,token,privateKey:keys.privateKey,keyId:'owner'});
  return {api,hooks,route,service,client,endpoint,token,get calls(){return calls;}};
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
  const huge=await fetch(f.endpoint+ROUTE,{method:'POST',headers:{...auth,'Content-Type':'application/json'},body:' '.repeat(100000)});
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
