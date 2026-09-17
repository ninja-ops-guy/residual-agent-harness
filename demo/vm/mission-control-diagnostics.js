import {mountMissionControl as mountWorld} from './mission-control-world.js';

export const DIAGNOSTIC_PROTOCOL = 'residual.diagnostic.v1';
export const DIAGNOSTIC_SCHEMA_VERSION = '1.0';
export const MAX_EVENTS = 5000;
export const MAX_PERSIST_BYTES = 1024 * 1024;
const SESSION_KEY = 'residual.demo.diagnostic.session.v1';
const BUFFER_KEY = 'residual.demo.diagnostic.buffer.v1';
const EVENT_TYPE = /^[a-z][a-z0-9_]*\.[a-z0-9_]+$/;
const MISSION_ID = /^m-[a-f0-9]{32}$/;
const REQUEST_ID = /^[a-f0-9]{32}$/;
const SAFE_CONTEXT_KEYS = new Set([
  'attempt','browser','cross_origin_isolated','duration_ms','error_message','error_name',
  'evidence_count','evidence_kind','execution','failure_code','from','health','http_status',
  'max_attempts','max_output_tokens','message_kind','mission_id','mode','model','online',
  'platform','request_id','run_status','sequence','stage','status','to','visibility'
]);
const SECRET_PATTERNS = [
  /\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]+/gi,
  /\b(?:sk|pk|api)[-_][A-Za-z0-9_-]{12,}\b/g,
  /([?&](?:token|key|secret|auth|code)=)[^&#\s]+/gi,
  /\b[A-Fa-f0-9]{64,}\b/g
];
const FAILURE_MAP = new Map([
  ['provider_timeout','ProviderTimeout'],
  ['provider_model_unavailable','ProviderUnavailable'],
  ['provider_authorization_failed','ProviderUnavailable'],
  ['provider_request_failed','ProviderUnavailable'],
  ['provider_error','ProviderUnavailable'],
  ['provider_disconnected','ProviderUnavailable'],
  ['provider_protocol_invalid','ProviderProtocolFailure'],
  ['provider_response_too_large','ProviderProtocolFailure'],
  ['provider_budget_exhausted','ProviderBudgetFailure'],
  ['browser_response_invalid','BrowserLifecycleFailure'],
  ['service_worker_failure','ServiceWorkerFailure'],
  ['runtime_initialization_failure','RuntimeInitializationFailure'],
  ['runtime_corruption','RuntimeCorruption'],
  ['worker_startup_failure','WorkerStartupFailure'],
  ['worker_termination','WorkerTermination'],
  ['evidence_publication_failure','EvidencePublicationFailure'],
  ['network_failure','NetworkFailure'],
  ['ui_state_failure','UIStateFailure'],
  ['schema_failure','SchemaFailure'],
  ['mission_cancelled','MissionCancelled']
]);

