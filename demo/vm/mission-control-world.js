import {mountMissionControl as mountBase} from './mission-control.js';
import {renderPreview} from './mission-preview.js';

const CURRENT='residual.chat.current.v2', INDEX='residual.chat.index.v2';
const cid=()=> 'c-'+crypto.randomUUID().replaceAll('-','');
const validCid=value=>/^c-[a-f0-9]{32}$/.test(value||'');
const key=id=>'residual.chat.session.v2.'+id;
function readJson(name,fallback){try{return JSON.parse(localStorage.getItem(name)||'null')??fallback}catch{return fallback}}
function fresh(id=cid()){return {version:2,id,turns:[],lastBuildMission:null,continueFrom:null,lastBundle:null,revision:0}}
function load(id){const value=readJson(key(id),null);return value&&value.version===2&&value.id===id?value:fresh(id)}
function index(){return readJson(INDEX,[]).filter(x=>validCid(x?.id)).slice(0,8)}
function save(state,title){try{localStorage.setItem(key(state.id),JSON.stringify(state));localStorage.setItem(CURRENT,state.id);const items=index().filter(x=>x.id!==state.id);items.unshift({id:state.id,title:(title||state.turns.find(t=>t.role==='user')?.text||'New conversation').slice(0,42),updated:Date.now()});localStorage.setItem(INDEX,JSON.stringify(items.slice(0,8)))}catch{}}
function append(state,turn){state.turns.push(turn);state.turns=state.turns.slice(-16);save(state)}
function bubble(root,kind,text){const node=document.createElement('div');node.className=`bubble ${kind}`;const meta=document.createElement('span');meta.className='meta';meta.textContent=kind==='user'?'YOU':kind==='assistant'?'RESIDUAL':'SYSTEM';const body=document.createElement('div');body.textContent=text;node.append(meta,body);root.append(node);return node}
function parseFrames(text,consume){const prefix='\x1b]777;RESIDUAL;';let cursor=0;while(true){const start=text.indexOf(prefix,cursor);if(start<0)return;const end=text.indexOf('\x07',start+prefix.length);if(end<0)return;try{const raw=text.slice(start+prefix.length,end).replace(/-/g,'+').replace(/_/g,'/');const bin=atob(raw);consume(JSON.parse(new TextDecoder().decode(Uint8Array.from(bin,c=>c.charCodeAt(0)))))}catch{}cursor=end+1}}

export function mountMissionControl(host){
  let id;try{id=localStorage.getItem(CURRENT)}catch{}if(!validCid(id))id=cid();
  let state=load(id), pending=new Set();
  const wrapped={...host,run:async request=>{let next={...request};if(request.mode==='build'){const previous=document.querySelector('#mc-inline-preview-frame');if(previous)previous.id=`mc-inline-preview-frame-r${Math.max(1,state.revision)}`;next.conversation_id=state.id;if(state.continueFrom)next.parent_mission_id=state.continueFrom;}pending.add(request.id);append(state,{role:'user',text:request.prompt,mission_id:request.id,mode:request.mode});return host.run(next)}};
  const base=mountBase(wrapped), root=document.querySelector('#mission-control'), chat=root.querySelector('#mc-chat'), header=root.querySelector('header');
  const session=document.createElement('span');session.className='muted';session.id='mc-session';
  const history=document.createElement('select');history.id='mc-history';history.title='Conversation history';
  const detach=document.createElement('button');detach.type='button';detach.id='mc-detach';detach.textContent='Fresh artifact';
  const create=document.createElement('button');create.type='button';create.id='mc-new-chat';create.textContent='New chat';
  header.insertBefore(session,header.querySelector('#mc-connect'));header.insertBefore(history,session);header.insertBefore(detach,history);header.insertBefore(create,detach);
  function status(){session.textContent=`CHAT ${state.id.slice(-6)} · ${state.continueFrom?'REV '+state.revision:'FRESH'}`;detach.disabled=!state.continueFrom}
  function fillHistory(){history.replaceChildren();for(const item of index()){const o=document.createElement('option');o.value=item.id;o.textContent=item.title||item.id.slice(-6);o.selected=item.id===state.id;history.append(o)}if(![...history.options].some(o=>o.value===state.id)){const o=document.createElement('option');o.value=state.id;o.textContent='Current chat';o.selected=true;history.prepend(o)}}
  function clearBackground(){const result=root.querySelector('#mc-result'),artifacts=root.querySelector('#mc-artifacts'),events=root.querySelector('#mc-events'),count=root.querySelector('#mc-count'),runState=root.querySelector('#mc-run-state'),preview=root.querySelector('#mc-preview'),previewStatus=root.querySelector('#mc-preview-status');if(result)result.hidden=true;if(artifacts)artifacts.hidden=true;if(events)events.replaceChildren();if(count)count.textContent='0';if(runState)runState.textContent='Conversation restored. Run a mission to populate background evidence.';if(preview){preview.hidden=true;preview.replaceChildren()}if(previewStatus)previewStatus.textContent='No preview yet.'}
  function restore(){clearBackground();chat.replaceChildren();if(!state.turns.length)bubble(chat,'assistant','Give the harness a job. Follow up naturally; accepted build artifacts stay attached to this conversation until you detach them or start a new chat.');for(const turn of state.turns){const node=bubble(chat,turn.role,turn.text);if(turn.role==='assistant'&&turn.mission_id===state.lastBuildMission&&state.lastBundle){const shell=document.createElement('div');shell.className='preview-shell';node.append(shell);renderPreview(shell,state.lastBundle,{frameId:'mc-restored-preview-frame'})}}chat.scrollTop=chat.scrollHeight;status();fillHistory()}
  create.onclick=()=>{state=fresh();pending.clear();save(state,'New conversation');restore()};
  detach.onclick=()=>{state.continueFrom=null;save(state);status();bubble(chat,'system','Next build starts a fresh artifact while this conversation remains visible.')};
  history.onchange=()=>{if(!validCid(history.value))return;state=load(history.value);pending.clear();save(state);restore()};
  restore();
  function capture(event){if(!event||!pending.has(event.mission_id))return;if(event.kind==='mission_error'){append(state,{role:'assistant',text:'Mission failed without a verified result.',mission_id:event.mission_id,status:'INCOMPLETE'});pending.delete(event.mission_id);status();fillHistory();return}if(event.kind!=='mission_finished')return;const data=event.data||{},build=data.execution==='generated_artifacts',bundle=data.result?.values?.build;let text=build?(bundle?.summary||'Build completed.'):data.result?.values?.answer?.text;if(!text&&data.result?.values?.inventory)text='Repository audit completed with deterministic source inventory.';if(!text)text=data.status?`Mission ${String(data.status).toLowerCase()}.`:'Mission completed.';append(state,{role:'assistant',text,mission_id:event.mission_id,status:data.status,mode:build?'build':'other'});if(build&&data.result?.success&&bundle){state.lastBuildMission=event.mission_id;state.continueFrom=event.mission_id;state.lastBundle=bundle;state.revision=data.lineage?.revision||state.revision+1;save(state)}pending.delete(event.mission_id);status();fillHistory()}
  return {onOutput(text){base.onOutput(text);parseFrames(text,capture)},connectProvider:base.connectProvider,destroy(){base.destroy()}};
}
