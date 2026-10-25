import {mountMissionControl as mountBase} from './mission-control-engineer.js';
import {renderEvidenceEvent, verifyEvidenceChain} from './mission-control.js';
import {renderPreview} from './mission-preview.js';

const CURRENT='residual.chat.current.v2', INDEX='residual.chat.index.v2';
const EVIDENCE_PREFIX='residual.chat.evidence.v1.', EVIDENCE_LIMIT=300000;
const evKey=id=>EVIDENCE_PREFIX+id;
const cid=()=> 'c-'+crypto.randomUUID().replaceAll('-','');
const validCid=value=>/^c-[a-f0-9]{32}$/.test(value||'');
const validMid=value=>/^m-[a-f0-9]{32}$/.test(value||'');
const key=id=>'residual.chat.session.v2.'+id;
function readJson(name,fallback){try{return JSON.parse(localStorage.getItem(name)||'null')??fallback}catch{return fallback}}
function fresh(id=cid()){return {version:2,id,turns:[],lastBuildMission:null,continueFrom:null,lastBundle:null,revision:0}}
function safeBundle(bundle){if(!bundle||typeof bundle!=='object'||typeof bundle.summary!=='string'||bundle.summary.length>4000||!Array.isArray(bundle.files)||bundle.files.length<1||bundle.files.length>8)return null;let total=0;const files=[];for(const item of bundle.files){if(!item||typeof item.path!=='string'||typeof item.content!=='string'||!item.path||item.path.startsWith('/')||item.path.includes('\\')||item.path.split('/').some(p=>!p||p==='.'||p==='..'||p.startsWith('.')))return null;const bytes=new TextEncoder().encode(item.content).length;if(bytes>48000)return null;total+=bytes;if(total>128000)return null;files.push({path:item.path,content:item.content})}return {summary:bundle.summary,files}}
function safeTurn(turn){if(!turn||!['user','assistant','system'].includes(turn.role)||typeof turn.text!=='string'||turn.text.length>16000)return null;const mission_id=turn.mission_id==null?null:(validMid(turn.mission_id)?turn.mission_id:null);return {role:turn.role,text:turn.text,mission_id,status:typeof turn.status==='string'?turn.status:null,mode:typeof turn.mode==='string'?turn.mode:null}}
function load(id){const value=readJson(key(id),null);if(!value||value.version!==2||value.id!==id||!Array.isArray(value.turns))return fresh(id);const turns=value.turns.slice(-16).map(safeTurn).filter(Boolean);const lastBuildMission=validMid(value.lastBuildMission)?value.lastBuildMission:null;const lastBundle=safeBundle(value.lastBundle);const continuation=validMid(value.continueFrom)?value.continueFrom:null;const revision=Number.isInteger(value.revision)&&value.revision>=0&&value.revision<=16?value.revision:0;return {version:2,id,turns,lastBuildMission,continueFrom:continuation,lastBundle,revision}}
function index(){const value=readJson(INDEX,[]);return (Array.isArray(value)?value:[]).filter(x=>validCid(x?.id)).slice(0,8).map(x=>({id:x.id,title:typeof x.title==='string'?x.title.slice(0,42):x.id.slice(-6),updated:Number.isFinite(x.updated)?x.updated:0}))}
export function clearLocalConversation(id,{evidenceOnly=false}={}){
  if(!validCid(id))return false;
  let ok=true;
  for(const name of evidenceOnly?[evKey(id)]:[evKey(id),key(id)]){
    try{localStorage.removeItem(name)}catch{ok=false}
  }
  if(!evidenceOnly){try{localStorage.setItem(INDEX,JSON.stringify(index().filter(x=>x.id!==id)));if(localStorage.getItem(CURRENT)===id)localStorage.removeItem(CURRENT)}catch{ok=false}}
  return ok;
}
export function loadEvidence(id){
  try{
    const text=localStorage.getItem(evKey(id));
    if(!text||text.length>EVIDENCE_LIMIT)return null;
    const value=JSON.parse(text);
    if(!validMid(value?.mission_id)||!Array.isArray(value.frames)||value.frames.length>300||!value.frames.every(x=>typeof x==='string'))return null;
    return value;
  }catch{return null}
}
export function storeEvidence(id,payload){
  // Never leave a previous mission looking like the latest successful save.
  if(!clearLocalConversation(id,{evidenceOnly:true}))return false;
  let text=JSON.stringify(payload);
  while(payload.frames.length&&text.length>EVIDENCE_LIMIT){payload.frames.pop();payload.truncated=true;text=JSON.stringify(payload)}
  if(!payload.frames.length)return false;
  try{localStorage.setItem(evKey(id),text);return true}catch{return false}
}
function save(state,title){try{localStorage.setItem(key(state.id),JSON.stringify(state));localStorage.setItem(CURRENT,state.id);const items=index().filter(x=>x.id!==state.id);items.unshift({id:state.id,title:(title||state.turns.find(t=>t.role==='user')?.text||'New conversation').slice(0,42),updated:Date.now()});localStorage.setItem(INDEX,JSON.stringify(items.slice(0,8)));for(const old of items.slice(8))clearLocalConversation(old.id)}catch{}}
function append(state,turn){const safe=safeTurn(turn);if(!safe)return;state.turns.push(safe);state.turns=state.turns.slice(-16);save(state)}
function bubble(root,kind,text){const node=document.createElement('div');node.className=`bubble ${kind}`;const meta=document.createElement('span');meta.className='meta';meta.textContent=kind==='user'?'YOU':kind==='assistant'?'RESIDUAL':'SYSTEM';const body=document.createElement('div');body.textContent=text;node.append(meta,body);root.append(node);return node}
function parseFrames(text,consume){const prefix='\x1b]777;RESIDUAL;';let cursor=0;while(true){const start=text.indexOf(prefix,cursor);if(start<0)return;const end=text.indexOf('\x07',start+prefix.length);if(end<0)return;try{const raw=text.slice(start+prefix.length,end).replace(/-/g,'+').replace(/_/g,'/');const bin=atob(raw);const decoded=new TextDecoder().decode(Uint8Array.from(bin,c=>c.charCodeAt(0)));consume(JSON.parse(decoded),decoded)}catch{}cursor=end+1}}
function failureText(data){const values=Object.values(data?.result?.unresolved||{});const item=values.find(v=>v&&typeof v==='object')||{};const code=item.code||'no_verified_candidate';const map={provider_exception:'provider adapter exception',provider_error:'provider request failed',provider_request_failed:'provider request failed',provider_model_unavailable:'selected model unavailable',provider_authorization_failed:'provider authorization/allowance failed',provider_protocol_invalid:'provider response violated the worker protocol',provider_timeout:'provider request timed out',browser_response_invalid:'browser-to-guest provider response was invalid',provider_budget_exhausted:'provider call budget exhausted',invalid_protocol:'provider response violated the worker protocol'};return `Build blocked — no artifact was accepted. Cause: ${map[code]||code}. Open Activity for what happened/why and Evidence for the retained result.`}

