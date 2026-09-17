import {mountMissionControl as mountCore} from './mission-control.js';

const PREFIX='\x1b]777;RESIDUAL;';
const FAILURE_HELP={
  provider_exception:['Provider adapter failed before a candidate reached RESIDUAL.','The worker boundary raised an unexpected adapter exception, so the Harness accepted nothing.','Retry once after reconnecting. If it repeats, inspect the provider tab and retained trace; this is an integration defect, not a successful build.'],
  provider_error:['Provider request failed before a usable candidate reached RESIDUAL.','The provider boundary returned a safe generic failure code; no provider error body or credential was copied into evidence.','Check model availability/account allowance in the provider tab, then retry.'],
  provider_request_failed:['Provider rejected or failed the model request.','The SDK call failed after authorization, before RESIDUAL received a candidate.','Check model/account allowance in the provider tab or choose another available model.'],
  provider_model_unavailable:['The selected model is not available in this provider session.','The provider rejected the selected model or the model could not be routed for this account.','Choose an available model and resend the preserved prompt.'],
  provider_authorization_failed:['Provider authorization or allowance was insufficient for this call.','Sign-in succeeded, but the model request was not authorized or billable for this account.','Return to provider setup, confirm the account/allowance, then retry.'],
  provider_protocol_invalid:['The model replied, but not in RESIDUAL’s required worker envelope.','Fail-closed protocol validation rejected prose or malformed tool arguments before the guest could treat them as a candidate.','Use the live provider stages to see whether decoding failed, then retry or select another tool-capable model.'],
  provider_timeout:['The provider did not return within the bounded request window.','RESIDUAL timed out rather than wait indefinitely or infer success. A timed-out remote request may still be billed.','Check the provider tab, then retry only if the prior request is no longer running.'],
  browser_response_invalid:['The browser-to-guest provider response was malformed or incomplete.','The mailbox reader could not establish a valid bounded response after retries, so the Harness accepted nothing.','Retry once. If it repeats, inspect Activity/Terminal; this indicates a transport defect.'],
  provider_budget_exhausted:['The mission exhausted its allowed provider-call budget.','RESIDUAL refused an additional dispatch beyond the explicit call ceiling.','Increase the bounded call budget only if the extra call is intentional.'],
  verification_failed:['A candidate was produced but failed verification.','The verifier rejected it; RESIDUAL did not promote the candidate into accepted state.','Inspect the verification event and counterexample, then refine the prompt or retry.'],
  no_verified_candidate:['No candidate satisfied the declared contract.','The run ended without an accepted obligation, so there is no artifact to preview.','Open Activity/Evidence to see whether dispatch, protocol, or verification blocked acceptance.']
};

function parseFrames(text,consume){let cursor=0;while(true){const start=text.indexOf(PREFIX,cursor);if(start<0)return;const end=text.indexOf('\x07',start+PREFIX.length);if(end<0)return;try{const raw=text.slice(start+PREFIX.length,end).replace(/-/g,'+').replace(/_/g,'/');const bin=atob(raw);consume(JSON.parse(new TextDecoder().decode(Uint8Array.from(bin,c=>c.charCodeAt(0)))))}catch{}cursor=end+1}}
function firstFailure(data){const values=Object.values(data?.result?.unresolved||{});const first=values.find(v=>v&&typeof v==='object')||{};let code=typeof first.code==='string'?first.code:'no_verified_candidate';if(code==='invalid_protocol')code='provider_protocol_invalid';const help=FAILURE_HELP[code]||[first.message||'Mission ended without an accepted result.','The retained result contains an unresolved obligation.','Inspect Activity/Evidence for the exact code and retry only after addressing it.'];return {code,title:help[0],why:help[1],next:help[2]}}
function acceptedBuild(data){const bundle=data?.result?.values?.build;return data?.execution==='generated_artifacts'&&data?.status==='passed'&&data?.result?.success===true&&bundle&&Array.isArray(bundle.files)&&bundle.files.length>0}
function latestAssistant(chat){const nodes=[...chat.querySelectorAll('.bubble.assistant:not(.mc-pipeline)')];return nodes.length?nodes[nodes.length-1]:null}
function replaceBubble(node,text){const body=node?.querySelector('div');if(body)body.textContent=text}

