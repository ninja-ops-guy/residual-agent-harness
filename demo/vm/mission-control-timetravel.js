const SPRITE='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABvklEQVR4nO2ZzXHDIBCFl4zryDldmFOasI/qw1IfuroI67SqIvc0Qi6RfxAYYRaRiPfNeMYjI97Twi4IEwEAAAAAAABqRKV20LatkTASqZnse+JNqqP/yk6qo/Z0ir+n66Lua7suWiNE9TMAAShtoDQIQGkDpQmuAsz8dJ1nZjEzSwl5stFae/cNwQ1FrNhfxhWIqlKAmY09oFUFwMXqAdB7TXqvF1/PTfUzQOxd4FWmUeeRi+hXPwO8y6AhulbLUXCtt/N8rZHf3+kqdXvu6mdAsRpQKudtqp8BxQJQat238aaA+i2QW3kXGB9STl+/Fa8B2AcURlFjPkKN+Dh+SQn6RnytmWC/Elc1A1znAck1QGs9u/bslMg3wktHPlYvxC0ijfn0NeLjeFlqRsKUjxQ937HYLQV6NVCvBiJ6d3yizCz5PZYUvaQzQQ8Pe4P76DuMSPyRmU1v1ticqZk1OlC/xIyUKdtSTr1rQ3Mmbw1QBxpchp7lnWVKJAA59HbmTNM+4DvO1zaoah/gIikAvsorvQLk1MMq8KIhIstUhv5X0UtJgZCY5MNn00stgj5R6YcvpQcAAAAAAAAA2+QHTo+RD7rBWD0AAAAASUVORK5CYII=';

const clone=value=>JSON.parse(JSON.stringify(value));
const object=value=>value&&typeof value==='object'&&!Array.isArray(value)?value:{};
const text=value=>typeof value==='string'?value:'';
const number=value=>Number.isFinite(value)?value:null;

export function deriveTimeline(events, runId=null){
  if(!Array.isArray(events))return [];
  return events
    .map((event,index)=>({event,index}))
    .filter(({event})=>event&&typeof event==='object'&&(!runId||event.run_id===runId))
    .sort((a,b)=>{
      const am=number(a.event.monotonic_ms),bm=number(b.event.monotonic_ms);
      if(am!==null&&bm!==null&&am!==bm)return am-bm;
      const at=Date.parse(a.event.timestamp||''),bt=Date.parse(b.event.timestamp||'');
      if(Number.isFinite(at)&&Number.isFinite(bt)&&at!==bt)return at-bt;
      return a.index-b.index;
    })
    .map(({event})=>clone(event));
}

export function reconstructState(events, index=events.length-1){
  const ordered=deriveTimeline(events);
  const end=Math.min(Math.max(Number.isInteger(index)?index:-1,-1),ordered.length-1);
  const state={
    event_index:end,event_count:ordered.length,run_id:null,mission_id:null,
    mission:{status:'unknown',mode:null,execution:null,failure_code:null},
    runtime:{health:'unknown'},provider:{status:'unknown',stage:null,model:null},
    evidence:{count:0,last_kind:null,last_sequence:null},ui:{},diagnostic:null,release:{commit:null,webvm_commit:null}
  };
  for(let i=0;i<=end;i++){
    const event=ordered[i],ctx=object(event.context),type=text(event.event_type);
    if(event.run_id)state.run_id=event.run_id;
    if(event.mission_id)state.mission_id=event.mission_id;
    if(event.release&&typeof event.release==='object')state.release={...state.release,...event.release};
    if(type==='mission.submitted'){state.mission.status='submitted';state.mission.mode=ctx.mode||state.mission.mode;}
    else if(type==='mission.started'||type==='mission.host_run_started')state.mission.status='running';
    else if(type==='mission.host_run_completed')state.mission.status=ctx.run_status||'completed';
    else if(type==='mission.finished'){state.mission.status=ctx.status||'finished';state.mission.execution=ctx.execution||null;state.mission.failure_code=ctx.failure_code||null;}
    else if(type==='mission.failed'||type==='mission.host_run_failed'){state.mission.status='failed';state.mission.failure_code=ctx.failure_code||ctx.error_name||state.mission.failure_code;}
    else if(type==='runtime.health_changed')state.runtime.health=ctx.health||ctx.to||state.runtime.health;
    else if(type.startsWith('provider.')){
      state.provider.status=type.split('.').slice(1).join('_')||state.provider.status;
      if(ctx.stage)state.provider.stage=ctx.stage;
      if(ctx.model)state.provider.model=ctx.model;
    }
    else if(type==='evidence.projected'){
      state.evidence.count+=1;state.evidence.last_kind=ctx.evidence_kind||null;state.evidence.last_sequence=Number.isInteger(ctx.sequence)?ctx.sequence:null;
    }
    else if(type==='ui.state_changed'&&ctx.stage)state.ui[ctx.stage]=ctx.status||'unknown';
    if(event.diagnostic)state.diagnostic=clone(event.diagnostic);
  }
  return state;
}

