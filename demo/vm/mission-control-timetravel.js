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
#mc-timetravel-panel{background:#020704;color:#d8ffe0}.tt-head{display:flex;gap:12px;align-items:center;flex-wrap:wrap;border-bottom:1px solid #153823;padding-bottom:12px}.tt-head img{width:42px;height:42px;image-rendering:pixelated}.tt-title{font-weight:800;letter-spacing:.14em;color:#39ff68}.tt-sub{color:#68a975;font-size:11px}.tt-spacer{flex:1}.tt-controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.tt-controls input[type=range]{min-width:220px}.tt-pos{font-size:11px;color:#68a975;min-width:72px;text-align:center}.tt-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px;margin-top:14px}.tt-card{border:1px solid #153823;background:#020a04;padding:12px;min-width:0}.tt-card h3{font-size:12px;color:#a8ffbf;margin:0 0 9px}.tt-kv{display:grid;grid-template-columns:120px minmax(0,1fr);gap:5px 10px;font-size:12px}.tt-kv b{color:#68a975;font-weight:500}.tt-kv span{overflow-wrap:anywhere}.tt-event{margin-top:12px;border:1px dashed #285d32;padding:12px}.tt-event pre{max-height:300px;margin:8px 0 0}.tt-diff{display:grid;gap:5px}.tt-change{border-left:2px solid #39ff68;padding-left:8px;font-size:11px;overflow-wrap:anywhere}.tt-change code{color:#a8ffbf}.tt-empty{padding:40px;text-align:center;color:#68a975}.tt-readonly{margin-top:10px;border-left:3px solid #ffaa00;background:#0b0902;padding:8px 10px;color:#d7c58b;font-size:11px}@media(max-width:760px){.tt-grid{grid-template-columns:1fr}.tt-controls input[type=range]{min-width:150px}.tt-kv{grid-template-columns:100px minmax(0,1fr)}}`;
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
  let index=-1,runId=diagnostics.latestRunId||null;

  function rawEvents(){try{return diagnostics.buffer?.snapshot?.()||diagnostics.bundle?.(null)?.events||[]}catch{return []}}
  function timeline(){return deriveTimeline(rawEvents(),runId)}
  function render(){
    const events=timeline();if(index<0||index>=events.length)index=events.length-1;panel.replaceChildren();
    if(!events.length){const empty=document.createElement('div');empty.className='tt-empty';empty.textContent=runId?'No sanitized diagnostic events are retained for this run.':'No sanitized diagnostic events are retained yet.';panel.append(empty);return;}
    const current=events[index],state=reconstructState(events,index),previous=index>0?reconstructState(events,index-1):null,changes=previous?diffStates(previous,state):[];
    const head=document.createElement('div');head.className='tt-head';const img=document.createElement('img');img.src=SPRITE;img.alt='Pixel DeLorean time travel debugger';const titles=document.createElement('div');const title=document.createElement('div');title.className='tt-title';title.textContent='TIME TRAVEL DEBUG';const sub=document.createElement('div');sub.className='tt-sub';sub.textContent=runId?`RUN ${runId}`:'SESSION TIMELINE';titles.append(title,sub);const spacer=document.createElement('span');spacer.className='tt-spacer';
    const controls=document.createElement('div');controls.className='tt-controls';const back=button('← Back'),forward=button('Forward →'),refresh=button('Refresh'),scope=document.createElement('select');scope.setAttribute('aria-label','Time travel scope');const all=document.createElement('option');all.value='';all.textContent='Full session';scope.append(all);const runs=[...new Set(rawEvents().map(x=>x?.run_id).filter(Boolean))];for(const rid of runs){const o=document.createElement('option');o.value=rid;o.textContent=rid===diagnostics.latestRunId?'Latest run':rid.slice(0,18)+'…';scope.append(o)}scope.value=runId||'';
    const slider=document.createElement('input');slider.type='range';slider.min='0';slider.max=String(events.length-1);slider.value=String(index);slider.setAttribute('aria-label','Historical event position');const pos=document.createElement('span');pos.className='tt-pos';pos.textContent=`${index+1} / ${events.length}`;back.disabled=index<=0;forward.disabled=index>=events.length-1;
    back.onclick=()=>{if(index>0){index--;render()}};forward.onclick=()=>{if(index<events.length-1){index++;render()}};refresh.onclick=()=>{index=-1;render()};slider.oninput=()=>{index=Number(slider.value);render()};scope.onchange=()=>{runId=scope.value||null;index=-1;render()};controls.append(scope,back,slider,pos,forward,refresh);head.append(img,titles,spacer,controls);panel.append(head);
    const note=document.createElement('div');note.className='tt-readonly';note.textContent='Read-only historical reconstruction from the privacy-sanitized Mission Control diagnostic buffer. It does not replay execution, mutate guest evidence, or replace the retained guest trace as the authority.';panel.append(note);
    const grid=document.createElement('div');grid.className='tt-grid';grid.append(
      stateCard('Mission state',[['Mission',state.mission_id],['Run',state.run_id],['Status',state.mission.status],['Mode',state.mission.mode],['Execution',state.mission.execution],['Failure',state.mission.failure_code]]),
      stateCard('Runtime / provider',[['Runtime',state.runtime.health],['Provider',state.provider.status],['Stage',state.provider.stage],['Model',state.provider.model],['Evidence',state.evidence.count],['Last evidence',state.evidence.last_kind]])
    );panel.append(grid);
    const event=document.createElement('section');event.className='tt-event';const eh=document.createElement('h3');eh.textContent=`Event ${index+1}: ${current.event_type||'unknown'}`;const meta=document.createElement('div');meta.className='tt-sub';meta.textContent=[current.timestamp,current.component,current.severity,current.event_id].filter(Boolean).join(' · ');const pre=document.createElement('pre');pre.textContent=JSON.stringify(current,null,2);event.append(eh,meta,pre);panel.append(event);
    const diff=document.createElement('section');diff.className='tt-event';const dh=document.createElement('h3');dh.textContent='Delta from previous event';const list=document.createElement('div');list.className='tt-diff';if(!changes.length){const none=document.createElement('div');none.className='tt-sub';none.textContent=index===0?'Start of retained timeline.':'No reconstructed state fields changed.';list.append(none)}else for(const change of changes.slice(0,40)){const row=document.createElement('div');row.className='tt-change';const code=document.createElement('code');code.textContent=change.field;const body=document.createElement('span');body.textContent=` · ${JSON.stringify(change.from)} → ${JSON.stringify(change.to)}`;row.append(code,body);list.append(row)}diff.append(dh,list);panel.append(diff);
  }

  tab.addEventListener('click',()=>{runId=diagnostics.latestRunId||runId;index=-1;queueMicrotask(render)});
  return {refresh:render,destroy(){tab.remove();panel.remove();}};
}
