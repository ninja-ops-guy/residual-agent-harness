const SPRITE=new URL('./time-travel-hero.webp',import.meta.url).href;

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
      // Wall time survives page reloads; performance.now() does not.
      const at=Date.parse(a.event.timestamp||''),bt=Date.parse(b.event.timestamp||'');
      const ta=Number.isFinite(at)?at:Infinity,tb=Number.isFinite(bt)?bt:Infinity;
      if(ta!==tb)return ta-tb;
      const am=number(a.event.monotonic_ms),bm=number(b.event.monotonic_ms);
      const ma=am??Infinity,mb=bm??Infinity;if(ma!==mb)return ma-mb;
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
  const selectedRun=ordered[end]?.run_id||null;
  for(let i=0;i<=end;i++){
    const event=ordered[i],ctx=object(event.context),type=text(event.event_type);
    // Global runtime events apply across runs, mission/provider state never does.
    if(event.run_id && event.run_id!==selectedRun)continue;
    if(!selectedRun && event.run_id)continue;
    if(event.run_id)state.run_id=event.run_id;
    if(event.mission_id)state.mission_id=event.mission_id;
    if(event.release&&typeof event.release==='object')state.release={...state.release,...event.release};
    if(type==='mission.submitted'){state.mission.status='submitted';state.mission.mode=ctx.mode||state.mission.mode;}
    else if(type==='mission.started'||type==='mission.host_run_started')state.mission.status='running';
    else if(type==='mission.host_run_completed'&&!['passed','failed','cancelled','finished'].includes(state.mission.status))state.mission.status=ctx.run_status||'completed';
    else if(type==='mission.finished'){state.mission.status=ctx.status||'finished';state.mission.execution=ctx.execution||null;state.mission.failure_code=ctx.failure_code||null;}
    else if(type==='mission.failed'||type==='mission.host_run_failed'){state.mission.status='failed';state.mission.failure_code=ctx.failure_code||ctx.error_name||state.mission.failure_code;}
    else if(type==='runtime.health_changed')state.runtime.health=ctx.health||ctx.to||state.runtime.health;
    else if(type.startsWith('provider.')){
      state.provider.status=type.split('.').slice(1).join('_')||state.provider.status;
      state.provider.stage=ctx.stage||null;
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

function flatten(value,prefix='',out=Object.create(null)){
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

#mc-timetravel-panel{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;--tt-green:#72ff98;--tt-dim:#87b8af;--tt-line:#25765a;color:#c7dfd9}
#mc-timetravel-panel button,#mc-timetravel-panel select{font:inherit;color:var(--tt-green);background:#03110e;border:1px solid var(--tt-line);border-radius:2px;cursor:pointer}
#mc-timetravel-panel button:disabled{opacity:.4;cursor:not-allowed}
#mc-timetravel-panel :focus-visible{outline:2px solid #b2ffc4;outline-offset:3px}
#mc-timetravel-panel .tt-title{font-size:16px}
#mc-timetravel-panel .tt-hero{min-height:390px;background:radial-gradient(ellipse at 50% 70%,#0d4329,transparent 65%),#010907;isolation:isolate}
#mc-timetravel-panel .tt-hero-heading{position:absolute;top:20px;left:22px;text-align:left;z-index:3;font-size:clamp(16px,2vw,27px);letter-spacing:.1em}
#mc-timetravel-panel .tt-hero-heading small{display:block;font-size:11px;color:#c7dfd9;margin-top:9px;letter-spacing:.08em}
#mc-timetravel-panel .tt-clock{position:absolute;width:280px;height:280px;border:4px double #48cc71;border-radius:50%;box-shadow:0 0 36px #2ddb5844,inset 0 0 32px #2ddb5822;color:#72ff98;font-size:25px;display:grid;place-items:start center;padding-top:10px;box-sizing:border-box;transform:translateY(20px)}
#mc-timetravel-panel .tt-clock:after{content:'';position:absolute;top:45px;height:95px;width:2px;background:#72ff98;transform-origin:bottom;transform:rotate(30deg)}
#mc-timetravel-panel .tt-hero img{margin-top:45px;width:100%;height:auto;max-height:390px;object-fit:contain;filter:none}#mc-timetravel-panel .tt-hero-heading{padding:8px;background:#020907d9}#mc-timetravel-panel .tt-enter{background:#020907e8;padding:7px}
#mc-timetravel-panel .tt-lower{grid-template-columns:minmax(0,1.35fr) minmax(0,1fr) minmax(200px,.8fr)}
#mc-timetravel-panel .tt-log{max-height:260px;overflow:auto;padding:8px}
#mc-timetravel-panel .tt-log button{display:block;width:100%;text-align:left;font-size:11px;min-height:28px;border:0;padding:5px 8px;color:#91bdb2;overflow-wrap:anywhere}
#mc-timetravel-panel .tt-log button[aria-current=true]{background:#113a2b;color:#b0ffbd;border-left:3px solid #72ff98}
#mc-timetravel-panel .tt-log button.tt-failure{color:#ff8b8b}
#mc-timetravel-panel .tt-change{border:0;padding:0;margin-bottom:7px}
#mc-timetravel-panel .tt-change span{display:block;padding:4px 6px;white-space:pre-wrap}
#mc-timetravel-panel .tt-removed{background:#33161c;color:#ff9797}
#mc-timetravel-panel .tt-added{background:#073a24;color:#80ffac}
#mc-timetravel-panel .tt-side .tt-event{max-height:210px;overflow:auto}
#mc-timetravel-panel .tt-readonly{color:#8bbbae;background:#061410;border-color:#25765a}
#mc-timetravel-panel .tt-position{display:flex;justify-content:space-between;color:var(--tt-green);font-size:12px;margin-bottom:10px}
@media(max-width:900px){#mc-timetravel-panel .tt-lower{grid-template-columns:1fr 1fr}#mc-timetravel-panel .tt-lower>.tt-card{grid-column:1/-1}}
@media(max-width:760px){#mc-timetravel-panel .tt-lower{grid-template-columns:1fr}#mc-timetravel-panel .tt-hero{min-height:350px}}
`;
  root.append(style);
}
export function isFailure(event){return event?.severity==='error'||!!event?.diagnostic||/failed|error|rejected/.test(event?.event_type||'')||['counterexample','provider_failed'].includes(event?.context?.evidence_kind)||['failed','rejected','cancelled'].includes(event?.context?.status);}

function button(label,id){const b=document.createElement('button');b.type='button';b.textContent=label;if(id)b.id=id;return b;}
function field(grid,label,value){const a=document.createElement('b'),b=document.createElement('span');a.textContent=label;b.textContent=value==null?'—':String(value);grid.append(a,b);}
function stateCard(title,items){const card=document.createElement('section');card.className='tt-card';const h=document.createElement('h3');h.textContent=title;const grid=document.createElement('div');grid.className='tt-kv';for(const item of items)field(grid,item[0],item[1]);card.append(h,grid);return card;}
export function mountTimeTravelDebug(root,diagnostics){
  if(!root||!diagnostics||root.querySelector('#mc-timetravel-panel'))return null;
  addStyle(root);
  const tabs=root.querySelector('.tabs'),main=root.querySelector('main');if(!tabs||!main)return null;
  const tab=button('🚗 Time Travel','mc-timetravel');tab.dataset.tab='timetravel';tab.setAttribute('aria-selected','false');tabs.append(tab);
  const panel=document.createElement('section');panel.id='mc-timetravel-panel';panel.className='panel';panel.hidden=true;main.append(panel);
  let index=-1,runId=diagnostics.latestRunId||null,entered=false,selectedId=null,destroyed=false;
  function rawEvents(){try{return diagnostics.buffer?.snapshot?.()||diagnostics.bundle?.(null)?.events||[]}catch{return []}}
  function timeline(){return deriveTimeline(rawEvents(),runId)}
  function render(){
    if(destroyed)return;
    const focused=panel.contains(document.activeElement)?document.activeElement:null;
    const focusLabel=focused?.getAttribute('aria-label')||focused?.textContent;
    const scroll=panel.scrollTop;
    const history=deriveTimeline(rawEvents()),events=runId?history.filter(event=>event.run_id===runId):history;
    if(index<0||index>=events.length)index=events.length-1;panel.replaceChildren();
    const at=i=>({...reconstructState(history,history.indexOf(events[i])),event_index:i,event_count:events.length});
    const current=events[index]||{},state=at(index),previous=index>0?at(index-1):null,changes=previous?diffStates(previous,state):[];
    selectedId=current.event_id||null;
    const shell=document.createElement('div');shell.className='tt-shell';panel.append(shell);
    const top=document.createElement('div');top.className='tt-top';const title=document.createElement('strong');title.className='tt-title';title.textContent='RESIDUAL // TIME TRAVEL DEBUGGER';const sub=document.createElement('span');sub.className='tt-sub';sub.textContent=runId?`RUN ${runId}`:'FULL SESSION';const spacer=document.createElement('span');spacer.className='tt-spacer';const clock=document.createElement('span');clock.className='tt-sub';clock.textContent=current.timestamp||'historical';top.append(title,sub,spacer,clock);shell.append(top);
    const dashboard=document.createElement('div');dashboard.className='tt-dashboard';
    const hero=document.createElement('button');hero.type='button';hero.className='tt-hero'+(entered?' active':'');hero.setAttribute('aria-label','Enter historical timeline');const img=document.createElement('img');img.src=SPRITE;img.alt='16-bit shaded DeLorean with open gull-wing doors';const enter=document.createElement('span');enter.className='tt-enter';enter.textContent=entered?'TEMPORAL LINK ACTIVE · CLICK TO REFRESH':'CLICK DELOREAN TO ENTER TIMELINE ▶';const heading=document.createElement('span');heading.className='tt-hero-heading';heading.textContent='TIME TRAVEL DEBUGGER';const tagline=document.createElement('small');tagline.textContent='INSPECT. UNDERSTAND. IMPROVE.';heading.append(tagline);hero.append(img,heading,enter);hero.onclick=()=>{entered=true;refresh()};dashboard.append(hero);
    const side=document.createElement('div');side.className='tt-side';side.append(
      stateCard('STATE SNAPSHOT',[['Timestamp',current.timestamp],['Event',current.event_type],['Mission',state.mission_id],['Status',state.mission.status],['Runtime',state.runtime.health],['Provider',state.provider.stage||state.provider.status],['Evidence',state.evidence.count],['Failure',state.mission.failure_code]]),
      stateCard('TRACE BINDING',[['Run',state.run_id],['Commit',state.release.commit],['WebVM',state.release.webvm_commit],['Sequence',state.evidence.last_sequence],['Last proof',state.evidence.last_kind]])
    );dashboard.append(side);shell.append(dashboard);
    const timelineBox=document.createElement('section');timelineBox.className='tt-timeline';const track=document.createElement('div');track.className='tt-track';const back=button('◀ STEP'),forward=button('STEP ▶'),scope=document.createElement('select');scope.setAttribute('aria-label','Time travel scope');const all=document.createElement('option');all.value='';all.textContent='Full session';scope.append(all);for(const rid of [...new Set(rawEvents().map(x=>x?.run_id).filter(Boolean))]){const o=document.createElement('option');o.value=rid;o.textContent=rid===diagnostics.latestRunId?'Latest run':rid.slice(0,18)+'…';scope.append(o)}scope.value=runId||'';const slider=document.createElement('input');slider.type='range';slider.min='0';slider.max=String(Math.max(0,events.length-1));slider.value=String(Math.max(0,index));slider.disabled=!events.length;slider.setAttribute('aria-label','Historical event position');const pos=document.createElement('span');pos.className='tt-sub';pos.textContent=`${index+1} / ${events.length}`;back.disabled=index<=0;forward.disabled=index>=events.length-1;back.onclick=()=>{entered=true;if(index>0){index--;render()}};forward.onclick=()=>{entered=true;if(index<events.length-1){index++;render()}};slider.onchange=()=>{entered=true;index=Number(slider.value);render()};scope.onchange=()=>{runId=scope.value||null;entered=true;index=-1;render()};track.append(back,slider,forward,scope);
    const actions=document.createElement('div');actions.className='tt-actions';const first=button('|◀ FIRST'),last=button('LAST ▶|'),failure=button('⚠ JUMP TO FAILURE'),evidence=button('◆ JUMP TO EVIDENCE');first.onclick=()=>{entered=true;index=0;render()};last.onclick=()=>{entered=true;index=events.length-1;render()};failure.onclick=()=>{entered=true;let found=-1;for(let i=0;i<events.length;i++){if(isFailure(events[i])){found=i;break}}if(found>=0)index=found;render()};evidence.onclick=()=>{entered=true;let found=-1;for(let i=index+1;i<events.length;i++)if(events[i].event_type==='evidence.projected'){found=i;break}if(found<0)for(let i=0;i<events.length;i++)if(events[i].event_type==='evidence.projected'){found=i;break}if(found>=0)index=found;render()};const fork=button('FORK HERE · UNAVAILABLE');fork.disabled=true;fork.title='Historical branching requires a separate execution replay contract.';actions.append(first,last,failure,evidence,fork);const position=document.createElement('div');position.className='tt-position';const label=document.createElement('span');label.textContent='TIMELINE';pos.textContent=`EVENT ${index+1} / ${events.length} · RETAINED HISTORY`;position.append(label,pos);timelineBox.append(position,track,actions);shell.append(timelineBox);
    const lower=document.createElement('div');lower.className='tt-lower';const event=document.createElement('section');event.className='tt-event';const eh=document.createElement('h3');eh.textContent=`EVENT DETAILS · ${index+1}/${events.length}`;const pre=document.createElement('pre');pre.textContent=JSON.stringify(current,null,2);event.append(eh,pre);
    const diff=document.createElement('section');diff.className='tt-event';const dh=document.createElement('h3');dh.textContent='DIFF VIEW · PREVIOUS → CURRENT';const list=document.createElement('div');list.className='tt-diff';if(!changes.length){const none=document.createElement('div');none.className='tt-sub';none.textContent=index===0?'Start of retained timeline.':'No reconstructed state fields changed.';list.append(none)}else for(const change of changes){const row=document.createElement('div');row.className='tt-change';const code=document.createElement('code');code.textContent=change.field;const body=document.createElement('span');body.className='tt-removed';body.textContent=`− ${JSON.stringify(change.from)}`;const added=document.createElement('span');added.className='tt-added';added.textContent=`+ ${JSON.stringify(change.to)}`;row.append(code,body,added);list.append(row)}diff.append(dh,list);
    const binding=side.lastElementChild;side.append(diff);
    const log=document.createElement('section');log.className='tt-event';const lh=document.createElement('h3');lh.textContent='EVENT LOG';const rows=document.createElement('div');rows.className='tt-log';
    for(const [i,item] of events.entries()){const row=button(`${String(i+1).padStart(3,'0')}  ${item.event_type}`);row.setAttribute('aria-current',String(i===index));if(isFailure(item))row.className='tt-failure';row.onclick=()=>{index=i;entered=true;render();panel.querySelector('.tt-log [aria-current=true]')?.focus({preventScroll:true})};rows.append(row)}
    log.append(lh,rows);lower.append(log,event,binding);shell.append(lower);
    const selectedRow=rows.querySelector('[aria-current=true]');if(selectedRow)rows.scrollTop=Math.max(0,selectedRow.offsetTop-rows.offsetTop-80);
    first.disabled=last.disabled=!events.length;failure.disabled=!events.some(isFailure);evidence.disabled=!events.some(item=>item.event_type==='evidence.projected');
    const refreshButton=button('REFRESH HISTORY');refreshButton.onclick=refresh;actions.append(refreshButton);
    if(!events.length){const empty=document.createElement('p');empty.className='tt-empty';empty.textContent='No sanitized diagnostic events are retained for this scope. Select Full session or refresh after a mission.';log.append(empty)}
    const note=document.createElement('div');note.className='tt-readonly';note.textContent='READ-ONLY RECONSTRUCTION · Historical inspection never mutates guest evidence, receipts, provider budgets, or the authoritative retained trace.';shell.append(note);
    panel.scrollTop=scroll;
    if(focusLabel){const replacement=[...panel.querySelectorAll('button,input,select')].find(el=>(el.getAttribute('aria-label')||el.textContent)===focusLabel);replacement?.focus({preventScroll:true})}
  }
  function refresh(){const events=timeline();const retained=selectedId?events.findIndex(event=>event.event_id===selectedId):-1;index=retained>=0?retained:events.length-1;render()}

  tab.onclick=()=>{root.dataset.view='timetravel';for(const item of root.querySelectorAll('.panel'))item.hidden=item!==panel;for(const item of root.querySelectorAll('[data-tab]'))item.setAttribute('aria-selected',String(item===tab));queueMicrotask(refresh)};
  return {refresh,destroy(){destroyed=true;tab.remove();panel.remove();root.querySelector('#mc-timetravel-style')?.remove();}};
}
