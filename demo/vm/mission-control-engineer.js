import {mountMissionControl as mountCore} from './mission-control.js';

const PREFIX='\x1b]777;RESIDUAL;';
const FAILURE_HELP={
  provider_exception:['Provider adapter failed before a candidate reached RESIDUAL.','The worker boundary raised an unexpected adapter exception, so the Harness accepted nothing.','Retry once after reconnecting. If it repeats, inspect the provider tab and retained trace; this is an integration defect, not a successful build.'],
  provider_error:['Provider request failed before a usable candidate reached RESIDUAL.','The provider boundary returned a safe generic failure code; no provider error body or credential was copied into evidence.','Check model availability/account allowance in the provider tab, then retry.'],
  provider_request_failed:['Provider rejected or failed the model request.','The SDK call failed after authorization, before RESIDUAL received a candidate.','Check model/account allowance in the provider tab or choose another available model.'],
  provider_model_unavailable:['The selected model is not available in this provider session.','Mission Control checked the provider model catalog before dispatch and refused to guess a replacement model.','Choose an available model and resend the preserved prompt.'],
  provider_authorization_failed:['Provider authorization or allowance was insufficient for this call.','Sign-in succeeded, but the model request was not authorized or billable for this account.','Return to provider setup, confirm the account/allowance, then retry.'],
  provider_protocol_invalid:['The model replied, but not in RESIDUAL’s required worker envelope.','Fail-closed protocol validation rejected prose or malformed tool arguments before the guest could treat them as a candidate.','Retry or select a stronger tool-capable model.'],
  provider_timeout:['The provider did not return within the bounded request window.','RESIDUAL timed out rather than wait indefinitely or infer success. A timed-out remote request may still be billed.','Check the provider tab, then retry only if the prior request is no longer running.'],
  browser_response_invalid:['The browser-to-guest provider response was malformed or incomplete.','The mailbox reader could not establish a valid bounded response after retries, so the Harness accepted nothing.','Retry once. If it repeats, inspect Activity/Terminal; this indicates a transport defect.'],
  provider_budget_exhausted:['The mission exhausted its allowed provider-call budget.','RESIDUAL refused an additional dispatch beyond the explicit call ceiling.','Increase the bounded call budget only if the extra call is intentional.'],
  verification_failed:['A candidate was produced but failed verification.','The verifier rejected it; RESIDUAL did not promote the candidate into accepted state.','Inspect the verification event and counterexample, then refine the prompt or retry.'],
  no_verified_candidate:['No candidate satisfied the declared contract.','The run ended without an accepted obligation, so there is no artifact to preview.','Open Activity/Evidence to see whether dispatch, protocol, or verification blocked acceptance.']
};

function parseFrames(text,consume){let cursor=0;while(true){const start=text.indexOf(PREFIX,cursor);if(start<0)return;const end=text.indexOf('\x07',start+PREFIX.length);if(end<0)return;try{const raw=text.slice(start+PREFIX.length,end).replace(/-/g,'+').replace(/_/g,'/');const bin=atob(raw);consume(JSON.parse(new TextDecoder().decode(Uint8Array.from(bin,c=>c.charCodeAt(0)))))}catch{}cursor=end+1}}
function firstFailure(data){const values=Object.values(data?.result?.unresolved||{});const first=values.find(v=>v&&typeof v==='object')||{};let code=typeof first.code==='string'?first.code:'no_verified_candidate';if(code==='invalid_protocol')code='provider_protocol_invalid';const help=FAILURE_HELP[code]||[first.message||'Mission ended without an accepted result.','The retained result contains an unresolved obligation.','Inspect Activity/Evidence for the exact code and retry only after addressing it.'];return {code,title:help[0],why:help[1],next:help[2]}}
function acceptedBuild(data){const bundle=data?.result?.values?.build;return data?.execution==='generated_artifacts'&&data?.status==='passed'&&data?.result?.success===true&&bundle&&Array.isArray(bundle.files)&&bundle.files.length>0}
function latestAssistant(chat){const nodes=chat.querySelectorAll('.bubble.assistant');return nodes.length?nodes[nodes.length-1]:null}
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