export function mountMissionControl(host){
  try{document.title='RESIDUAL \u00b7 Mission Control';}catch{}
  const evidenceFrames=new Map(), truncatedMissions=new Set();
  let evidenceGeneration=0;
  let id;try{id=localStorage.getItem(CURRENT)}catch{}if(!validCid(id))id=cid();
  let state=load(id), pending=new Set(), busy=false, setBusy=()=>{};
  const wrapped={...host,run:async request=>{let next={...request};if(request.mode==='build'){const previous=document.querySelector('#mc-inline-preview-frame');if(previous)previous.id=`mc-inline-preview-frame-r${Math.max(1,state.revision)}`;next.conversation_id=state.id;if(state.continueFrom)next.parent_mission_id=state.continueFrom;}pending.add(request.id);append(state,{role:'user',text:request.prompt,mission_id:request.id,mode:request.mode});setBusy(true);queueMicrotask(()=>{const prompt=document.querySelector('#mc-prompt'),controls=document.querySelector('#mc-composer details');if(prompt&&prompt.value===request.prompt)prompt.value='';if(controls)controls.open=false});try{return await host.run(next)}catch(error){pending.delete(request.id);setBusy(false);throw error}}};
  const base=mountBase(wrapped), root=document.querySelector('#mission-control'), chat=root.querySelector('#mc-chat'), header=root.querySelector('header');
  const session=document.createElement('span');session.className='muted';session.id='mc-session';
  const history=document.createElement('select');history.id='mc-history';history.title='Conversation history';
  const detach=document.createElement('button');detach.type='button';detach.id='mc-detach';detach.textContent='Fresh artifact';
  const create=document.createElement('button');create.type='button';create.id='mc-new-chat';create.textContent='New chat';
  header.insertBefore(session,header.querySelector('#mc-connect'));header.insertBefore(history,session);header.insertBefore(detach,history);header.insertBefore(create,detach);
  const privacy=document.createElement('div');privacy.className='notice';
  const disclosure=document.createElement('p');disclosure.textContent='Browser evidence may contain your exact goal, source excerpts, provider packet, model response, verification messages and accepted values. Saved evidence remains on this browser profile until cleared or its conversation is evicted; there is no automatic expiration. Anyone using this profile may inspect it. Chat transcripts and previews are saved separately. New chat and Fresh artifact do not delete history. Clearing here does not delete guest trace.jsonl, Terminal output, downloads or provider records.';
  const rememberLabel=document.createElement('label'),remember=document.createElement('input');remember.type='checkbox';remember.id='mc-remember-evidence';rememberLabel.append(remember,document.createTextNode(' Save evidence for this conversation on this browser (optional; off on each visit).'));
  const clear=document.createElement('button');clear.type='button';clear.id='mc-clear-evidence';clear.textContent='Clear this chat’s browser evidence';
  const remove=document.createElement('button');remove.type='button';remove.id='mc-delete-chat';remove.textContent='Delete this browser conversation';
  const notice=document.createElement('p');notice.id='mc-retention-status';notice.setAttribute('role','status');
  privacy.append(disclosure,rememberLabel,clear,remove,notice);root.querySelector('#mc-composer').prepend(privacy);
  function clearProjection(){evidenceGeneration++;evidenceFrames.clear();truncatedMissions.clear();base.clearEvidence();clearBackground()}
  clear.onclick=()=>{if(busy)return;remember.checked=false;const ok=clearLocalConversation(state.id,{evidenceOnly:true});clearProjection();notice.textContent=ok?'Browser evidence cleared. Chat, guest traces and other copies remain.':'Browser storage deletion failed. Clear this site’s data in browser settings before sharing this profile.'};
  remove.onclick=()=>{if(busy)return;if(!clearLocalConversation(state.id)){notice.textContent='Conversation deletion failed. Clear this site’s data in browser settings before sharing this profile.';return}clearProjection();remember.checked=false;state=fresh();restore();notice.textContent='Browser conversation and evidence deleted. Guest traces and other copies remain.'};
  function status(){clear.disabled=busy;remove.disabled=busy;remember.disabled=busy;session.textContent=`CHAT ${state.id.slice(-6)} · ${state.continueFrom?'REV '+state.revision:'FRESH'}`;create.disabled=busy;history.disabled=busy;detach.disabled=busy||!state.continueFrom}
  setBusy=value=>{busy=!!value;status()};
  function fillHistory(){history.replaceChildren();for(const item of index()){const o=document.createElement('option');o.value=item.id;o.textContent=item.title||item.id.slice(-6);o.selected=item.id===state.id;history.append(o)}if(![...history.options].some(o=>o.value===state.id)){const o=document.createElement('option');o.value=state.id;o.textContent='Current chat';o.selected=true;history.prepend(o)}}
  function clearBackground(){const result=root.querySelector('#mc-result'),artifacts=root.querySelector('#mc-artifacts'),events=root.querySelector('#mc-events'),count=root.querySelector('#mc-count'),runState=root.querySelector('#mc-run-state'),preview=root.querySelector('#mc-preview'),previewStatus=root.querySelector('#mc-preview-status');if(result)result.hidden=true;if(artifacts)artifacts.hidden=true;if(events)events.replaceChildren();if(count)count.textContent='0';if(runState)runState.textContent='Browser-local conversation restored. Guest traces remain authoritative evidence.';if(preview){preview.hidden=true;preview.replaceChildren()}if(previewStatus)previewStatus.textContent='No live mission preview yet.'}
  function restoreEvidence(){
    const panel=root.querySelector('#mc-events'),count=root.querySelector('#mc-count');if(!panel)return;
    const generation=++evidenceGeneration;
    const stored=loadEvidence(state.id);
    if(!stored||!Array.isArray(stored.frames)||!stored.frames.length||!validMid(stored.mission_id))return;
    let rendered=0;
    for(const frame of stored.frames){try{const event=JSON.parse(frame);if(event?.kind!=='evidence'||!event.data||event.mission_id!==stored.mission_id)continue;panel.append(renderEvidenceEvent(event.data));rendered++}catch{}}
    if(!rendered)return;
    if(count)count.textContent=String(rendered);
    const note=document.createElement('p');note.className='muted';note.textContent=`Restored browser-local evidence projection for mission ${stored.mission_id} \u00b7 the guest trace remains authoritative.`;panel.prepend(note);
    verifyEvidenceChain(stored.frames,stored.mission_id,stored.truncated?null:stored.trace_root).then(proof=>{
      if(generation!==evidenceGeneration)return;
      const verdict=document.createElement('p');verdict.className='mc-ev-chain';
      verdict.textContent=proof.ok
        ?`Restored chain re-verified in this browser: ${proof.count} events \u00b7 head ${proof.head.slice(0,12)}\u2026${stored.truncated?' \u00b7 projection truncated for storage; guest trace.jsonl holds the complete chain':stored.trace_root?' \u00b7 matches the recorded result root \u2713':''}`
        :`Restored projection could not be re-verified (${proof.reason}) \u00b7 rely on the retained guest trace`;
      panel.append(verdict);
    });
  }
  function restore(){clearBackground();chat.replaceChildren();const prompt=root.querySelector('#mc-prompt');if(prompt)prompt.value='';if(!state.turns.length)bubble(chat,'assistant','Give the harness a job. Follow up naturally; accepted build artifacts stay attached to this conversation until you detach them or start a new chat.');for(const turn of state.turns){const node=bubble(chat,turn.role,turn.text);if(turn.role==='assistant'&&turn.mission_id===state.lastBuildMission&&state.lastBundle){const shell=document.createElement('div');shell.className='preview-shell';node.append(shell);renderPreview(shell,state.lastBundle,{frameId:'mc-restored-preview-frame'});const note=document.createElement('div');note.className='muted';note.textContent='Restored browser-local preview cache · verify guest Evidence/Terminal before treating it as authoritative.';node.append(note)}}if(state.turns.length)bubble(chat,'system','Session transcript restored from this browser. Mission evidence and lineage authority remain in verified guest traces.');chat.scrollTop=chat.scrollHeight;status();fillHistory();restoreEvidence()}
  create.onclick=()=>{if(busy)return;clearProjection();remember.checked=false;state=fresh();pending.clear();save(state,'New conversation');restore()};
  detach.onclick=()=>{if(busy)return;state.continueFrom=null;save(state);status();bubble(chat,'system','Next build starts a fresh artifact while this conversation remains visible.')};
  history.onchange=()=>{if(busy||!validCid(history.value))return;clearProjection();remember.checked=false;state=load(history.value);pending.clear();save(state);restore()};
  restore();
  function persistEvidence(mid,status,traceRoot){
    const frames=evidenceFrames.get(mid)||[];evidenceFrames.delete(mid);
    const truncated=truncatedMissions.delete(mid);
    if(!remember.checked||!frames.length)return;
    const payload={mission_id:mid,status:status||null,trace_root:traceRoot||null,frames,truncated};
    notice.textContent=storeEvidence(state.id,payload)?'Evidence saved on this browser until cleared or conversation eviction.':'Evidence was not saved (storage unavailable or projection too large). Guest traces remain authoritative.';
  }
  function capture(event,rawText){
    if(!event||!pending.has(event.mission_id))return;
    if(event.kind==='evidence'){if(typeof rawText==='string'){const list=evidenceFrames.get(event.mission_id)||[];if(list.length<300){list.push(rawText);evidenceFrames.set(event.mission_id,list);}else truncatedMissions.add(event.mission_id);}return}
    if(event.kind==='mission_error'){persistEvidence(event.mission_id,'error',null);append(state,{role:'assistant',text:'Mission failed without a verified result. Open Activity for the failure explanation.',mission_id:event.mission_id,status:'INCOMPLETE'});pending.delete(event.mission_id);setBusy(false);fillHistory();return}
    if(event.kind!=='mission_finished')return;
    const data=event.data||{},build=data.execution==='generated_artifacts',bundle=data.result?.values?.build,accepted=build&&data.status==='passed'&&data.result?.success===true&&bundle&&Array.isArray(bundle.files)&&bundle.files.length>0;
    let text;
    if(accepted)text=bundle.summary||'Build completed with accepted generated files.';
    else if(build)text=failureText(data);
    else text=data.result?.values?.answer?.text;
    if(!text&&data.result?.values?.inventory)text='Repository audit completed with deterministic source inventory.';
    persistEvidence(event.mission_id,data.status,data.result?.trace_root);
    if(!text)text=data.status?`Mission ${String(data.status).toLowerCase()}.`:'Mission completed.';
    append(state,{role:'assistant',text,mission_id:event.mission_id,status:data.status,mode:build?'build':'other'});
    if(accepted){const safe=safeBundle(bundle);if(safe){state.lastBuildMission=event.mission_id;state.continueFrom=event.mission_id;state.lastBundle=safe;state.revision=Number.isInteger(data.lineage?.revision)?data.lineage.revision:state.revision+1;save(state)}}
    pending.delete(event.mission_id);setBusy(false);fillHistory();
  }
  return {onOutput(text){base.onOutput(text);parseFrames(text,capture)},connectProvider:base.connectProvider,destroy(){base.destroy()}};
}