function nowIso(){ return new Date().toISOString(); }
function mono(){ try{return Math.round(performance.now()*1000)/1000}catch{return 0} }
function randomId(prefix){
  try{return `${prefix}_${crypto.randomUUID().replaceAll('-','')}`}
  catch{return `${prefix}_${Date.now().toString(16)}${Math.random().toString(16).slice(2)}`}
}
function cleanString(value, limit=240){
  let text=String(value ?? '').replace(/[\r\n\t]+/g,' ').slice(0,limit);
  for(const pattern of SECRET_PATTERNS) text=text.replace(pattern, match=>match.includes('=')?match.split('=')[0]+'=[REDACTED]':'[REDACTED]');
  try{
    text=text.replace(/https?:\/\/[^\s]+/gi, raw=>{const u=new URL(raw); return `${u.origin}${u.pathname}`;});
  }catch{}
  return text;
}
export function sanitizeContext(input){
  if(!input || typeof input!=='object' || Array.isArray(input)) return {};
  const out={};
  for(const [key,value] of Object.entries(input)){
    if(!SAFE_CONTEXT_KEYS.has(key) || value===undefined || value===null) continue;
    if(typeof value==='boolean' || (typeof value==='number' && Number.isFinite(value))){out[key]=value;continue;}
    if(typeof value!=='string') continue;
    if(key==='mission_id' && !MISSION_ID.test(value)) continue;
    if(key==='request_id' && !REQUEST_ID.test(value)) continue;
    out[key]=cleanString(value,key==='error_message'?240:120);
  }
  return out;
}
export function classifyFailure(value){
  const code=typeof value==='string'?value:(value?.code||value?.error||value?.name||'');
  if(FAILURE_MAP.has(code)) return FAILURE_MAP.get(code);
  const lower=String(code).toLowerCase();
  if(lower.includes('timeout')) return 'ProviderTimeout';
  if(lower.includes('serviceworker')||lower.includes('service_worker')) return 'ServiceWorkerFailure';
  if(lower.includes('network')||lower.includes('fetch')) return 'NetworkFailure';
  if(lower.includes('worker')) return 'WorkerTermination';
  if(lower.includes('runtime')) return 'RuntimeInitializationFailure';
  return 'UnknownFailure';
}
function failureCode(data){
  const direct=data?.failure_code||data?.error||data?.code;
  if(typeof direct==='string') return cleanString(direct,80);
  const unresolved=data?.result?.unresolved;
  if(unresolved && typeof unresolved==='object'){
    for(const value of Object.values(unresolved)) if(value && typeof value==='object' && typeof value.code==='string') return cleanString(value.code,80);
  }
  return null;
}
function componentFor(type){ return type.split('.',1)[0]; }
function safeStorage(kind){
  try{return kind==='session'?sessionStorage:null}catch{return null}
}
export class DiagnosticBuffer {
  constructor(maxEvents=MAX_EVENTS){this.maxEvents=maxEvents;this.events=[];}
  push(event){this.events.push(event);if(this.events.length>this.maxEvents)this.events.splice(0,this.events.length-this.maxEvents);}
  snapshot(){return this.events.slice();}
}

