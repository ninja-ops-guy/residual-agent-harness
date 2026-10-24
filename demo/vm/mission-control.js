import {ProviderSession, validId, validRequest, bounded} from './provider-session.js';
import {renderPreview} from './mission-preview.js';

// UI projections are not an independent trust anchor. The retained guest trace
// and verify-trace command remain the source of integrity evidence.
// Browser-side evidence verification and rendering. The guest projects each
// retained ledger event inside canonical({"data":event,"kind":"evidence",
// "mission_id":...}) frames, so the exact hashed bytes are recoverable from the
// raw frame without re-serializing (which could change number formatting).
// This is an inspection aid layered on the projection: the guest trace.jsonl
// and `verify-trace` remain authoritative.
export function evidenceEventCanonical(rawFrame, missionId) {
  const prefix = '{"data":', suffix = ',"kind":"evidence","mission_id":"' + missionId + '"}';
  if (typeof rawFrame !== 'string' || !rawFrame.startsWith(prefix) || !rawFrame.endsWith(suffix)) return null;
  return rawFrame.slice(prefix.length, rawFrame.length - suffix.length);
}
export async function sha256Hex(text) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, '0')).join('');
}
export async function verifyEvidenceChain(rawFrames, missionId, traceRoot) {
  let head = '0'.repeat(64), count = 0;
  for (const raw of rawFrames) {
    const canon = evidenceEventCanonical(raw, missionId);
    if (canon === null) return { ok: false, reason: 'projection framing changed; local recompute unavailable' };
    let event;
    try { event = JSON.parse(canon); } catch { return { ok: false, reason: 'unparseable event bytes' }; }
    if (!/^[0-9a-f]{64}$/.test(event.sha256 || '')) return { ok: false, reason: `event ${count} is missing its digest` };
    if (event.previous !== head) return { ok: false, reason: `chain link broken at event ${event.seq}` };
    if (await sha256Hex(canon) !== event.sha256) return { ok: false, reason: `digest mismatch at event ${event.seq}` };
    head = event.sha256; count++;
  }
  if (!count) return { ok: false, reason: 'no evidence events' };
  if (traceRoot && head !== traceRoot) return { ok: false, reason: 'chain head differs from the bound result trace_root' };
  return { ok: true, count, head };
}
const EV_SHORT = value => (typeof value === 'string' && /^[0-9a-f]{64}$/.test(value)) ? value.slice(0, 12) + '\u2026' : String(value);
function describeEvidence(event) {
  const d = event && event.data || {};
  switch (event.kind) {
    case 'run_started': return { title: 'Run started', tone: 'pass', body: `task ${d.task_id} · mode ${d.mode} · ${Object.keys(d.artifact_hashes || {}).length} frozen artifacts` };
    case 'structural_plan': return { title: 'Structural plan', body: `applicable=${d.applicable}` };
    case 'context_plan': return { title: 'Context plan', body: `${d.plan} · role ${d.role} · obligations ${(d.obligation_ids || []).join(', ')}` };
    case 'call_reserved': return { title: 'Provider call dispatched', body: `${d.provider} · ${d.request_bytes} bytes · packet ${EV_SHORT(d.packet_sha256)} · obligations ${(d.obligation_ids || []).join(', ')}` };
    case 'call_completed': return { title: 'Model response received', body: `${Math.round(d.elapsed_ms || 0)} ms · finish=${d.finish_reason} · tokens ${d.usage?.input_tokens ?? '?'} in / ${d.usage?.output_tokens ?? '?'} out · response ${EV_SHORT(d.response_sha256)}` };
    case 'verification': return { title: d.status === 'pass' ? 'Verifier · PASS' : `Verifier · ${String(d.status || '').toUpperCase()}`, tone: d.status === 'pass' ? 'pass' : 'fail', body: `obligation ${d.obligation_id} · code ${d.code}` };
    case 'counterexample': return { title: 'Candidate rejected', tone: 'fail', body: `obligation ${d.obligation_id} · ${d.code}` };
    case 'obligation_accepted': return { title: 'Obligation accepted', tone: 'pass', body: `${d.obligation_id} · source ${d.source} · value ${EV_SHORT(d.receipt?.value_sha256)}` };
    case 'station_receipt_issued': return { title: 'Receipt issued', body: `${d.obligation_id} · receipt ${EV_SHORT(d.receipt?.receipt_hash)}` };
    case 'provider_failed': return { title: 'Provider call failed', tone: 'fail', body: `role ${d.role} · ${d.code}` };
    case 'budget_blocked': return { title: 'Dispatch blocked by budget', tone: 'fail', body: `role ${d.role} · request ${d.request_bytes} bytes` };
    case 'evidence_requested': return { title: 'Worker requested evidence', body: `${d.artifact_id} lines ${d.start_line}\u2013${d.end_line}` };
    case 'evidence_denied': return { title: 'Evidence request denied', tone: 'fail', body: `obligation ${d.obligation_id} · ${d.code}` };
    case 'run_finished': return { title: 'Run finished', tone: d.success ? 'pass' : 'fail', body: `success=${d.success} · result ${EV_SHORT(d.result_sha256)}` };
    default: return { title: String(event.kind || 'event'), body: '' };
  }
}
function evSection(parent, label, text, verify) {
  const p = document.createElement('p'); p.className = 'mc-ev-label'; p.textContent = label;
  const pre = document.createElement('pre'); pre.textContent = text;
  parent.append(p, pre);
  if (!verify || !/^[0-9a-f]{64}$/.test(verify.expected || '')) return;
  const button = document.createElement('button'); button.type = 'button'; button.className = 'mc-ev-verify';
  button.textContent = 'Recompute hash in browser';
  button.onclick = async () => {
    button.disabled = true;
    try {
      const input = verify.kind === 'raw' ? text : JSON.stringify(text);
      const ok = await sha256Hex(input) === verify.expected;
      button.textContent = ok ? '\u2713 matches the recorded hash' : '\u2717 MISMATCH \u2014 does not match the recorded hash';
      button.classList.add(ok ? 'mc-ev-pass' : 'mc-ev-fail');
    } catch { button.textContent = 'local recompute unavailable'; }
  };
  parent.append(button);
}
export function renderEvidenceEvent(event) {
  const d = event && event.data || {};
  const info = describeEvidence(event);
  const det = document.createElement('details'), sum = document.createElement('summary');
  sum.textContent = `${event.seq} · ${info.title}${info.body ? ' \u2014 ' + info.body : ''}`;
  if (info.tone === 'pass') sum.classList.add('mc-ev-pass');
  if (info.tone === 'fail') sum.classList.add('mc-ev-fail');
  det.append(sum);
  if (typeof d.goal === 'string') evSection(det, 'Mission goal bound at run start \u00b7 exact user prompt', d.goal);
  if (d.packet && typeof d.packet === 'object') {
    for (const ob of d.packet.obligations || []) evSection(det, `Exact instruction sent to the model · obligation ${ob.id}`, String(ob.instruction || ''));
    for (const ex of d.packet.evidence || []) evSection(det, `Frozen evidence sent to the model · ${ex.artifact_id} lines ${ex.start_line}\u2013${ex.end_line}`, String(ex.text || ''), { kind: 'raw', expected: ex.excerpt_sha256 });
  }
  if (typeof d.response_text === 'string') evSection(det, 'Exact model response received by the Harness', d.response_text, { kind: 'canonical-string', expected: d.response_sha256 });
  if (event.kind === 'verification' && typeof d.message === 'string' && d.message) evSection(det, 'Verifier message', d.message);
  if (event.kind === 'obligation_accepted' && d.value !== undefined) evSection(det, 'Accepted candidate value · bound to the receipt', JSON.stringify(d.value, null, 2));
  const raw = document.createElement('details'), rs = document.createElement('summary'), rp = document.createElement('pre');
  rs.textContent = 'Raw hash-chained ledger event'; rp.textContent = JSON.stringify(event, null, 2);
  raw.append(rs, rp); det.append(raw);
  return det;
}
export function mountMissionControl(host) {
  const element = document.createElement('section');
  element.id = 'mission-control'; element.dataset.view = 'chat';
  element.innerHTML = `<style>
#mission-control{--g:#39ff68;--g2:#72ff8d;--panel:#020902;--border:#285d32;--muted:#68a975;--white:#d8ffe0;position:fixed;inset:0;z-index:100;background:#000;color:var(--g2);font:14px/1.5 ui-monospace,monospace;display:flex;flex-direction:column;box-sizing:border-box}
#mission-control *{box-sizing:border-box}#mission-control header{display:flex;align-items:center;gap:10px;padding:10px 16px;border-bottom:1px solid #235331;flex-wrap:wrap;background:#000}
#mission-control h1{font-size:16px;margin:0;letter-spacing:.18em}#mission-control .muted{color:var(--muted)}#mission-control .spacer{flex:1}
#mission-control button,#mission-control select,#mission-control textarea,#mission-control input{font:inherit;background:#030b04;color:var(--white);border:1px solid var(--border);border-radius:0;padding:8px}
#mission-control button{cursor:pointer}#mission-control button:disabled{opacity:.45;cursor:not-allowed}#mission-control button.primary{background:#39ff68;color:#000;font-weight:700}
#mission-control .tabs{display:flex;gap:4px;overflow:auto;padding:7px 10px;border-bottom:1px solid #153823;background:#020604}#mission-control .tabs button{white-space:nowrap;padding:6px 11px}#mission-control .tabs button[aria-selected=true]{background:#12351d;color:#b9ffca;border-color:#39ff68}
#mission-control main{flex:1;min-height:0;overflow:hidden;max-width:1180px;width:100%;margin:auto}#mission-control .panel{height:100%;overflow:auto;padding:16px}#mission-control .panel[hidden]{display:none!important}
#mission-control[data-view=terminal]{bottom:auto;background:transparent}#mission-control[data-view=terminal] main{display:none}#mission-control[data-view=terminal] .tabs{background:#000}
#mc-chat-panel{display:flex;flex-direction:column!important;padding:0!important}#mc-chat{flex:1;overflow:auto;padding:18px max(16px,calc((100% - 900px)/2));display:flex;flex-direction:column;gap:12px}
#mission-control .bubble{max-width:88%;border:1px solid #1d472a;padding:11px 13px;white-space:pre-wrap;overflow-wrap:anywhere}#mission-control .bubble.user{align-self:flex-end;background:#0b2513;color:#e0ffe7}#mission-control .bubble.assistant{align-self:flex-start;background:#041008}#mission-control .bubble.system{align-self:center;max-width:96%;color:#a9c7b0;background:#020704;border-style:dashed}
#mission-control .bubble .meta{display:block;color:#79a987;font-size:11px;margin-bottom:5px;text-transform:uppercase;letter-spacing:.08em}
#mc-composer{border-top:1px solid #153823;padding:10px max(12px,calc((100% - 900px)/2));background:#000;position:sticky;bottom:0}#mc-composer textarea{width:100%;resize:vertical;max-height:180px}#mission-control .composer-row{display:flex;gap:8px;align-items:flex-end}#mission-control .composer-row textarea{flex:1}#mission-control .composer-row button{min-width:78px;height:42px}
#mission-control details{border:1px solid #1c4328;padding:9px;margin:8px 0}#mission-control summary{cursor:pointer;color:#a8ffbf}#mission-control label{display:block;margin:8px 0 4px}#mission-control .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}#mission-control .row>label{flex:1;min-width:180px}#mission-control input[type=checkbox]{width:17px;height:17px;vertical-align:middle}
#mission-control .notice{border-left:3px solid #39ff68;padding:9px 12px;background:#06130a;white-space:pre-wrap;overflow-wrap:anywhere}#mission-control pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:480px;overflow:auto;font:12px/1.55 monospace}#mission-control a{color:#8effa8}
#mission-control .provider-guide{border:1px solid var(--g);background:#020902;padding:14px;margin:0 0 10px}#mission-control .provider-guide h2{font-size:15px;color:#fff;margin:0 0 6px}#mission-control .provider-steps{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:12px 0}#mission-control .provider-step{border:1px solid var(--border);padding:9px;color:var(--muted)}#mission-control .provider-step b{display:block;color:var(--g);font-size:11px;margin-bottom:3px}#mission-control .provider-guide-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}#mission-control #mc-provider-frame{height:250px;margin-top:12px;border:1px solid var(--border);background:#000}
#mission-control .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}#mission-control .cards details{margin:0}#mc-artifact-list{display:grid;gap:7px;margin:8px 0}#mc-artifact-list .artifact{display:flex;gap:8px;align-items:center;justify-content:space-between;border:1px solid #1c4328;padding:8px;border-radius:8px}
#mission-control .preview-shell{border:1px solid #2a6940;border-radius:10px;overflow:hidden;background:#fff;margin-top:10px}#mission-control .preview-controls{display:flex;gap:8px;align-items:center;justify-content:space-between;padding:7px 9px;background:#06130a;color:#a2b8a8}#mission-control iframe{display:block;width:100%;height:420px;border:0;background:#fff}
#mc-inline-preview{margin-top:10px;min-width:min(760px,82vw)}
#mission-control .mc-ev-pass{color:#39ff68}#mission-control .mc-ev-fail{color:#ff9f9f}#mission-control .mc-ev-label{color:#79a987;font-size:11px;text-transform:uppercase;letter-spacing:.08em;margin:8px 0 2px}#mission-control .mc-ev-verify{font-size:11px;padding:3px 8px;margin:2px 0}#mission-control .mc-ev-chain{border:1px solid #285d32;padding:9px;margin:0 0 10px;background:#041008;white-space:pre-wrap;overflow-wrap:anywhere}#mc-inline-preview iframe{height:360px}#mission-control [hidden]{display:none!important}
@media(max-width:600px){#mission-control header{padding:8px}#mission-control h1{font-size:14px}#mc-chat{padding:12px 10px}#mc-composer{padding:8px}#mission-control .bubble{max-width:94%}#mission-control .cards{grid-template-columns:1fr 1fr}#mission-control iframe{height:360px}#mc-inline-preview{min-width:0;width:100%}#mission-control .preview-controls{align-items:flex-start;flex-direction:column}#mission-control .provider-steps{grid-template-columns:1fr}}
</style>
<header><h1>RESIDUAL</h1><span class="muted">MISSION CONTROL</span><span class="spacer"></span><button id="mc-connect">Connect provider</button><button id="mc-restart" type="button" hidden>Restart guest</button><span id="mc-runtime" class="muted">Guest starting…</span></header>
<nav class="tabs" aria-label="Mission Control views"><button id="mc-mission" data-tab="chat" aria-selected="true">Chat</button><button data-tab="activity" aria-selected="false">Activity</button><button data-tab="evidence" aria-selected="false">Evidence <span id="mc-count">0</span></button><button data-tab="files" aria-selected="false">Files</button><button id="mc-terminal" data-tab="terminal" aria-selected="false">Terminal</button></nav>
<main>
<section id="mc-chat-panel" class="panel"><div id="mc-chat"><div class="bubble assistant"><span class="meta">RESIDUAL</span>Give the harness a job. I’ll run it in the Linux guest, verify what can be verified, and keep the execution details in the background tabs.</div></div>
<form id="mc-form"><div id="mc-composer"><section id="mc-provider-guide" class="provider-guide" hidden><h2>Connect Puter without leaving the lab</h2><div class="muted">RESIDUAL embeds provider setup here, outside the isolated VM runtime. Puter authentication may use its secure popup, but Mission Control stays open and your draft remains untouched.</div><div class="provider-steps"><div class="provider-step"><b>01 · LOAD</b>Load the provider SDK only after you choose to connect.</div><div class="provider-step"><b>02 · AUTHORIZE</b>Sign in directly with Puter. Credentials never enter RESIDUAL.</div><div class="provider-step"><b>03 · CONSENT</b>Approve this prompt before any model request is sent.</div></div><div class="provider-guide-actions"><button id="mc-provider-start" type="button" class="primary">Start guided setup</button><button id="mc-provider-cancel" type="button">Not now</button><span id="mc-provider-guide-state" class="muted">Nothing loaded yet.</span></div><iframe id="mc-provider-frame" title="Embedded Puter provider setup" credentialless hidden></iframe></section><div class="composer-row"><textarea id="mc-prompt" rows="2" maxlength="4000" placeholder="Build a calculator" required></textarea><button id="mc-run" class="primary" disabled>Send</button><button id="mc-stop" type="button" disabled>Stop</button></div>
<details><summary>Run controls</summary><div class="row"><label>Execution<select id="mc-mode"><option value="build" selected>Build app / deliverable · real provider</option><option value="live">Source-grounded answer / review</option><option value="audit">Repository audit · no model</option></select></label><label>Call budget<select id="mc-budget"><option value="1">Quick · 1</option><option value="2" selected>Bounded · 2</option><option value="3">Repair · 3</option></select></label></div><label id="mc-files-label" for="mc-files">Optional reference repository paths</label><textarea id="mc-files" rows="2" placeholder="README.md\nresidual/engine.py"></textarea><label for="mc-required">Required literal text · one per line (optional)</label><textarea id="mc-required" rows="2" placeholder="Calculator"></textarea><div class="row"><label>Model<input id="mc-model" value="gpt-5-nano" maxlength="96"></label><label>Max output tokens<input id="mc-tokens" type="number" min="256" max="8192" value="8192"></label></div><label id="mc-consent-label"><input type="checkbox" id="mc-consent"> I authorize this prompt and selected source snapshots to my provider. Provider charges may apply.</label></details></div></form></section>
<section id="mc-activity-panel" class="panel" hidden><h2>Background activity</h2><div id="mc-provider-state" class="notice" role="status">Builds and live prompts require a provider connection. Repository audit runs locally.</div><p id="mc-run-state" class="notice" role="status">Waiting for a mission.</p><div class="cards"><details open><summary>Mission</summary><p>Validated prompt, frozen sources and explicit checks become a real Task.</p></details><details><summary>Workers</summary><p>Bounded Harness dispatch and retry/counterexample feedback.</p></details><details><summary>Verifiers</summary><p>Mechanical artifact/source contracts. Semantic/code correctness stays UNKNOWN.</p></details><details><summary>Integration</summary><p>Accepted build files land only under the mission artifact directory.</p></details><details><summary>Policy / runtime</summary><p>Explicit consent plus source/call/token/time/file limits. No scripted model fallback.</p></details></div></section>
<section id="mc-evidence-panel" class="panel" hidden><h2>Evidence and verification</h2><p class="muted">Hash-chained guest ledger events. Content-retaining events show the exact goal, dispatched packet, and model response, with in-browser hash recomputation. This panel is an inspection aid; the guest trace.jsonl and verify-trace remain authoritative.</p><section id="mc-result" hidden><p id="mc-verdict"></p><pre id="mc-answer"></pre><details id="mc-citations-box" hidden><summary>Checked source quotations</summary><pre id="mc-citations"></pre></details><p id="mc-path"></p><button id="mc-download" type="button">Download run evidence JSON</button><details open><summary>Metrics, receipts and result binding</summary><pre id="mc-json"></pre></details></section><details open><summary>Retained-ledger events</summary><div id="mc-events"></div></details></section>
<section id="mc-files-panel" class="panel" hidden><h2>Generated files</h2><p class="muted">Files are saved in the guest and downloadable here. HTML apps can run in an opaque-origin sandbox with network access blocked. Previewing is not semantic verification.</p><section id="mc-artifacts" hidden><div id="mc-artifact-list"></div></section><p id="mc-preview-status" class="notice">No preview yet.</p><div id="mc-preview" class="preview-shell" hidden></div></section>
</main>`;
  document.body.append(element);
  const $ = id => element.querySelector('#mc-' + id);
  let active = null, result = null, events = [], rawFrames = [], carry = '', completed = false, running = false, currentAssistant = null;
  const provider = new ProviderSession((status, message) => { $('provider-state').textContent = message; $('provider-guide-state').textContent = message; $('connect').textContent = status === 'connected' ? 'Provider connected ✓' : 'Connect Puter'; if(status === 'connected') $('provider-guide').hidden = true; });
  const panels = ['chat','activity','evidence','files'];
  function selectTab(name) {
    const terminal = name === 'terminal'; element.dataset.view = terminal ? 'terminal' : name;
    for (const key of panels) $(`${key}-panel`).hidden = terminal || key !== name;
    element.querySelectorAll('[data-tab]').forEach(button => button.setAttribute('aria-selected', String(button.dataset.tab === name)));
    if (terminal) host.focus();
  }
  element.querySelectorAll('[data-tab]').forEach(button => button.onclick = () => selectTab(button.dataset.tab));
  function connectProvider() { selectTab('chat'); $('provider-guide').hidden = false; $('provider-start').focus(); }
  function startProviderSetup() { try { const frame=$('provider-frame');frame.hidden=false;provider.open(frame);$('provider-start').hidden=true; } catch { $('provider-guide-state').textContent='This browser could not create the private provider channel. No prompt was sent.'; } }
  function runtimeHealth() { const value = typeof host.health === 'function' ? host.health() : (host.ready() ? 'ready' : 'starting'); return value === 'ready' || value === 'poisoned' ? value : 'starting'; }
  function guestReady() { return runtimeHealth() === 'ready'; }
  $('connect').onclick = connectProvider;
  $('provider-start').onclick = startProviderSetup;
  $('provider-cancel').onclick = () => { $('provider-guide').hidden = true; $('prompt').focus(); };
  $('restart').onclick = () => { if (active || running || typeof host.restart !== 'function') return; provider.end(); $('restart').disabled = true; $('runtime').textContent = 'RESTARTING GUEST'; try { host.restart(); } catch { $('runtime').textContent = 'GUEST RESTART FAILED'; $('restart').disabled = false; } };
  function bubble(kind, text) { const node = document.createElement('div'); node.className = `bubble ${kind}`; const meta = document.createElement('span'); meta.className = 'meta'; meta.textContent = kind === 'user' ? 'YOU' : kind === 'assistant' ? 'RESIDUAL' : 'SYSTEM'; const body = document.createElement('div'); body.textContent = text; node.append(meta, body); $('chat').append(node); $('chat').scrollTop = $('chat').scrollHeight; return {node, body}; }
  function setAssistant(text) { if (!currentAssistant) currentAssistant = bubble('assistant', text); else currentAssistant.body.textContent = text; $('chat').scrollTop = $('chat').scrollHeight; }
  function reset(mid) { active = mid; result = null; events = []; rawFrames = []; completed = false; currentAssistant = null; $('events').replaceChildren(); $('count').textContent = '0'; $('result').hidden = true; $('artifacts').hidden = true; $('artifact-list').replaceChildren(); $('citations-box').hidden = true; $('citations').textContent = ''; $('preview').hidden = true; $('preview').replaceChildren(); $('preview-status').textContent = 'No preview yet.'; }
  function state(text) { $('run-state').textContent = text; if (active && !completed) setAssistant(text); }
  function downloadGenerated(path, content) { const url = URL.createObjectURL(new Blob([content], {type:'text/plain;charset=utf-8'})); const a = document.createElement('a'); a.href = url; a.download = path.split('/').pop() || 'artifact.txt'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
  function renderArtifacts(bundle) { $('artifact-list').replaceChildren(); if (!bundle || !Array.isArray(bundle.files)) { $('artifacts').hidden = true; return; } $('artifacts').hidden = false; for (const file of bundle.files) { const row = document.createElement('div'), name = document.createElement('code'), button = document.createElement('button'); row.className='artifact'; name.textContent=file.path; button.type='button'; button.textContent='Download'; button.onclick=()=>downloadGenerated(file.path,file.content); row.append(name,button); $('artifact-list').append(row); } }
  function inlinePreview(bundle, targetBubble) { const shell = document.createElement('div'); shell.id = 'mc-inline-preview'; shell.className = 'preview-shell'; targetBubble.node.append(shell); renderPreview(shell, bundle, {frameId:'mc-inline-preview-frame'}); }
  function consume(event, rawFrame) {
    if (!event || !validId(event.mission_id)) return;
    if (event.kind === 'mission_started' && !active) { reset(event.mission_id); bubble('system', `CLI mission ${event.mission_id} projected into Mission Control.`); }
    if (event.mission_id !== active) return;
    const data = event.data;
    if (event.kind === 'mission_started') state(`Running ${event.mission_id} in the Linux guest…`);
    if (event.kind === 'evidence') { if (!data || data.seq !== events.length || events.length >= 300 || typeof data.kind !== 'string') { state('Evidence projection out of sequence. Inspect the retained guest trace.'); return; } events.push(data); rawFrames.push(typeof rawFrame === 'string' ? rawFrame : null); $('count').textContent=String(events.length); $('events').append(renderEvidenceEvent(data)); state(`Working · ${data.kind} · ${events.length} evidence events`); }
    if (event.kind === 'inference_requested' && data && validRequest(data.request_id)) { state('Waiting for the authorized provider response…'); const mid=active; provider.infer(mid,data).then(reply=>host.mailbox(`/${mid}-${data.request_id}.json`,JSON.stringify(reply))).catch(()=>state('Provider transport failed. The guest will fail closed or time out.')); }
    if (event.kind === 'mission_error') { completed=true; setAssistant('Mission failed without a verified result. Open Activity or Terminal for the failure path.'); provider.end(); active=null; }
    if (event.kind === 'mission_finished') {
      if (!data?.verification?.result_bound || !data.result || data.verification.root !== data.result.trace_root) { state('Result projection is missing its trace binding. Inspect the guest.'); return; }
      result={summary:data,events:[...events],projection_frames:[...rawFrames]}; completed=true; provider.end(); active=null; $('result').hidden=false;
      const build=data.execution==='generated_artifacts', live=data.execution==='live_provider';
      if (build) {
        const bundle=data.result.values.build; $('verdict').textContent=`${data.status.toUpperCase()} · evidence integrity checked · CODE CORRECTNESS: UNKNOWN — generated files were not automatically certified`;
        $('answer').textContent=bundle?.summary || JSON.stringify(data.result.unresolved,null,2); renderArtifacts(bundle); $('citations-box').hidden=true;
        $('path').textContent=`Guest files: ${data.output}/result.json · trace.jsonl · artifacts/manifest.json · artifacts/*`;
        $('preview').hidden=false; renderPreview($('preview'),bundle,{frameId:'mc-preview-frame',status:$('preview-status')});
        currentAssistant = bubble('assistant', bundle?.summary || 'Build completed.'); inlinePreview(bundle,currentAssistant);
        const note=document.createElement('div'); note.className='muted'; note.textContent='The preview runs generated client-side code in an isolated sandbox with network blocked. Interact with it to verify behavior; RESIDUAL still reports code correctness as UNKNOWN.'; currentAssistant.node.append(note);
        $('run-state').textContent=`${data.status.toUpperCase()} · generated files saved under ${data.output}/artifacts/`;
      } else {
        $('artifacts').hidden=true; $('preview').hidden=true;
        $('verdict').textContent=`${data.status.toUpperCase()} · evidence integrity checked · ${live?'SEMANTIC CORRECTNESS: UNKNOWN — human review required':'deterministic source inventory only — not a security audit'}`;
        const text=data.result.values.answer?.text || JSON.stringify(data.result.values.inventory || data.result.unresolved,null,2); $('answer').textContent=text; currentAssistant=bubble('assistant',text);
        $('citations-box').hidden=!live||!data.result.values.answer; $('citations').textContent=(data.result.values.answer?.citations||[]).map(c=>`${data.source_paths[c.artifact_id]||c.artifact_id}:${c.start_line}-${c.end_line}\n${c.quote}`).join('\n\n');
        $('path').textContent=`Guest files: ${data.output}/result.json · trace.jsonl · ${live?'answer.md (only if accepted)':'sources.json'}`;
        $('run-state').textContent=`${data.status.toUpperCase()} · ${data.output}`;
      }
      $('json').textContent=JSON.stringify({metrics:data.result.metrics,receipts:data.result.receipts,verification:data.verification,unresolved:data.result.unresolved,generated_files:data.generated_files||[]},null,2);
      verifyEvidenceChain([...rawFrames], event.mission_id, data.result.trace_root).then(proof => {
        const note=document.createElement('p'); note.className='mc-ev-chain';
        note.textContent = proof.ok
          ? `Browser re-verified the projected trace chain: ${proof.count} events \u00b7 head ${proof.head.slice(0,12)}\u2026 matches the bound result root \u2713 \u00b7 the guest trace.jsonl and verify-trace remain authoritative`
          : `Browser could not re-verify the projected trace chain: ${proof.reason} \u00b7 inspect the retained guest trace.jsonl`;
        $('events').prepend(note);
      });
    }
  }
  function onOutput(text) { carry+=text; const prefix='\x1b]777;RESIDUAL;'; while(true){ const start=carry.indexOf(prefix); if(start<0){carry=carry.slice(-prefix.length);break;} if(start)carry=carry.slice(start); const end=carry.indexOf('\x07',prefix.length); if(end<0)break; try{const bin=atob(carry.slice(prefix.length,end).replace(/-/g,'+').replace(/_/g,'/'));const decoded=new TextDecoder().decode(Uint8Array.from(bin,c=>c.charCodeAt(0)));consume(JSON.parse(decoded),decoded);}catch{state('Malformed guest projection ignored. Verify the trace in Terminal.');} carry=carry.slice(end+1);} if(carry.length>400000){carry='';state('Guest projection exceeded its byte limit.');} }
  function updateMode(){ const mode=$('mode').value,remote=mode==='build'||mode==='live',tokens=$('tokens'),current=Number(tokens.value); $('consent-label').hidden=!remote; $('files-label').textContent=mode==='build'?'Optional reference repository paths · at most 6 files':'Repository paths · one per line · at most 6 files'; if(mode==='build'){tokens.max='8192';if(!Number.isFinite(current)||current<256||current<=1536)tokens.value='8192';}else{tokens.max='1536';if(!Number.isFinite(current)||current<256||current>1536)tokens.value='1536';} if(mode!=='build'&&!$('files').value.trim())$('files').value='README.md\nresidual/cli.py'; }
  $('mode').onchange=updateMode; updateMode();
  $('form').onsubmit=async event=>{ event.preventDefault(); if(active||running||!guestReady())return; const mode=$('mode').value,remote=mode==='build'||mode==='live'; if(remote&&(!$('consent').checked||!provider.ready)){ bubble('system','Connect a provider and authorize this mission before sending it. No prompt was sent.'); return; } const files=$('files').value.split('\n').map(s=>s.trim()).filter(Boolean); if(mode!=='build'&&files.length===0){bubble('system','This mode requires at least one repository source path.');return;} const req={id:'m-'+crypto.randomUUID().replaceAll('-',''),mode,prompt:$('prompt').value,files,required_text:$('required').value.split('\n').filter(Boolean),model:$('model').value,max_calls:Number($('budget').value),max_output_tokens:Number($('tokens').value),cloud_consent:remote&&$('consent').checked}; if(!bounded(req)){bubble('system','Mission input exceeds the byte budget.');return;} bubble('user',req.prompt); reset(req.id); running=true; currentAssistant=bubble('assistant','Submitting a real guest mission…'); try{if(remote)provider.begin(req.id,req.max_calls,req.model); const exit=await host.run(req); if(!completed)setAssistant(`Guest returned ${exit?.status??'unknown'} without a verified completion projection. Open Terminal.`);}catch{setAssistant('Guest submission failed. Check Activity, Terminal, and provider connection. No success claimed.');}finally{provider.end();active=null;running=false;} };
  $('stop').onclick=async()=>{if(!active)return;const mid=active;provider.end();try{await host.mailbox(`/${mid}-cancel.json`,'{}');state('Stop requested. A provider request already sent may still incur charges.');}catch{state('Provider authorization revoked, but the guest stop signal could not be written.');}};
  $('download').onclick=()=>{if(!result)return;const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`${result.summary.result.task_id}-evidence.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  const timer=setInterval(()=>{provider.checkConnection();const health=runtimeHealth(),ready=health==='ready',poisoned=health==='poisoned';$('runtime').textContent=poisoned?'GUEST FAILED · RESTART REQUIRED':ready?'LINUX · READY':'GUEST STARTING';$('restart').hidden=!poisoned||typeof host.restart!=='function';$('restart').disabled=!poisoned||!!active||running;$('run').disabled=!ready||!!active||running;$('stop').disabled=!active;},300);
  return {onOutput,connectProvider,destroy(){clearInterval(timer);provider.close();element.remove();}};
}