function flatten(value,prefix='',out={}){
  if(value&&typeof value==='object'&&!Array.isArray(value)){
    for(const [key,item] of Object.entries(value))flatten(item,prefix?`${prefix}.${key}`:key,out);
  }else out[prefix]=value;
  return out;
}

export function diffStates(from,to){
  const a=flatten(from||{}),b=flatten(to||{}),keys=[...new Set([...Object.keys(a),...Object.keys(b)])].sort(),changes=[];
  for(const key of keys)if(JSON.stringify(a[key])!==JSON.stringify(b[key]))changes.push({field:key,from:a[key]??null,to:b[key]??null});
  return changes;
}

function addStyle(root){
  if(root.querySelector('#mc-timetravel-style'))return;
  const style=document.createElement('style');style.id='mc-timetravel-style';style.textContent=`
#mc-timetravel-panel{--tt-green:#39ff68;--tt-dim:#68a975;--tt-line:#1f5630;--tt-panel:#020704;background:#010402;color:#d8ffe0;padding:0!important}
#mc-timetravel-panel .tt-shell{min-height:100%;background:linear-gradient(rgba(57,255,104,.018) 50%,transparent 50%),#010402;background-size:100% 4px}
#mc-timetravel-panel .tt-top{display:flex;gap:10px;align-items:center;padding:10px 12px;border-bottom:1px solid var(--tt-line);flex-wrap:wrap}
#mc-timetravel-panel .tt-title{font-weight:800;letter-spacing:.14em;color:var(--tt-green)}#mc-timetravel-panel .tt-sub{color:var(--tt-dim);font-size:11px}#mc-timetravel-panel .tt-spacer{flex:1}
#mc-timetravel-panel .tt-dashboard{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(250px,.75fr);gap:10px;padding:10px}
#mc-timetravel-panel .tt-hero,#mc-timetravel-panel .tt-card,#mc-timetravel-panel .tt-timeline,#mc-timetravel-panel .tt-event{border:1px solid var(--tt-line);background:#020804;min-width:0}
#mc-timetravel-panel .tt-hero{min-height:310px;position:relative;overflow:hidden;display:grid;place-items:center;padding:12px;cursor:pointer}
#mc-timetravel-panel .tt-hero:before{content:'';position:absolute;inset:0;background:radial-gradient(circle at 50% 45%,rgba(57,255,104,.13),transparent 42%),linear-gradient(transparent 75%,rgba(57,255,104,.05));pointer-events:none}
#mc-timetravel-panel .tt-hero img{width:min(78%,560px);max-height:260px;object-fit:contain;image-rendering:pixelated;filter:contrast(1.18) brightness(.78) saturate(.85);position:relative;z-index:1}
#mc-timetravel-panel .tt-hero:after{content:'';position:absolute;inset:0;pointer-events:none;opacity:.16;background-image:radial-gradient(#9dffb2 0.7px,transparent .8px);background-size:3px 3px;mix-blend-mode:screen}
#mc-timetravel-panel .tt-hero.active img{filter:contrast(1.22) brightness(.9) saturate(1)}#mc-timetravel-panel .tt-enter{position:absolute;right:12px;bottom:10px;z-index:2;color:var(--tt-green);font-size:11px;letter-spacing:.08em}
#mc-timetravel-panel .tt-side{display:grid;gap:10px;align-content:start}#mc-timetravel-panel .tt-card h3,#mc-timetravel-panel .tt-event h3{font-size:11px;letter-spacing:.1em;color:var(--tt-green);padding:8px 10px;margin:0;border-bottom:1px solid var(--tt-line)}
#mc-timetravel-panel .tt-kv{display:grid;grid-template-columns:92px minmax(0,1fr);gap:5px 9px;padding:10px;font-size:12px}#mc-timetravel-panel .tt-kv b{font-weight:400;color:var(--tt-dim)}#mc-timetravel-panel .tt-kv span{overflow-wrap:anywhere}
#mc-timetravel-panel .tt-timeline{margin:0 10px 10px;padding:10px}#mc-timetravel-panel .tt-track{display:grid;grid-template-columns:auto minmax(100px,1fr) auto auto;gap:8px;align-items:center}
#mc-timetravel-panel input[type=range]{width:100%;accent-color:var(--tt-green)}#mc-timetravel-panel button,#mc-timetravel-panel select{min-height:38px}
#mc-timetravel-panel .tt-actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:9px}#mc-timetravel-panel .tt-actions button{font-size:11px;padding:6px 9px}
#mc-timetravel-panel .tt-lower{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px;margin:0 10px 10px}
#mc-timetravel-panel .tt-event{padding-bottom:10px}#mc-timetravel-panel .tt-event pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:260px;margin:9px 10px 0;font-size:11px}
#mc-timetravel-panel .tt-diff{display:grid;gap:5px;padding:9px 10px}#mc-timetravel-panel .tt-change{border-left:2px solid var(--tt-green);padding-left:7px;font-size:11px;overflow-wrap:anywhere}#mc-timetravel-panel .tt-change code{color:#a8ffbf}
#mc-timetravel-panel .tt-readonly{margin:0 10px 10px;border-left:3px solid #8c7d31;background:#090801;padding:8px 10px;color:#c9bd7d;font-size:11px}
#mc-timetravel-panel .tt-empty{padding:40px;text-align:center;color:var(--tt-dim)}
@media(max-width:760px){#mc-timetravel-panel .tt-dashboard,#mc-timetravel-panel .tt-lower{grid-template-columns:1fr}#mc-timetravel-panel .tt-hero{min-height:220px}#mc-timetravel-panel .tt-hero img{width:94%;max-height:200px}#mc-timetravel-panel .tt-track{grid-template-columns:1fr 1fr}#mc-timetravel-panel .tt-track input{grid-column:1/-1;grid-row:1}#mc-timetravel-panel .tt-track select{grid-column:1/-1}}
`;
  root.append(style);
}
function button(label,id){const b=document.createElement('button');b.type='button';b.textContent=label;if(id)b.id=id;return b;}
function field(grid,label,value){const a=document.createElement('b'),b=document.createElement('span');a.textContent=label;b.textContent=value==null?'—':String(value);grid.append(a,b);}
function stateCard(title,items){const card=document.createElement('section');card.className='tt-card';const h=document.createElement('h3');h.textContent=title;const grid=document.createElement('div');grid.className='tt-kv';for(const item of items)field(grid,item[0],item[1]);card.append(h,grid);return card;}
export function mountTimeTravelDebug(root,diagnostics){
  if(!root||!diagnostics||root.querySelector('#mc-timetravel-panel'))return null;
  addStyle(root);
  const tabs=root.querySelector('.tabs'),main=root.querySelector('main');if(!tabs||!main)return null;
  const tab=button('🚗 Time Travel','mc-timetravel');tab.dataset.tab='timetravel';tab.setAttribute('aria-selected','false');tabs.append(tab);
  const panel=document.createElement('section');panel.id='mc-timetravel-panel';panel.className='panel';panel.hidden=true;main.append(panel);
  let index=-1,runId=diagnostics.latestRunId||null,entered=false;
  function rawEvents(){try{return diagnostics.buffer?.snapshot?.()||diagnostics.bundle?.(null)?.events||[]}catch{return []}}
  function timeline(){return deriveTimeline(rawEvents(),runId)}
  function render(){
    const events=timeline();if(index<0||index>=events.length)index=events.length-1;panel.replaceChildren();
    if(!events.length){const empty=document.createElement('div');empty.className='tt-empty';empty.textContent=runId?'No sanitized diagnostic events are retained for this run.':'No sanitized diagnostic events are retained yet.';panel.append(empty);return;}
    const current=events[index],state=reconstructState(events,index),previous=index>0?reconstructState(events,index-1):null,changes=previous?diffStates(previous,state):[];
    const shell=document.createElement('div');shell.className='tt-shell';panel.append(shell);
    const top=document.createElement('div');top.className='tt-top';const title=document.createElement('strong');title.className='tt-title';title.textContent='RESIDUAL // TIME TRAVEL DEBUGGER';const sub=document.createElement('span');sub.className='tt-sub';sub.textContent=runId?`RUN ${runId}`:'FULL SESSION';const spacer=document.createElement('span');spacer.className='tt-spacer';const clock=document.createElement('span');clock.className='tt-sub';clock.textContent=current.timestamp||'historical';top.append(title,sub,spacer,clock);shell.append(top);
    const dashboard=document.createElement('div');dashboard.className='tt-dashboard';
    const hero=document.createElement('button');hero.type='button';hero.className='tt-hero'+(entered?' active':'');hero.setAttribute('aria-label','Enter historical timeline');const img=document.createElement('img');img.src=SPRITE;img.alt='16-bit shaded DeLorean with open gull-wing doors';const enter=document.createElement('span');enter.className='tt-enter';enter.textContent=entered?'TEMPORAL LINK ACTIVE · CLICK TO REFRESH':'CLICK DELOREAN TO ENTER TIMELINE ▶';hero.append(img,enter);hero.onclick=()=>{entered=true;index=events.length-1;render()};dashboard.append(hero);
    const side=document.createElement('div');side.className='tt-side';side.append(
      stateCard('STATE SNAPSHOT',[['Event',current.event_type],['Mission',state.mission_id],['Status',state.mission.status],['Runtime',state.runtime.health],['Provider',state.provider.stage||state.provider.status],['Evidence',state.evidence.count],['Failure',state.mission.failure_code]]),
      stateCard('TRACE BINDING',[['Run',state.run_id],['Commit',state.release.commit],['WebVM',state.release.webvm_commit],['Sequence',state.evidence.last_sequence],['Last proof',state.evidence.last_kind]])
    );dashboard.append(side);shell.append(dashboard);
    const timelineBox=document.createElement('section');timelineBox.className='tt-timeline';const track=document.createElement('div');track.className='tt-track';const back=button('◀ STEP'),forward=button('STEP ▶'),scope=document.createElement('select');scope.setAttribute('aria-label','Time travel scope');const all=document.createElement('option');all.value='';all.textContent='Full session';scope.append(all);for(const rid of [...new Set(rawEvents().map(x=>x?.run_id).filter(Boolean))]){const o=document.createElement('option');o.value=rid;o.textContent=rid===diagnostics.latestRunId?'Latest run':rid.slice(0,18)+'…';scope.append(o)}scope.value=runId||'';const slider=document.createElement('input');slider.type='range';slider.min='0';slider.max=String(events.length-1);slider.value=String(index);slider.setAttribute('aria-label','Historical event position');const pos=document.createElement('span');pos.className='tt-sub';pos.textContent=`${index+1} / ${events.length}`;back.disabled=index<=0;forward.disabled=index>=events.length-1;back.onclick=()=>{entered=true;if(index>0){index--;render()}};forward.onclick=()=>{entered=true;if(index<events.length-1){index++;render()}};slider.oninput=()=>{entered=true;index=Number(slider.value);render()};scope.onchange=()=>{runId=scope.value||null;entered=true;index=-1;render()};track.append(back,slider,forward,scope);
    const actions=document.createElement('div');actions.className='tt-actions';const first=button('|◀ FIRST'),last=button('LAST ▶|'),failure=button('⚠ JUMP TO FAILURE'),evidence=button('◆ JUMP TO EVIDENCE');first.onclick=()=>{entered=true;index=0;render()};last.onclick=()=>{entered=true;index=events.length-1;render()};failure.onclick=()=>{entered=true;let found=-1;for(let i=0;i<events.length;i++){if(events[i].severity==='error'||events[i].diagnostic||/failed|error/.test(events[i].event_type||'')){found=i;break}}if(found>=0)index=found;render()};evidence.onclick=()=>{entered=true;let found=-1;for(let i=index+1;i<events.length;i++)if(events[i].event_type==='evidence.projected'){found=i;break}if(found<0)for(let i=0;i<events.length;i++)if(events[i].event_type==='evidence.projected'){found=i;break}if(found>=0)index=found;render()};actions.append(first,last,failure,evidence);timelineBox.append(track,actions);shell.append(timelineBox);
    const lower=document.createElement('div');lower.className='tt-lower';const event=document.createElement('section');event.className='tt-event';const eh=document.createElement('h3');eh.textContent=`EVENT DETAILS · ${index+1}/${events.length}`;const pre=document.createElement('pre');pre.textContent=JSON.stringify(current,null,2);event.append(eh,pre);
    const diff=document.createElement('section');diff.className='tt-event';const dh=document.createElement('h3');dh.textContent='DIFF VIEW · PREVIOUS → CURRENT';const list=document.createElement('div');list.className='tt-diff';if(!changes.length){const none=document.createElement('div');none.className='tt-sub';none.textContent=index===0?'Start of retained timeline.':'No reconstructed state fields changed.';list.append(none)}else for(const change of changes.slice(0,40)){const row=document.createElement('div');row.className='tt-change';const code=document.createElement('code');code.textContent=change.field;const body=document.createElement('span');body.textContent=` · ${JSON.stringify(change.from)} → ${JSON.stringify(change.to)}`;row.append(code,body);list.append(row)}diff.append(dh,list);lower.append(event,diff);shell.append(lower);
    const note=document.createElement('div');note.className='tt-readonly';note.textContent='READ-ONLY RECONSTRUCTION · Historical inspection never mutates guest evidence, receipts, provider budgets, or the authoritative retained trace.';shell.append(note);
  }
  tab.onclick=()=>{root.dataset.view='timetravel';for(const item of root.querySelectorAll('.panel'))item.hidden=item!==panel;for(const item of root.querySelectorAll('[data-tab]'))item.setAttribute('aria-selected',String(item===tab));runId=diagnostics.latestRunId||runId;index=-1;queueMicrotask(render)};
  return {refresh:render,destroy(){tab.remove();panel.remove();}};
}