export class DemoDiagnostics {
  constructor(){
    this.buffer=new DiagnosticBuffer(); this.runByMission=new Map(); this.latestRunId=null;
    this.release={commit:null,webvm_commit:null}; this.lastHealth=null; this.lastUi=new Map();
    const storage=safeStorage('session');
    let sessionId=null;
    try{sessionId=storage?.getItem(SESSION_KEY)}catch{}
    this.sessionId=/^ses_[a-f0-9]+$/.test(sessionId||'')?sessionId:randomId('ses');
    try{storage?.setItem(SESSION_KEY,this.sessionId)}catch{}
    this.restore();
    this.environment=this.captureEnvironment();
    this.emit('session.started',{status:'started'});
    this.attachLifecycle();
    this.loadBuildInfo();
  }
  captureEnvironment(){
    let browser='unknown',platform='unknown';
    try{browser=cleanString(navigator.userAgent,180);platform=cleanString(navigator.platform||'unknown',80)}catch{}
    return {browser,platform,online:typeof navigator==='undefined'?null:navigator.onLine,visibility:typeof document==='undefined'?'unknown':document.visibilityState,cross_origin_isolated:globalThis.crossOriginIsolated===true};
  }
  restore(){
    const storage=safeStorage('session'); if(!storage)return;
    try{
      const value=JSON.parse(storage.getItem(BUFFER_KEY)||'null');
      if(!value||value.session_id!==this.sessionId||!Array.isArray(value.events))return;
      for(const event of value.events.slice(-MAX_EVENTS)) if(event&&event.schema_version===DIAGNOSTIC_SCHEMA_VERSION)this.buffer.push(event);
    }catch{}
  }
  persist(){
    const storage=safeStorage('session'); if(!storage)return;
    try{
      let events=this.buffer.snapshot(); let text=JSON.stringify({session_id:this.sessionId,events});
      while(text.length>MAX_PERSIST_BYTES && events.length>1){events=events.slice(Math.max(1,Math.floor(events.length/8)));text=JSON.stringify({session_id:this.sessionId,events});}
      storage.setItem(BUFFER_KEY,text);
    }catch{}
  }
  emit(eventType,context={},options={}){
    try{
      if(!EVENT_TYPE.test(eventType))return null;
      const missionId=MISSION_ID.test(options.mission_id||'')?options.mission_id:null;
      const runId=options.run_id|| (missionId?this.runByMission.get(missionId):null) || null;
      const failureClass=options.failure_class||null;
      const event={
        schema_version:DIAGNOSTIC_SCHEMA_VERSION,event_id:randomId('evt'),trace_id:runId||this.sessionId,
        parent_event_id:null,session_id:this.sessionId,run_id:runId,mission_id:missionId,
        timestamp:nowIso(),monotonic_ms:mono(),component:componentFor(eventType),event_type:eventType,
        severity:['debug','info','warn','error'].includes(options.severity)?options.severity:'info',
        release:{...this.release},context:sanitizeContext(context)
      };
      if(failureClass)event.diagnostic={failure_class:failureClass,recoverable:options.recoverable===true};
      this.buffer.push(event);this.persist();return event;
    }catch{return null}
  }
  startRun(missionId,mode){
    if(!MISSION_ID.test(missionId||''))return null;
    const runId=randomId('run');this.runByMission.set(missionId,runId);this.latestRunId=runId;
    this.emit('mission.submitted',{mode,mission_id:missionId},{mission_id:missionId,run_id:runId});return runId;
  }
  attachLifecycle(){
    try{document.addEventListener('visibilitychange',()=>this.emit('browser.visibility_changed',{visibility:document.visibilityState}));}catch{}
    try{window.addEventListener('online',()=>this.emit('browser.online',{online:true}));window.addEventListener('offline',()=>this.emit('browser.offline',{online:false}));}catch{}
    try{window.addEventListener('error',event=>this.emit('ui.unhandled_error',{error_name:event.error?.name||'Error',error_message:event.error?.message||event.message||'window error'},{severity:'error',failure_class:classifyFailure(event.error)}));}catch{}
    try{window.addEventListener('unhandledrejection',event=>this.emit('ui.unhandled_rejection',{error_name:event.reason?.name||'PromiseRejection',error_message:event.reason?.message||String(event.reason||'unhandled rejection')},{severity:'error',failure_class:classifyFailure(event.reason)}));}catch{}
    try{navigator.serviceWorker?.addEventListener('message',event=>{const data=event.data;if(!data||data.protocol!==DIAGNOSTIC_PROTOCOL||!EVENT_TYPE.test(data.event_type||''))return;this.emit(data.event_type,data.context||{},{severity:data.severity||'warn',failure_class:data.failure_class||null,recoverable:data.recoverable===true});});}catch{}
  }
  async loadBuildInfo(){
    try{
      const response=await fetch('./build-info.json',{cache:'no-store'}); if(!response.ok)return;
      const info=await response.json();
      if(typeof info.commit==='string')this.release.commit=cleanString(info.commit,64);
      if(typeof info.webvm_commit==='string')this.release.webvm_commit=cleanString(info.webvm_commit,64);
      this.emit('environment.probed',{browser:this.environment.browser,platform:this.environment.platform,online:this.environment.online,visibility:this.environment.visibility,cross_origin_isolated:this.environment.cross_origin_isolated});
    }catch{}
  }
  wrapHost(host){
    const diagnostics=this;
    return {...host,
      ready(){try{return host.ready()}catch(error){diagnostics.emit('runtime.ready_probe_failed',{error_name:error?.name||'Error',error_message:error?.message||'ready probe failed'},{severity:'error',failure_class:classifyFailure(error)});throw error}},
      health(){const value=host.health();if(value!==diagnostics.lastHealth){diagnostics.emit('runtime.health_changed',{from:diagnostics.lastHealth||'unknown',to:value,health:value},{severity:value==='poisoned'?'error':'info',failure_class:value==='poisoned'?'RuntimeCorruption':null});diagnostics.lastHealth=value;}return value;},
      restart(){diagnostics.emit('recovery.guest_restart_requested',{status:'requested'});try{return host.restart()}catch(error){diagnostics.emit('recovery.guest_restart_failed',{error_name:error?.name||'Error',error_message:error?.message||'restart failed'},{severity:'error',failure_class:classifyFailure(error)});throw error}},
      focus(){return host.focus()},
      async mailbox(path,text){const messageKind=String(path).endsWith('-cancel.json')?'cancel':'provider_response';diagnostics.emit('provider.mailbox_write_started',{message_kind:messageKind});try{const value=await host.mailbox(path,text);diagnostics.emit('provider.mailbox_write_completed',{message_kind:messageKind});return value}catch(error){diagnostics.emit('provider.mailbox_write_failed',{message_kind:messageKind,error_name:error?.name||'Error',error_message:error?.message||'mailbox write failed'},{severity:'error',failure_class:'ProviderUnavailable'});throw error}},
      async run(request){const runId=diagnostics.startRun(request?.id,request?.mode);const started=mono();diagnostics.emit('mission.host_run_started',{mode:request?.mode},{mission_id:request?.id,run_id:runId});try{const value=await host.run(request);diagnostics.emit('mission.host_run_completed',{duration_ms:Math.max(0,mono()-started),run_status:String(value?.status??'unknown')},{mission_id:request?.id,run_id:runId});return value}catch(error){diagnostics.emit('mission.host_run_failed',{duration_ms:Math.max(0,mono()-started),error_name:error?.name||'Error',error_message:error?.message||'host run failed'},{mission_id:request?.id,run_id:runId,severity:'error',failure_class:classifyFailure(error)});throw error}}
    };
  }
  consumeFrame(frame){
    try{
      if(!frame||!MISSION_ID.test(frame.mission_id||''))return;
      const mid=frame.mission_id;if(!this.runByMission.has(mid)&&frame.kind==='mission_started')this.startRun(mid,'external');
      const runId=this.runByMission.get(mid)||null,data=frame.data||{};
      if(frame.kind==='mission_started')this.emit('mission.started',{status:'running'},{mission_id:mid,run_id:runId});
      else if(frame.kind==='evidence')this.emit('evidence.projected',{sequence:Number.isInteger(data.seq)?data.seq:-1,evidence_kind:typeof data.kind==='string'?data.kind:'unknown'},{mission_id:mid,run_id:runId});
      else if(frame.kind==='inference_requested')this.emit('provider.request_requested',{request_id:REQUEST_ID.test(data.request_id||'')?data.request_id:undefined,model:typeof data.model==='string'?data.model:undefined,max_output_tokens:Number.isInteger(data.max_output_tokens)?data.max_output_tokens:undefined},{mission_id:mid,run_id:runId});
      else if(frame.kind==='mission_error'){const code=failureCode(data)||'mission_error';this.emit('mission.failed',{failure_code:code,status:'error'},{mission_id:mid,run_id:runId,severity:'error',failure_class:classifyFailure(code)});}
      else if(frame.kind==='mission_finished'){const code=failureCode(data);const failed=data.status!=='passed';this.emit('mission.finished',{status:String(data.status||'unknown'),execution:String(data.execution||'unknown'),evidence_count:Number.isInteger(data.result?.metrics?.evidence_events)?data.result.metrics.evidence_events:undefined,failure_code:code||undefined},{mission_id:mid,run_id:runId,severity:failed?'warn':'info',failure_class:failed?classifyFailure(code||'mission_error'):null});}
    }catch{}
  }
  consumeOutput(text){
    const prefix='\x1b]777;RESIDUAL;';let cursor=0;
    while(typeof text==='string'){
      const start=text.indexOf(prefix,cursor);if(start<0)return;const end=text.indexOf('\x07',start+prefix.length);if(end<0)return;
      try{const raw=text.slice(start+prefix.length,end).replace(/-/g,'+').replace(/_/g,'/');const bin=atob(raw);this.consumeFrame(JSON.parse(new TextDecoder().decode(Uint8Array.from(bin,c=>c.charCodeAt(0)))));}catch{}
      cursor=end+1;
    }
  }
  uiCode(id,text){
    const lower=String(text||'').toLowerCase();
    if(id==='mc-runtime'){if(lower.includes('failed')||lower.includes('poison'))return 'guest_failed';if(lower.includes('ready'))return 'guest_ready';if(lower.includes('restart'))return 'guest_restarting';return 'guest_starting';}
    if(id==='mc-provider-state'){if(lower.includes('signed in')||lower.includes('stage'))return 'provider_connected';if(lower.includes('stopped responding')||lower.includes('lost'))return 'provider_disconnected';if(lower.includes('fail')||lower.includes('timed out')||lower.includes('unavailable'))return 'provider_failure';return 'provider_waiting';}
    if(id==='mc-run-state'){if(lower.includes('waiting for a mission'))return 'run_idle';if(lower.includes('provider response'))return 'provider_wait';if(lower.includes('passed'))return 'run_passed';if(lower.includes('fail')||lower.includes('blocked'))return 'run_failed';if(lower.includes('working'))return 'run_working';return 'run_active';}
    return 'unknown';
  }
  observeUi(root){
    try{
      const ids=['mc-runtime','mc-provider-state','mc-run-state'];
      const update=node=>{const code=this.uiCode(node.id,node.textContent);if(this.lastUi.get(node.id)===code)return;this.lastUi.set(node.id,code);this.emit('ui.state_changed',{stage:node.id,status:code});};
      for(const id of ids){const node=root.querySelector('#'+id);if(!node)continue;update(node);new MutationObserver(()=>update(node)).observe(node,{childList:true,subtree:true,characterData:true});}
    }catch{}
  }
  attachDownload(root){
    try{
      const header=root.querySelector('header');if(!header||header.querySelector('#mc-diagnostics'))return;
      const button=document.createElement('button');button.type='button';button.id='mc-diagnostics';button.textContent='Download diagnostics';button.title='Download privacy-sanitized local diagnostic trace';
      button.onclick=()=>this.download(this.latestRunId);const runtime=header.querySelector('#mc-runtime');header.insertBefore(button,runtime||null);
    }catch{}
  }
  bundle(runId=null){
    const events=this.buffer.snapshot().filter(event=>!runId||event.run_id===runId||event.run_id===null);
    return {manifest:{schema_version:DIAGNOSTIC_SCHEMA_VERSION,generated_at:nowIso(),session_id:this.sessionId,run_id:runId,release:{...this.release},authoritative_execution_evidence:false,privacy:'sanitized-local-diagnostic-only'},environment:{...this.environment},events};
  }
  download(runId=null){
    try{const bundle=this.bundle(runId),blob=new Blob([JSON.stringify(bundle,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`residual-diagnostic-${runId||this.sessionId}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);this.emit('diagnostic.bundle_downloaded',{status:'complete'});return true}catch{return false}
  }
}

let singleton=null;
export function getDemoDiagnostics(){if(!singleton)singleton=new DemoDiagnostics();return singleton;}
export function mountMissionControl(host){
  const diagnostics=getDemoDiagnostics();
  const base=mountWorld(diagnostics.wrapHost(host));
  try{const root=document.querySelector('#mission-control');if(root){diagnostics.attachDownload(root);diagnostics.observeUi(root);}}
  catch{}
  try{globalThis.__residualDiagnostics=diagnostics}catch{}
  return {onOutput(text){try{diagnostics.consumeOutput(text)}catch{}return base.onOutput(text)},connectProvider:base.connectProvider,destroy(){try{diagnostics.emit('session.ui_destroyed',{status:'destroyed'})}catch{}return base.destroy()}};
}