const LEDGER_EXPLAIN={
  run_started:['Task frozen','The Harness bound the task, limits, and artifact hashes before worker dispatch.','Any later evidence refers back to this frozen start state.'],
  context_plan:['Context plan selected','RESIDUAL chose the bounded evidence/context capsule for this dispatch.','Inspect Evidence to see exactly which frozen artifacts were in scope.'],
  call_reserved:['Provider call reserved','A remote call slot was reserved before I/O because failed requests may still incur cost.','The response still has no authority until protocol parsing and verification pass.'],
  provider_failed:['Provider call failed','The provider/transport ended before a usable candidate was accepted.','Use the safe failure code and provider tab status to choose the next action.'],
  call_completed:['Provider response returned','A bounded provider response arrived and was hash-recorded.','RESIDUAL must still parse the worker protocol and verify any candidate.'],
  verification:['Verifier checked candidate','A declared verifier evaluated the candidate against the obligation contract.','PASS can advance; FAIL/UNKNOWN remains unaccepted.'],
  counterexample:['Candidate rejected','RESIDUAL recorded why the current candidate could not be accepted.','The reason may guide a bounded retry; rejection is not hidden.'],
  obligation_accepted:['Obligation accepted','A candidate passed its declared mechanical verifier and received an acceptance receipt.','This proves the contract pass—not general semantic/code correctness.'],
  station_receipt_issued:['Receipt issued','A receipt bound the accepted value to verifier identity and upstream evidence.','The receipt is inspectable in Evidence.'],
  run_finished:['Run finalized','The Harness recorded a terminal result and trace root.','Mission Control will only call a build successful if an accepted artifact bundle is actually present.']
};
const LEDGER_PIPELINE={
  run_started:['HARNESS','Task frozen','Goal, limits, obligations, and artifact hashes are now bound to the retained trace.'],
  context_plan:['CONTEXT','Evidence capsule selected','The Harness selected the bounded frozen context available to this worker call.'],
  call_reserved:['BUDGET','Provider call reserved','The remote-call slot was charged to the mission budget before network I/O.'],
  provider_failed:['PROVIDER','Provider attempt failed','A typed provider/transport failure was retained; no candidate gained authority.'],
  call_completed:['HARNESS','Provider response ingested','The guest consumed the bounded response and hash-recorded the completed call.'],
  verification:['VERIFIER','Candidate contract check','A declared verifier is checking the candidate; this is not yet acceptance.'],
  counterexample:['VERIFIER','Candidate rejected','The verifier produced a counterexample/rejection that can drive a bounded retry.'],
  obligation_accepted:['VERIFIER','Obligation accepted','The candidate passed the declared mechanical contract and entered accepted state.'],
  station_receipt_issued:['EVIDENCE','Acceptance receipt bound','Receipt identity now binds the accepted value to verifier and upstream evidence.'],
  run_finished:['EVIDENCE','Trace finalized','The Harness recorded the terminal result and trace root.']
};
const PROVIDER_PIPELINE={
  'model selected':['PROVIDER','Model selected',model=>`The provider bridge selected ${model||'the requested model'} without substituting a different model.`],
  'request dispatched':['LLM','Model inference running',model=>`puter.ai.chat() was dispatched${model?` to ${model}`:''}; stream:false, so the bridge is waiting for one normalized response.`],
  'response received':['PROVIDER','Model response received',()=>`Puter returned a normalized response object. The browser bridge is decoding tool/JSON structure.`],
  'envelope decoded':['PROTOCOL','Worker envelope decoded',()=>`The browser boundary validated the exact updates/requests shape. The structured response can now cross into the guest mailbox.`]
};

