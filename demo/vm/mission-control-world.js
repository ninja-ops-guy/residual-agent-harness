import {mountMissionControl as mountBase} from './mission-control-engineer.js';
import {renderPreview} from './mission-preview.js';
import {executeMissionCommand} from './mission-control-commands.js';

const CURRENT='residual.chat.current.v2', INDEX='residual.chat.index.v2';
const cid=()=> 'c-'+crypto.randomUUID().replaceAll('-','');
const validCid=value=>/^c-[a-f0-9]{32}$/.test(value||'');
const validMid=value=>/^m-[a-f0-9]{32}$/.test(value||'');
const key=id=>'residual.chat.session.v2.'+id;
function readJson(name,fallback){try{return JSON.parse(localStorage.getItem(name)||'null')??fallback}catch{return fallback}}
function fresh(id=cid()){return {version:2,id,turns:[],lastBuildMission:null,continueFrom:null,lastBundle:null,revision:0}}
function safeBundle(bundle){if(!bundle||typeof bundle!=='object'||typeof bundle.summary!=='string'||bundle.summary.length>4000||!Array.isArray(bundle.files)||bundle.files.length<1||bundle.files.length>8)return null;let total=0;const files=[];for(const item of bundle.files){if(!item||typeof item.path!=='string'||typeof item.content!=='string'||!item.path||item.path.startsWith('/')||item.path.includes('\\')||item.path.split('/').some(p=>!p||p==='.'||p==='..'||p.startsWith('.')))return null;const bytes=new TextEncoder().encode(item.content).length;if(bytes>48000)return null;total+=bytes;if(total>128000)return null;files.push({path:item.path,content:item.content})}return {summary:bundle.summary,files}}
function safeTurn(turn){if(!turn||!['user','assistant','system'].includes(turn.role)||typeof turn.text!=='string'||turn.text.length>16000)return null;const mission_id=turn.mission_id==null?null:(validMid(turn.mission_id)?turn.mission_id:null);return {role:turn.role,text:turn.text,mission_id,status:typeof turn.status==='string'?turn.status:null,mode:typeof turn.mode==='string'?turn.mode:null}}
function load(id){const value=readJson(key(id),null);if(!value||value.version!==2||value.id!==id||!Array.isArray(value.turns))return fresh(id);const turns=value.turns.slice(-16).map(safeTurn).filter(Boolean);const lastBuildMission=validMid(value.lastBuildMission)?value.lastBuildMission:null;const lastBundle=safeBundle(value.lastBundle);const continuation=validMid(value.continueFrom)?value.continueFrom:null;const revision=Number.isInteger(value.revision)&&value.revision>=0&&value.revision<=16?value.revision:0;return {version:2,id,turns,lastBuildMission,continueFrom:continuation,lastBundle,revision}}
function index(){return readJson(INDEX,[]).filter(x=>validCid(x?.id)).slice(0,8).map(x=>({id:x.id,title:typeof x.title==='string'?x.title.slice(0,42):x.id.slice(-6),updated:Number.isFinite(x.updated)?x.updated:0}))}
function save(state,title){try{localStorage.setItem(key(state.id),JSON.stringify(state));localStorage.setItem(CURRENT,state.id);const items=index().filter(x=>x.id!==state.id);items.unshift({id:state.id,title:(title||state.turns.find(t=>t.role==='user')?.text||'New conversation').slice(0,42),updated:Date.now()});localStorage.setItem(INDEX,JSON.stringify(items.slice(0,8)))}catch{}}
function append(state,turn){const safe=safeTurn(turn);if(!safe)return;state.turns.push(safe);state.turns=state.turns.slice(-16);save(state)}
function bubble(root,kind,text){const node=document.createElement('div');node.className=`bubble ${kind}`;const meta=document.createElement('span');meta.className='meta';meta.textContent=kind==='user'?'YOU':kind==='assistant'?'RESIDUAL':'SYSTEM';const body=document.createElement('div');body.textContent=text;node.append(meta,body);root.append(node);return node}
function parseFrames(text,consume){const prefix='\x1b]777;RESIDUAL;';let cursor=0;while(true){const start=text.indexOf(prefix,cursor);if(start<0)return;const end=text.indexOf('\x07',start+prefix.length);if(end<0)return;try{const raw=text.slice(start+prefix.length,end).replace(/-/g,'+').replace(/_/g,'/');const bin=atob(raw);consume(JSON.parse(new TextDecoder().decode(Uint8Array.from(bin,c=>c.charCodeAt(0)))))}catch{}cursor=end+1}}
function failureText(data){const values=Object.values(data?.result?.unresolved||{});const item=values.find(v=>v&&typeof v==='object')||{};const code=item.code||'no_verified_candidate';const map={provider_exception:'provider adapter exception',provider_error:'provider request failed',provider_request_failed:'provider request failed',provider_model_unavailable:'selected model unavailable',provider_authorization_failed:'provider authorization/allowance failed',provider_protocol_invalid:'provider response violated the worker protocol',provider_timeout:'provider request timed out',browser_response_invalid:'browser-to-guest provider response was invalid',provider_budget_exhausted:'provider call budget exhausted',invalid_protocol:'provider response violated the worker protocol'};return `Build blocked — no artifact was accepted. Cause: ${map[code]||code}. Open Activity for what happened/why and Evidence for the retained result.`}

