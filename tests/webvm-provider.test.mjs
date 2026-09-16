import test from 'node:test';
import assert from 'node:assert/strict';
import {ProviderSession, PROTOCOL, RESPONSE_SCHEMA, validInference, protocolReply, validProtocolEnvelope, protocolFailureReason, providerFailureMessage, errorCode} from '../demo/vm/provider-session.js';
const mid = 'm-'+'a'.repeat(32), rid = 'b'.repeat(32);
const request = {request_id:rid, model:'gpt-5-nano', max_output_tokens:256, messages:[{role:'user',content:'Untrusted prompt'}]};
function session() { const p = new ProviderSession(); p.channel = {postMessage(){}, close(){}}; p.connected = true; p.lastSeen = Date.now(); return p; }
test('SDK is not loaded by creating a session', () => { const p = new ProviderSession(); assert.equal(p.ready,false); assert.equal(p.channel,null); });
test('bounded request contract rejects malformed role, id, model and token budget', () => {
 assert.equal(validInference(request),true);
 for (const change of [{messages:[{role:'root',content:'bad'}]}, {request_id:'../escape'}, {model:'x;alert(1)'}, {max_output_tokens:1537}, {max_output_tokens:true}, {messages:[{role:'user',content:'x'.repeat(65536)}]}]) assert.equal(!!validInference({...request,...change}),false);
});
test('no inference without a live connection and explicit grant', async () => {
 const p = session(); assert.equal((await p.infer(mid,request)).error,'provider_disconnected'); p.close();
});
test('reply correlation and single-call budget', async () => {
 const p=session(); p.begin(mid,1,request.model); const result=p.infer(mid,request);
 p.receive({protocol:PROTOCOL, kind:'response', mission_id:'m-'+'c'.repeat(32), request_id:rid,ok:true,text:'wrong'});
 assert.equal(p.pending.size,1);
 p.receive({protocol:PROTOCOL,kind:'response',mission_id:mid,request_id:rid,ok:true,text:'accepted'});
 assert.equal((await result).text,'accepted'); assert.equal(p.pending.size,0);
 assert.equal((await p.infer(mid,{...request,request_id:'d'.repeat(32)})).error,'provider_budget_exhausted'); p.close();
});
test('duplicate requests cannot consume another model call', async () => {
 const p=session(); p.begin(mid,3,request.model); const result=p.infer(mid,request);
 assert.equal((await p.infer(mid,request)).error,'provider_budget_exhausted');
 p.end(); assert.equal((await result).error,'mission_cancelled'); p.close();
});
test('heartbeat expiry blocks grants', () => { const p=session();p.lastSeen=Date.now()-16000;assert.equal(p.ready,false);assert.throws(()=>p.begin(mid,1,request.model));p.close(); });
test('model selection is bound to grant', async () => { const p=session();p.begin(mid,1,request.model);assert.equal((await p.infer(mid,{...request,model:'other'})).error,'provider_budget_exhausted');p.close(); });
test('errors are mapped to safe codes, not arbitrary server bodies', () => {
 assert.equal(errorCode({error:'popup_blocked'}),'popup_blocked');assert.equal(errorCode({msg:'private token',error:'secret'}),'provider_error');
});
test('protocol tool schema is strict at the top level', () => {
 assert.deepEqual(RESPONSE_SCHEMA.required,['updates','requests']); assert.equal(RESPONSE_SCHEMA.additionalProperties,false);
});
test('tool-call responses are converted to the exact RESIDUAL envelope', () => {
 const envelope={updates:{answer:{text:'ok',citations:[]}},requests:[]};
 const result={message:{tool_calls:[{function:{name:'residual_submit',arguments:JSON.stringify(envelope)}}]}};
 assert.equal(protocolReply(result),JSON.stringify(envelope)); assert.equal(validProtocolEnvelope(envelope),true);
});
test('plain and single fenced JSON envelopes normalize to the exact worker envelope', () => {
 const envelope={updates:{answer:{text:'ok',citations:[]}},requests:[]};
 assert.equal(protocolReply({message:{content:JSON.stringify(envelope)}}),JSON.stringify(envelope));
 assert.equal(protocolReply({message:{content:`\`\`\`json\n${JSON.stringify(envelope)}\n\`\`\``}}),JSON.stringify(envelope));
});
test('protocol failures stay fail-closed but expose only bounded structural reasons', () => {
 let error;
 try { protocolReply({message:{content:'Here is your answer'}}); } catch (value) { error=value; }
 assert.equal(error?.code,'provider_protocol_invalid');
 assert.equal(protocolFailureReason(error),'content_not_json');
 assert.match(providerFailureMessage(error.code, protocolFailureReason(error)),/not a JSON worker envelope/);
 assert.throws(()=>protocolReply({message:{content:JSON.stringify({updates:{}})}}),/provider_protocol_invalid/);
 assert.throws(()=>protocolReply({message:{tool_calls:[{function:{name:'other',arguments:'{}'}}]}}),/provider_protocol_invalid/);
 assert.throws(()=>protocolReply({message:{tool_calls:[{function:{name:'residual_submit',arguments:'{}'}},{function:{name:'residual_submit',arguments:'{}'}}]}}),/provider_protocol_invalid/);
});
test('provider response detail is visible to the session without changing the safe error code', async () => {
 const changes=[]; const p=session(); p.onState=(...v)=>changes.push(v); p.begin(mid,1,request.model); const result=p.infer(mid,request);
 p.receive({protocol:PROTOCOL,kind:'response',mission_id:mid,request_id:rid,ok:false,error:'provider_protocol_invalid',detail:'content_not_json'});
 assert.equal((await result).error,'provider_protocol_invalid');
 assert.match(changes.at(-1)[1],/not a JSON worker envelope/); p.close();
});
test('lost heartbeat produces visible disconnection once', () => {
 const changes=[]; const p=session();p.onState=(...v)=>changes.push(v);p.lastSeen=Date.now()-16000;
 p.checkConnection();p.checkConnection();assert.equal(p.connected,false);assert.equal(changes.length,1);assert.equal(changes[0][0],'disconnected');p.close();
});