export function mountMissionControl(host){
  const core=mountCore(host),root=document.querySelector('#mission-control'),chat=root.querySelector('#mc-chat'),form=root.querySelector('#mc-form');
  const q=id=>root.querySelector('#mc-'+id),details=root.querySelector('#mc-composer details'),consent=q('consent'),consentLabel=q('consent-label'),connect=q('connect');
  const initialAssistant=latestAssistant(chat);
  if(q('model').value==='gpt-5-nano')q('model').value='openai/gpt-5.4-nano';
  let setupOpened=false,pipeline=null,pipelineTimer=null;

  const liveStyle=document.createElement('style');
  liveStyle.textContent=`
#mission-control .mc-pipeline{border-color:#2a6940;background:#020b05;max-width:min(94%,820px)}
#mission-control .mc-pipeline-head{display:flex;align-items:center;gap:8px;margin-bottom:8px;color:#c8ffd5}
#mission-control .mc-pipeline-head .muted{font-size:11px}
#mission-control .mc-pipeline-lines{display:grid;gap:5px}
#mission-control .mc-pipeline-line{display:grid;grid-template-columns:20px minmax(64px,auto) 1fr;gap:7px;align-items:start;padding:3px 0;border-bottom:1px solid #102719}
#mission-control .mc-pipeline-line:last-child{border-bottom:0}
#mission-control .mc-pipeline-mark{color:#7ea889;text-align:center}
#mission-control .mc-pipeline-line.active .mc-pipeline-mark,#mission-control .mc-pipeline-line.active .mc-pipeline-title{color:#39ff68}
#mission-control .mc-pipeline-line.failed .mc-pipeline-mark,#mission-control .mc-pipeline-line.failed .mc-pipeline-title{color:#ff9f9f}
#mission-control .mc-pipeline-source{font-size:10px;letter-spacing:.08em;color:#78a786;padding-top:2px}
#mission-control .mc-pipeline-detail{display:block;color:#96ad9c;font-size:11px;margin-top:1px}
#mission-control .mc-pipeline-links{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px}
#mission-control .mc-pipeline-links button{padding:4px 8px;border-radius:999px;font-size:11px}
#mission-control .mc-pipeline-earlier{font-size:11px;color:#6f8b77;margin:3px 0}
`;
  root.append(liveStyle);

  const gate=document.createElement('div');gate.id='mc-provider-gate';gate.className='notice';
  const gateStatus=document.createElement('div');gateStatus.id='mc-provider-gate-status';
  gateStatus.textContent='Builds use your provider. Send will open setup when needed; explicit prompt authorization is required before inference.';
  gate.append(gateStatus);if(consentLabel){consentLabel.style.marginTop='8px';gate.append(consentLabel)}details.before(gate);

  const activity=q('activity-panel'),engineer=document.createElement('details');engineer.open=true;engineer.id='mc-engineer-explain';
  engineer.innerHTML='<summary>Engineering trace · what happened and why</summary><p class="muted">This is a human-readable projection of the real guest/Harness/provider events. It is explanatory, not an additional trust anchor; the retained guest trace remains authoritative.</p><div id="mc-engineer-timeline"></div>';
  const cards=activity.querySelector('.cards');activity.insertBefore(engineer,cards);
  const timeline=engineer.querySelector('#mc-engineer-timeline');
  function explain(title,why,next,code=''){if(timeline.children.length>=80)timeline.firstElementChild?.remove();const d=document.createElement('div');d.className='notice';const h=document.createElement('strong');h.textContent=title+(code?` · ${code}`:'');const p=document.createElement('div');p.textContent='WHY · '+why;const n=document.createElement('div');n.className='muted';n.textContent='NEXT · '+next;d.append(h,p,n);timeline.append(d);timeline.scrollTop=timeline.scrollHeight}
  function system(text){const node=document.createElement('div');node.className='bubble system';node.innerHTML='<span class="meta">SYSTEM</span>';const body=document.createElement('div');body.textContent=text;node.append(body);chat.append(node);chat.scrollTop=chat.scrollHeight}
  function remoteMode(){return ['build','live'].includes(q('mode').value)}
  function providerReady(){return connect.textContent==='Provider connected'}

  function stopPipelineTimer(){if(pipelineTimer){clearInterval(pipelineTimer);pipelineTimer=null}}
  function ensurePipeline(){
    if(pipeline)return pipeline;
    const coreBubble=latestAssistant(chat),node=document.createElement('div'),head=document.createElement('div'),lines=document.createElement('div'),links=document.createElement('div');
    node.className='bubble assistant mc-pipeline';head.className='mc-pipeline-head';lines.className='mc-pipeline-lines';links.className='mc-pipeline-links';
    const title=document.createElement('strong');title.textContent='LIVE PIPELINE';const note=document.createElement('span');note.className='muted';note.textContent='event-backed · only observed stages appear';head.append(title,note);
    for(const [label,tab] of [['Activity','activity'],['Evidence','evidence'],['Files','files']]){const b=document.createElement('button');b.type='button';b.textContent=label;b.onclick=()=>root.querySelector(`[data-tab="${tab}"]`)?.click();links.append(b)}
    node.append(head,lines,links);
    if(coreBubble&&coreBubble!==initialAssistant){coreBubble.hidden=true;chat.insertBefore(node,coreBubble)}else chat.append(node);
    pipeline={node,lines,coreBubble:coreBubble&&coreBubble!==initialAssistant?coreBubble:null,active:null,count:0,earlier:0,tick:0};
    pipelineTimer=setInterval(()=>{if(!pipeline?.active)return;pipeline.tick=(pipeline.tick+1)%3;pipeline.active.mark.textContent='▸'+'.'.repeat(pipeline.tick+1)},360);
    chat.scrollTop=chat.scrollHeight;
    return pipeline;
  }
  function completeActive(failed=false){if(!pipeline?.active)return;pipeline.active.row.classList.remove('active');if(failed)pipeline.active.row.classList.add('failed');pipeline.active.mark.textContent=failed?'×':'✓';pipeline.active=null}
  function trimPipeline(){if(!pipeline)return;while(pipeline.lines.querySelectorAll('.mc-pipeline-line').length>7){pipeline.lines.querySelector('.mc-pipeline-line')?.remove();pipeline.earlier++}let prior=pipeline.node.querySelector('.mc-pipeline-earlier');if(pipeline.earlier){if(!prior){prior=document.createElement('div');prior.className='mc-pipeline-earlier';pipeline.lines.before(prior)}prior.textContent=`+${pipeline.earlier} earlier observed stage${pipeline.earlier===1?'':'s'} · open Activity/Evidence for the full trace`}}
  function pipelineStage(source,title,detail,failed=false){
    const p=ensurePipeline();completeActive(false);const row=document.createElement('div'),mark=document.createElement('span'),src=document.createElement('span'),body=document.createElement('span'),name=document.createElement('strong'),small=document.createElement('span');
    row.className='mc-pipeline-line active';mark.className='mc-pipeline-mark';src.className='mc-pipeline-source';body.className='mc-pipeline-title';small.className='mc-pipeline-detail';mark.textContent='▸.';src.textContent=source;name.textContent=title;small.textContent=detail;body.append(name,small);row.append(mark,src,body);p.lines.append(row);p.active={row,mark};p.count++;trimPipeline();if(failed)completeActive(true);chat.scrollTop=chat.scrollHeight;
  }
  function finishPipeline(ok,title,detail){if(!pipeline)return;completeActive(!ok);const p=pipeline;pipelineStage(ok?'RESULT':'BLOCKED',title,detail,!ok);if(ok)completeActive(false);stopPipelineTimer();if(p.coreBubble)p.coreBubble.hidden=false;pipeline=null;chat.scrollTop=chat.scrollHeight}
  function schedulePipeline(){queueMicrotask(()=>{if(!pipeline)pipelineStage('UI','Prompt queued','Mission Control accepted the send action and is waiting for guest admission.')})}

  function updateGate(){
    gate.hidden=!remoteMode();if(!remoteMode())return;
    if(!providerReady()){
      gateStatus.textContent=setupOpened
        ? 'Provider setup opened · complete SDK load/sign-in in the new tab. Your prompt is preserved and unsent.'
        : 'Provider not connected · Send opens provider setup and keeps your prompt here.';
      return;
    }
    setupOpened=false;
    if(!consent.checked){gateStatus.textContent='Provider connected · authorize this specific prompt below, then Send.';return}
    gateStatus.textContent='Provider connected + prompt authorized · ready to dispatch when you Send.';
  }
  new MutationObserver(updateGate).observe(connect,{childList:true,subtree:true});q('mode').addEventListener('change',updateGate);consent.addEventListener('change',updateGate);updateGate();

  const providerState=q('provider-state');
  function projectProviderState(){
    const text=providerState.textContent||'';if(!text.startsWith('Provider stage · '))return;
    const parts=text.split(' · '),name=parts[1]||'',model=parts[2]||'';const stage=PROVIDER_PIPELINE[name];if(!stage)return;
    const [source,title,detail]=stage;pipelineStage(source,title,detail(model));
    if(name==='request dispatched')explain('Provider request dispatched','The Puter SDK accepted the authorized non-stream request. No candidate exists yet.','Wait for the normalized response; if it fails, the next provider stage identifies the boundary.');
    if(name==='response received')explain('Provider response received','Puter returned a normalized response object to the browser bridge.','The bridge must decode an exact worker envelope before anything reaches the guest.');
    if(name==='envelope decoded')explain('Worker envelope decoded','The browser boundary established an exact updates/requests envelope without granting it authority.','The structured response now crosses the guest mailbox and still requires Harness verification.');
  }
  new MutationObserver(projectProviderState).observe(providerState,{childList:true,subtree:true,characterData:true});

  form.addEventListener('submit',event=>{
    if(!remoteMode()){schedulePipeline();return}
    if(!providerReady()){
      event.preventDefault();event.stopImmediatePropagation();
      setupOpened=true;
      gateStatus.textContent='Provider setup opened · complete SDK load/sign-in in the new tab. Your prompt is preserved and unsent.';
      system('Provider setup opened. Your prompt is still in the composer; no inference was sent. Complete sign-in, authorize this prompt, then Send again.');
      explain('Authorization gate stopped dispatch','The mission requires a remote provider, but no live provider session was connected.','Complete provider setup; the prompt remains unsent and editable.','provider_disconnected');
      core.connectProvider();updateGate();return;
    }
    if(!consent.checked){
      event.preventDefault();event.stopImmediatePropagation();
      gateStatus.textContent='Provider connected, but this prompt is not authorized yet. Check the authorization box; nothing was sent.';
      system('Provider is connected, but this prompt still needs explicit authorization. Nothing was sent.');
      explain('Consent gate stopped dispatch','Provider connectivity is not permission to send the current prompt/source snapshots.','Review the authorization text, check the box, then Send.','authorization_required');
      consent.focus();return;
    }
    schedulePipeline();
  },true);

  function handleFrame(event){if(!event||typeof event.kind!=='string')return;
    if(event.kind==='mission_started'){
      pipelineStage('GUEST','Mission admitted','The validated request entered the persistent Linux guest and became a bounded workbench mission.');
      explain('Mission entered the guest','The prompt passed local validation and became a bounded Task in the Linux guest.','Follow Activity for dispatch/verification; Evidence retains the authoritative trace.');
    }
    if(event.kind==='inference_requested'){
      pipelineStage('BRIDGE','Provider request framed','The guest requested one authorized provider call with bounded messages, model, and output budget.');
      explain('Provider dispatch requested','The Harness still had an unresolved obligation and requested one authorized model call.','The returned value will be checked before it can become an accepted artifact.');
    }
    if(event.kind==='evidence'&&event.data?.kind){
      const x=LEDGER_EXPLAIN[event.data.kind];if(x)explain(x[0],x[1],x[2],event.data?.data?.code||event.data?.data?.status||'');
      const p=LEDGER_PIPELINE[event.data.kind];if(p){let detail=p[2];const code=event.data?.data?.code||event.data?.data?.status;if(code)detail+=` · ${code}`;pipelineStage(p[0],p[1],detail,event.data.kind==='provider_failed')}
    }
    if(event.kind==='mission_error'){
      explain('Mission aborted without a verified result','The guest reported a terminal execution error before a result could be bound.','Inspect Terminal and retained failure evidence; no success is inferred.','mission_error');
      finishPipeline(false,'Mission aborted','The guest terminated before a trace-bound result could be accepted. Open Activity or Terminal for the failure path.');
    }
    if(event.kind==='mission_finished'){
      const data=event.data||{};
      if(data.execution==='generated_artifacts'&&!acceptedBuild(data)){
        const fail=firstFailure(data),message=`Build blocked — no artifact was accepted.\n\n${fail.title}\n\nWhy: ${fail.why}\nNext: ${fail.next}`;
        replaceBubble(latestAssistant(chat),message);
        const inline=root.querySelector('#mc-inline-preview');if(inline)inline.remove();
        q('artifacts').hidden=true;q('preview').hidden=true;q('preview').replaceChildren();q('preview-status').textContent='No preview: RESIDUAL did not accept a build artifact.';
        q('verdict').textContent=`BLOCKED · no accepted build artifact · ${fail.code}`;q('answer').textContent=message;q('run-state').textContent=`BLOCKED · ${fail.code} · inspect the explanation below and retained Evidence`;
        explain('Build was not accepted',fail.why,fail.next,fail.code);
        finishPipeline(false,'Build blocked',`${fail.code} · no artifact was accepted.`);
      }else if(acceptedBuild(data)){
        explain('Build artifact accepted','The generated bundle passed its declared mechanical contract and is trace-bound.','Interact with the sandboxed preview; code/semantic correctness remains UNKNOWN unless stronger behavioral verification is shown.','PASS');
        finishPipeline(true,'Artifact bundle ready','Accepted files were persisted under the mission directory and the sandbox preview can now render them.');
      }else if(data?.result?.success===false){const fail=firstFailure(data);explain('Mission finished unresolved',fail.why,fail.next,fail.code);finishPipeline(false,'Mission unresolved',`${fail.code} · no verified result was accepted.`)}
      else finishPipeline(true,'Result trace-bound','The mission finalized with a retained result/trace binding.');
    }
  }
  return {onOutput(text){core.onOutput(text);parseFrames(text,handleFrame)},connectProvider:core.connectProvider,destroy(){stopPipelineTimer();core.destroy()}};
}