export function mountMissionControl(host){
  let id;try{id=localStorage.getItem(CURRENT)}catch{}if(!validCid(id))id=cid();
  let state=load(id), pending=new Set(), busy=false, setBusy=()=>{};
  const wrapped={...host,run:async request=>{let next={...request};if(request.mode==='build'){const previous=document.querySelector('#mc-inline-preview-frame');if(previous)previous.id=`mc-inline-preview-frame-r${Math.max(1,state.revision)}`;next.conversation_id=state.id;if(state.continueFrom)next.parent_mission_id=state.continueFrom;}pending.add(request.id);append(state,{role:'user',text:request.prompt,mission_id:request.id,mode:request.mode});setBusy(true);queueMicrotask(()=>{const prompt=document.querySelector('#mc-prompt'),controls=document.querySelector('#mc-composer details');if(prompt&&prompt.value===request.prompt)prompt.value='';if(controls)controls.open=false});try{return await host.run(next)}catch(error){pending.delete(request.id);setBusy(false);throw error}}};
  const base=mountBase(wrapped), root=document.querySelector('#mission-control'), chat=root.querySelector('#mc-chat'), header=root.querySelector('header');
  const session=document.createElement('span');session.className='muted';session.id='mc-session';
  const history=document.createElement('select');history.id='mc-history';history.title='Conversation history';
  const detach=document.createElement('button');detach.type='button';detach.id='mc-detach';detach.textContent='Fresh artifact';
  const create=document.createElement('button');create.type='button';create.id='mc-new-chat';create.textContent='New chat';
  header.insertBefore(session,header.querySelector('#mc-connect'));header.insertBefore(history,session);header.insertBefore(detach,history);header.insertBefore(create,detach);
  function status(){session.textContent=`CHAT ${state.id.slice(-6)} · ${state.continueFrom?'REV '+state.revision:'FRESH'}`;create.disabled=busy;history.disabled=busy;detach.disabled=busy||!state.continueFrom}
  setBusy=value=>{busy=!!value;status()};
  function fillHistory(){history.replaceChildren();for(const item of index()){const o=document.createElement('option');o.value=item.id;o.textContent=item.title||item.id.slice(-6);o.selected=item.id===state.id;history.append(o)}if(![...history.options].some(o=>o.value===state.id)){const o=document.createElement('option');o.value=state.id;o.textContent='Current chat';o.selected=true;history.prepend(o)}}
  function clearBackground(){const result=root.querySelector('#mc-result'),artifacts=root.querySelector('#mc-artifacts'),events=root.querySelector('#mc-events'),count=root.querySelector('#mc-count'),runState=root.querySelector('#mc-run-state'),preview=root.querySelector('#mc-preview'),previewStatus=root.querySelector('#mc-preview-status');if(result)result.hidden=true;if(artifacts)artifacts.hidden=true;if(events)events.replaceChildren();if(count)count.textContent='0';if(runState)runState.textContent='Browser-local conversation restored. Guest traces remain authoritative evidence.';if(preview){preview.hidden=true;preview.replaceChildren()}if(previewStatus)previewStatus.textContent='No live mission preview yet.'}
  function restore(){clearBackground();chat.replaceChildren();const prompt=root.querySelector('#mc-prompt');if(prompt)prompt.value='';if(!state.turns.length)bubble(chat,'assistant','Give the harness a job. Follow up naturally; accepted build artifacts stay attached to this conversation until you detach them or start a new chat. Type /help for console commands.');for(const turn of state.turns){const node=bubble(chat,turn.role,turn.text);if(turn.role==='assistant'&&turn.mission_id===state.lastBuildMission&&state.lastBundle){const shell=document.createElement('div');shell.className='preview-shell';node.append(shell);renderPreview(shell,state.lastBundle,{frameId:'mc-restored-preview-frame'});const note=document.createElement('div');note.className='muted';note.textContent='Restored browser-local preview cache · verify guest Evidence/Terminal before treating it as authoritative.';node.append(note)}}if(state.turns.length)bubble(chat,'system','Session transcript restored from this browser. Mission evidence and lineage authority remain in verified guest traces.');chat.scrollTop=chat.scrollHeight;status();fillHistory()}
  create.onclick=()=>{if(busy)return;state=fresh();pending.clear();save(state,'New conversation');restore()};
  detach.onclick=()=>{if(busy)return;state.continueFrom=null;save(state);status();bubble(chat,'system','Next build starts a fresh artifact while this conversation remains visible.')};
  history.onchange=()=>{if(busy||!validCid(history.value))return;state=load(history.value);pending.clear();save(state);restore()};
  restore();
  const commandForm=root.querySelector('#mc-form'), commandPrompt=root.querySelector('#mc-prompt');
  function commandReply(text){bubble(chat,'system',text);chat.scrollTop=chat.scrollHeight}
  const commandApi={
    async status(){
      let health='unknown';try{health=typeof host.health==='function'?host.health():(host.ready?.()?'ready':'starting')}catch{health='error'}
      let worker=null;try{worker=typeof host.workerStatus==='function'?await host.workerStatus():null}catch{worker={available:false,error:'worker_status_unavailable'}}
      return {
        guest:health,
        worker,
        mission_active:busy,
        conversation:state.id,
        revision:state.revision,
        attached_parent:state.continueFrom,
        mode:root.querySelector('#mc-mode')?.value||null,
        call_budget:Number(root.querySelector('#mc-budget')?.value||0),
        model:root.querySelector('#mc-model')?.value||null,
        output_tokens:Number(root.querySelector('#mc-tokens')?.value||0),
        evidence_events:Number(root.querySelector('#mc-count')?.textContent||0)
      };
    },
    async tab(name){root.querySelector(`[data-tab="${name}"]`)?.click()},
    async mode(value){const el=root.querySelector('#mc-mode');el.value=value;el.dispatchEvent(new Event('change',{bubbles:true}));return el.value},
    async budget(value){root.querySelector('#mc-budget').value=String(value)},
    async model(value){root.querySelector('#mc-model').value=value},
    async outputTokens(value){const el=root.querySelector('#mc-tokens'),max=Number(el.max||8192),selected=Math.min(value,max);el.value=String(selected);return selected},
    async busy(){return busy},
    async newChat(){create.click()},
    async detach(){const changed=!!state.continueFrom;detach.click();return changed},
    async history(){return index()},
    async clear(){state.turns=[];save(state);restore()},
    async stop(){const button=root.querySelector('#mc-stop');if(!button||button.disabled)return false;button.click();return true},
    async restart(){const button=root.querySelector('#mc-restart');if(!button||button.hidden||button.disabled)return false;button.click();return true},
    async connect(){base.connectProvider()},
    async workerStatus(){
      if(typeof host.workerStatus==='function')return await host.workerStatus();
      return {available:false,detail:'Persistent guest worker status is not exposed by this host.'};
    },
    async meshStatus(){
      if(typeof host.meshStatus==='function')return await host.meshStatus();
      return {
        attached:false,
        browser_lab:'isolated',
        detail:'This Mission Control browser guest is not attached to a native multi-device mesh.',
        native_status:'residual cluster status --json',
        experiments:'residual experiment mesh --messages 1000 --repeats 3'
      };
    }
  };
  commandForm.addEventListener('submit',async event=>{
    const value=commandPrompt.value.trim();
    if(!value.startsWith('/')||value.startsWith('//'))return;
    event.preventDefault();event.stopImmediatePropagation();
    const outcome=await executeMissionCommand(value,commandApi);
    if(!outcome.handled)return;
    commandPrompt.value='';
    commandReply(outcome.text);
  },true);
  function capture(event){
    if(!event||!pending.has(event.mission_id))return;
    if(event.kind==='mission_error'){append(state,{role:'assistant',text:'Mission failed without a verified result. Open Activity for the failure explanation.',mission_id:event.mission_id,status:'INCOMPLETE'});pending.delete(event.mission_id);setBusy(false);fillHistory();return}
    if(event.kind!=='mission_finished')return;
    const data=event.data||{},build=data.execution==='generated_artifacts',bundle=data.result?.values?.build,accepted=build&&data.status==='passed'&&data.result?.success===true&&bundle&&Array.isArray(bundle.files)&&bundle.files.length>0;
    let text;
    if(accepted)text=bundle.summary||'Build completed with accepted generated files.';
    else if(build)text=failureText(data);
    else text=data.result?.values?.answer?.text;
    if(!text&&data.result?.values?.inventory)text='Repository audit completed with deterministic source inventory.';
    if(!text)text=data.status?`Mission ${String(data.status).toLowerCase()}.`:'Mission completed.';
    append(state,{role:'assistant',text,mission_id:event.mission_id,status:data.status,mode:build?'build':'other'});
    if(accepted){const safe=safeBundle(bundle);if(safe){state.lastBuildMission=event.mission_id;state.continueFrom=event.mission_id;state.lastBundle=safe;state.revision=Number.isInteger(data.lineage?.revision)?data.lineage.revision:state.revision+1;save(state)}}
    pending.delete(event.mission_id);setBusy(false);fillHistory();
  }
  return {onOutput(text){base.onOutput(text);parseFrames(text,capture)},connectProvider:base.connectProvider,destroy(){base.destroy()}};
}
