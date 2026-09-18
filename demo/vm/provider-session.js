/* Same-origin relay; no credentials cross the channel or enter the guest. */
export const PROTOCOL = 'residual.provider.v1';
export const MAX_WIRE = 65536;
export const MAX_PROVIDER_OUTPUT_TOKENS = 8192;
export const PROVIDER_LIVENESS_MS = 300000;
export const validId = value => typeof value === 'string' && /^m-[a-f0-9]{32}$/.test(value);
export const validRequest = value => typeof value === 'string' && /^[a-f0-9]{32}$/.test(value);
export const validModel = value => typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,95}$/.test(value);
export const bounded = value => { try { return new TextEncoder().encode(JSON.stringify(value)).length <= MAX_WIRE; } catch { return false; } };
export const RESPONSE_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['updates', 'requests'],
  properties: {
    updates: {type: 'object'},
    requests: {type: 'array', items: {
      type: 'object', additionalProperties: false,
      required: ['obligation_id', 'artifact_id', 'start_line', 'end_line'],
      properties: {
        obligation_id: {type: 'string'}, artifact_id: {type: 'string'},
        start_line: {type: 'integer', minimum: 1}, end_line: {type: 'integer', minimum: 1}
      }
    }}
  }
};
const PROTOCOL_REASONS = new Set([
  'tool_call_count', 'tool_name', 'tool_arguments_empty', 'tool_arguments_not_json',
  'content_missing', 'content_empty', 'content_not_json', 'envelope_shape', 'response_truncated'
]);
const PROVIDER_PROGRESS_STAGES = new Set([
  'model_selected', 'request_dispatched', 'response_received', 'protocol_rejected', 'envelope_decoded'
]);
export class ProviderProtocolError extends Error {
  constructor(reason) { super('provider_protocol_invalid'); this.name='ProviderProtocolError'; this.code='provider_protocol_invalid'; this.reason=PROTOCOL_REASONS.has(reason)?reason:'envelope_shape'; }
}
export const protocolFailureReason = error => PROTOCOL_REASONS.has(error?.reason) ? error.reason : null;
export function providerTransportAfterFailure(current, code) { const mode=current==='json'?'json':'tool'; return mode==='tool'&&code==='provider_protocol_invalid'?'json':mode; }
export function validInference(req) { return req && validRequest(req.request_id) && validModel(req.model) && Number.isInteger(req.max_output_tokens) && req.max_output_tokens>=1 && req.max_output_tokens<=MAX_PROVIDER_OUTPUT_TOKENS && Array.isArray(req.messages) && req.messages.length>=1 && req.messages.length<=6 && req.messages.every(m=>m&&['system','user','assistant'].includes(m.role)&&typeof m.content==='string') && bounded(req); }
export function errorCode(error) { const code=error?.error||error?.code; return ['popup_blocked','auth_window_closed','not_available_in_app'].includes(code)?code:'provider_error'; }
function protocolReasonText(detail) { const messages={tool_call_count:'The model returned an unexpected number of tool calls.',tool_name:'The model called a tool other than residual_submit.',tool_arguments_empty:'The residual_submit tool call had no arguments.',tool_arguments_not_json:'The residual_submit arguments were not valid JSON.',content_missing:'The normalized provider response contained neither a usable tool call nor text.',content_empty:'The provider returned empty text instead of a worker envelope.',content_not_json:'The provider returned text that was not a JSON worker envelope.',envelope_shape:'The returned JSON did not have exactly the required updates/requests worker shape.',response_truncated:'The provider hit the output-token limit before completing the RESIDUAL worker envelope.'}; return messages[detail]||''; }
export function providerFailureMessage(code, detail=null) { const messages={provider_model_unavailable:'Provider connected, but the selected model is unavailable. Choose another model and retry.',provider_authorization_failed:'Provider connected, but this model request was not authorized/allowed. Check account allowance or billing.',provider_protocol_invalid:'Provider returned a response, but it violated the RESIDUAL worker protocol. No candidate was accepted.',provider_timeout:'Provider request timed out. No candidate was accepted; a timed-out remote request may still be billed.',provider_request_failed:'Provider request failed before a usable candidate was returned. No candidate was accepted.',provider_response_too_large:'Provider response exceeded the browser bridge limit. No candidate was accepted.',provider_budget_exhausted:'Provider call budget was exhausted. RESIDUAL refused another dispatch.',provider_disconnected:'Provider connection was lost before the request completed.',mission_cancelled:'Provider authorization was revoked because the mission was cancelled.'}; const base=messages[code]||'Provider failed with a bounded safe error code. No candidate was accepted.'; const why=code==='provider_protocol_invalid'?protocolReasonText(detail):''; return why?`${base} ${why}`:base; }
export function providerProgressMessage(stage, model=null) { if(!PROVIDER_PROGRESS_STAGES.has(stage))return null; const suffix=validModel(model)?` · ${model}`:''; const messages={model_selected:`Provider stage · model selected${suffix}`,request_dispatched:`Provider stage · request dispatched${suffix}`,response_received:`Provider stage · response received${suffix}`,protocol_rejected:`Provider stage · response rejected by RESIDUAL protocol${suffix}`,envelope_decoded:`Provider stage · envelope decoded${suffix}`}; return messages[stage]; }
export function textReply(result) { if(typeof result==='string')return result; const content=result?.message?.content??result?.text??result?.content; if(typeof content==='string')return content; if(Array.isArray(content))return content.map(p=>typeof p==='string'?p:(p?.text||'')).join(''); throw new ProviderProtocolError('content_missing'); }
export function validProtocolEnvelope(value) { if(!value||typeof value!=='object'||Array.isArray(value))return false; const keys=Object.keys(value).sort(); if(keys.length!==2||keys[0]!=='requests'||keys[1]!=='updates')return false; if(!value.updates||typeof value.updates!=='object'||Array.isArray(value.updates)||!Array.isArray(value.requests))return false; return value.requests.every(r=>r&&typeof r==='object'&&!Array.isArray(r)&&Object.keys(r).sort().join(',')==='artifact_id,end_line,obligation_id,start_line'&&typeof r.obligation_id==='string'&&typeof r.artifact_id==='string'&&Number.isInteger(r.start_line)&&r.start_line>=1&&Number.isInteger(r.end_line)&&r.end_line>=1); }
function unwrapJsonFence(text) { const trimmed=text.trim(); const fenced=trimmed.match(/^```(?:json)?\s*\r?\n([\s\S]*?)\r?\n```$/i); return fenced?fenced[1].trim():trimmed; }
function parseEnvelope(text,source='content') { if(typeof text!=='string'||!text.trim())throw new ProviderProtocolError(`${source}_empty`); let value; try{value=JSON.parse(unwrapJsonFence(text));}catch{throw new ProviderProtocolError(`${source}_not_json`);} if(!validProtocolEnvelope(value))throw new ProviderProtocolError('envelope_shape'); return JSON.stringify(value); }
export function protocolReply(result) { if(result?.finish_reason==='length')throw new ProviderProtocolError('response_truncated'); const calls=result?.message?.tool_calls; if(Array.isArray(calls)&&calls.length>0){if(calls.length!==1)throw new ProviderProtocolError('tool_call_count');if(calls[0]?.function?.name!=='residual_submit')throw new ProviderProtocolError('tool_name');const args=calls[0]?.function?.arguments;if(args===undefined||args===null||args==='')throw new ProviderProtocolError('tool_arguments_empty');return parseEnvelope(typeof args==='string'?args:JSON.stringify(args),'tool_arguments');} return parseEnvelope(textReply(result),'content'); }
export class ProviderSession {
  constructor(onState=()=>{}) { this.onState=onState;this.channel=null;this.pending=new Map();this.connected=false;this.lastSeen=0;this.grant=null;this.generation=0;this.sdk=null;this.sdkLoad=null;this.transport='tool'; }
  get ready(){return this.connected&&Date.now()-this.lastSeen<PROVIDER_LIVENESS_MS;}
  checkConnection(){if(this.connected&&!this.ready){this.connected=false;this.onState('disconnected','Provider tab has not responded recently. Reopen setup if it was closed; a suspended mobile tab can reconnect without changing provider authorization. No new requests are authorized while disconnected.');}}
  async open(){
    if(!this.sdk?.auth){
      this.onState('loading','Step 1 of 3 · loading the Puter provider inside Mission Control…');
      this.sdkLoad ||= new Promise((resolve,reject)=>{
        const existing=document.querySelector('script[data-residual-puter-sdk="1"]');
        if(existing&&window.puter?.auth)return resolve(window.puter);
        const script=existing||document.createElement('script');script.src='https://js.puter.com/v2/';script.async=true;script.dataset.residualPuterSdk='1';
        const timer=setTimeout(()=>reject(new Error('sdk_load_timeout')),10000);
        script.onload=()=>{clearTimeout(timer);window.puter?.auth&&window.puter?.ai?resolve(window.puter):reject(new Error('sdk_unavailable'));};
        script.onerror=()=>{clearTimeout(timer);reject(new Error('sdk_load_failed'));};
        if(!existing)document.head.append(script);
      });
      try{this.sdk=await this.sdkLoad;}catch(error){this.sdkLoad=null;this.onState('error','Puter could not load. Check content blockers or network access, then retry. No prompt was sent.');throw error;}
      if(!this.sdk.auth.isSignedIn?.()){this.onState('loaded','Step 1 complete · Puter is loaded. Click “Authorize Puter” to continue in its secure popup.');return false;}
    }
    this.onState('authorizing','Step 2 of 3 · authorize Puter in its secure popup. Mission Control stays open here.');
    if(!this.sdk.auth.isSignedIn?.())await this.sdk.auth.signIn({attempt_temp_user_creation:false});
    if(!this.sdk.auth.isSignedIn?.())throw new Error('not_signed_in');
    this.connected=true;this.lastSeen=Date.now();
    this.onState('connected','Step 3 of 3 · Puter connected. Review the prompt authorization checkbox, then run the mission.');
    return true;
  }
  receive(message){if(!message||message.protocol!==PROTOCOL||!bounded(message))return;this.lastSeen=Date.now();if(message.kind==='state'){this.connected=message.connected===true;this.onState(this.ready?'connected':'disconnected',this.ready?'Provider signed in. Model access and billing are checked on each run.':'Provider not signed in. Open setup to continue.');return;}if(message.kind==='progress'&&validRequest(message.request_id)&&validId(message.mission_id)){const entry=this.pending.get(message.request_id),text=providerProgressMessage(message.stage,message.model);if(entry&&entry.missionId===message.mission_id&&text)this.onState(this.ready?'connected':'disconnected',text,{kind:'provider_progress',stage:message.stage,mission_id:message.mission_id,request_id:message.request_id,model:validModel(message.model)?message.model:null});return;}if(message.kind==='response'&&validRequest(message.request_id)){const entry=this.pending.get(message.request_id);if(entry&&message.mission_id===entry.missionId){if(message.ok===false&&typeof message.error==='string')this.onState(this.ready?'connected':'disconnected',providerFailureMessage(message.error,message.detail));clearTimeout(entry.timer);this.pending.delete(message.request_id);entry.resolve(message);}}}
  begin(missionId,calls,model){if(!this.ready||!validId(missionId)||!validModel(model)||!Number.isInteger(calls)||calls<1||calls>3)throw new Error('Provider is not connected or budget is invalid.');this.grant={missionId,calls,model,used:0,seen:new Set()};this.channel?.postMessage({protocol:PROTOCOL,kind:'grant',mission_id:missionId,max_calls:calls,model});}
  async infer(missionId,req){
    const g=this.grant;if(!this.ready||!g||g.missionId!==missionId)return{ok:false,error:'provider_disconnected',request_id:req.request_id};
    if(!validInference(req)||req.model!==g.model||g.seen.has(req.request_id)||g.used>=g.calls)return{ok:false,error:'provider_budget_exhausted',request_id:req.request_id};
    g.used++;g.seen.add(req.request_id);
    if(!this.sdk?.ai)return new Promise(resolve=>{const timer=setTimeout(()=>{this.pending.delete(req.request_id);const response={ok:false,request_id:req.request_id,error:'provider_timeout'};this.onState(this.ready?'connected':'disconnected',providerFailureMessage(response.error));resolve(response);},85000);this.pending.set(req.request_id,{resolve,timer,missionId});this.channel?.postMessage({protocol:PROTOCOL,kind:'request',mission_id:missionId,...req});});
    const progress=stage=>this.onState('connected',providerProgressMessage(stage,req.model));
    const tools=[{type:'function',function:{name:'residual_submit',description:'Submit one RESIDUAL worker envelope with exactly updates and requests.',parameters:RESPONSE_SCHEMA}}];
    const jsonNote='\n\nReturn exactly one raw JSON object with exactly two top-level keys: updates and requests. Return no prose, Markdown, or additional keys.';
    const messages=this.transport==='tool'?req.messages:req.messages.map((m,i)=>i===0&&m.role==='system'?{...m,content:m.content+jsonNote}:m);
    const options={model:req.model,max_tokens:req.max_output_tokens,stream:false,normalize:true};if(this.transport==='tool')options.tools=tools;
    let timer;
    try{progress('model_selected');progress('request_dispatched');const result=await Promise.race([this.sdk.ai.chat(messages,options),new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('provider_timeout')),80000)})]);progress('response_received');let text;try{text=protocolReply(result)}catch(error){this.transport=providerTransportAfterFailure(this.transport,'provider_protocol_invalid');progress('protocol_rejected');return{ok:false,error:'provider_protocol_invalid',detail:protocolFailureReason(error),request_id:req.request_id}}progress('envelope_decoded');const usage=result?.usage||{};return{ok:true,text,request_id:req.request_id,usage:{input_tokens:Number.isInteger(usage.input_tokens??usage.prompt_tokens)?(usage.input_tokens??usage.prompt_tokens):null,output_tokens:Number.isInteger(usage.output_tokens??usage.completion_tokens)?(usage.output_tokens??usage.completion_tokens):null}}}catch(error){const raw=String(error?.error||error?.code||error?.message||'').toLowerCase();const code=raw.includes('timeout')?'provider_timeout':raw.includes('model')?'provider_model_unavailable':raw.match(/auth|permission|forbidden|billing|credit|quota|401|403/)?'provider_authorization_failed':'provider_request_failed';this.onState('connected',providerFailureMessage(code));return{ok:false,error:code,request_id:req.request_id}}finally{clearTimeout(timer)}
  }
  end(){this.grant=null;for(const[id,entry]of this.pending){clearTimeout(entry.timer);entry.resolve({ok:false,request_id:id,error:'mission_cancelled'});}this.pending.clear();this.channel?.postMessage({protocol:PROTOCOL,kind:'revoke'});}
  close(){this.end();this.channel?.close();this.channel=null;this.connected=false;this.lastSeen=0;this.generation++;}
}