export function mountMissionControl(host){
  const core=mountCore(host),root=document.querySelector('#mission-control'),chat=root.querySelector('#mc-chat'),form=root.querySelector('#mc-form');
  const q=id=>root.querySelector('#mc-'+id),details=root.querySelector('#mc-composer details'),consent=q('consent'),consentLabel=q('consent-label'),connect=q('connect');
  if(q('model').value==='gpt-5-nano')q('model').value='openai/gpt-5-nano';
  let setupOpened=false;

  const gate=document.createElement('div');gate.id='mc-provider-gate';gate.className='notice';
  const gateStatus=document.createElement('div');gateStatus.id='mc-provider-gate-status';
  gateStatus.textContent='Builds use your provider. Send will open setup when needed; explicit prompt authorization is required before inference.';
  gate.append(gateStatus);if(consentLabel){consentLabel.style.marginTop='8px';gate.append(consentLabel)}details.before(gate);

  const activity=q('activity-panel'),engineer=document.createElement('details');engineer.open=true;engineer.id='mc-engineer-explain';
  engineer.innerHTML='<summary>Engineering trace · what happened and why</summary><p class="muted">This is a human-readable projection of the real guest/Harness events. It is explanatory, not an additional trust anchor; the retained guest trace remains authoritative.</p><div id="mc-engineer-timeline"></div>';
  const cards=activity.querySelector('.cards');activity.insertBefore(engineer,cards);
  const timeline=engineer.querySelector('#mc-engineer-timeline');
  function explain(title,why,next,code=''){if(timeline.children.length>=80)timeline.firstElementChild?.remove();const d=document.createElement('div');d.className='notice';const h=document.createElement('strong');h.textContent=title+(code?` · ${code}`:'');const p=document.createElement('div');p.textContent='WHY · '+why;const n=document.createElement('div');n.className='muted';n.textContent='NEXT · '+next;d.append(h,p,n);timeline.append(d);timeline.scrollTop=timeline.scrollHeight}
  function system(text){const node=document.createElement('div');node.className='bubble system';node.innerHTML='<span class="meta">SYSTEM</span>';const body=document.createElement('div');body.textContent=text;node.append(body);chat.append(node);chat.scrollTop=chat.scrollHeight}
  function remoteMode(){return ['build','live'].includes(q('mode').value)}
  function providerReady(){return connect.textContent==='Provider connected'}
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

  form.addEventListener('submit',event=>{
    if(!remoteMode())return;
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
  },true);

  function handleFrame(event){if(!event||typeof event.kind!=='string')return;
    if(event.kind==='mission_started')explain('Mission entered the guest','The prompt passed local validation and became a bounded Task in the Linux guest.','Follow Activity for dispatch/verification; Evidence retains the authoritative trace.');
    if(event.kind==='inference_requested')explain('Provider dispatch requested','The Harness still had an unresolved obligation and requested one authorized model call.','The returned value will be checked before it can become an accepted artifact.');
    if(event.kind==='evidence'&&event.data?.kind){const x=LEDGER_EXPLAIN[event.data.kind];if(x)explain(x[0],x[1],x[2],event.data?.data?.code||event.data?.data?.status||'')}
    if(event.kind==='mission_error')explain('Mission aborted without a verified result','The guest reported a terminal execution error before a result could be bound.','Inspect Terminal and retained failure evidence; no success is inferred.','mission_error');
    if(event.kind==='mission_finished'){
      const data=event.data||{};
      if(data.execution==='generated_artifacts'&&!acceptedBuild(data)){
        const fail=firstFailure(data),message=`Build blocked — no artifact was accepted.\n\n${fail.title}\n\nWhy: ${fail.why}\nNext: ${fail.next}`;
        replaceBubble(latestAssistant(chat),message);
        const inline=root.querySelector('#mc-inline-preview');if(inline)inline.remove();
        q('artifacts').hidden=true;q('preview').hidden=true;q('preview').replaceChildren();q('preview-status').textContent='No preview: RESIDUAL did not accept a build artifact.';
        q('verdict').textContent=`BLOCKED · no accepted build artifact · ${fail.code}`;q('answer').textContent=message;q('run-state').textContent=`BLOCKED · ${fail.code} · inspect the explanation below and retained Evidence`;
        explain('Build was not accepted',fail.why,fail.next,fail.code);
      }else if(acceptedBuild(data)){
        explain('Build artifact accepted','The generated bundle passed its declared mechanical contract and is trace-bound.','Interact with the sandboxed preview; code/semantic correctness remains UNKNOWN unless stronger behavioral verification is shown.','PASS');
      }else if(data?.result?.success===false){const fail=firstFailure(data);explain('Mission finished unresolved',fail.why,fail.next,fail.code)}
    }
  }
  return {onOutput(text){core.onOutput(text);parseFrames(text,handleFrame)},connectProvider:core.connectProvider,destroy(){core.destroy()}};
}
