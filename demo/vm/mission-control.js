import {ProviderSession, validId, validRequest, bounded} from './provider-session.js';

// UI projections are not an independent trust anchor. The retained guest trace
// and verify-trace command remain the source of integrity evidence.
export function mountMissionControl(host) {
  const element = document.createElement('section'); element.id = 'mission-control'; element.dataset.view = 'mission';
  element.innerHTML = `<style>
#mission-control{position:fixed;inset:0;z-index:100;background:#000;color:#39ff68;font:14px/1.55 ui-monospace,monospace;display:flex;flex-direction:column;box-sizing:border-box}
#mission-control *{box-sizing:border-box}#mission-control header{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:12px 18px;border-bottom:1px solid #235331;background:#000}
#mission-control h1{font-size:17px;margin:0;letter-spacing:.14em}#mission-control .muted{color:#a2b8a8}#mission-control main{overflow:auto;padding:24px;max-width:1100px;width:100%;margin:auto;flex:1}
#mission-control button,#mission-control select,#mission-control textarea,#mission-control input{font:inherit;background:#07100a;color:#d1ffdb;border:1px solid #2a6940;border-radius:4px;padding:9px}
#mission-control button{cursor:pointer}#mission-control button:disabled{opacity:.45;cursor:not-allowed}#mission-control button:focus-visible,#mission-control input:focus-visible,#mission-control textarea:focus-visible,#mission-control summary:focus-visible{outline:2px solid #39ff68;outline-offset:3px}
#mission-control button.primary{background:#39ff68;color:#000;font-weight:700}#mission-control textarea{width:100%;resize:vertical}#mission-control label{display:block;margin:10px 0 5px}#mission-control .row{display:flex;align-items:center;gap:12px;flex-wrap:wrap}#mission-control .row>label{flex:1;min-width:180px}#mission-control input[type=checkbox]{width:18px;height:18px;vertical-align:middle}
#mission-control details{border:1px solid #1c4328;border-radius:4px;padding:10px;margin:8px 0}#mission-control summary{cursor:pointer;color:#a8ffbf}#mission-control pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:420px;overflow:auto;font:12px/1.6 monospace}#mission-control .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px}#mission-control .cards details{margin:0}#mission-control .notice{border-left:3px solid #39ff68;padding:10px 14px;background:#06130a;white-space:pre-wrap;overflow-wrap:anywhere}#mission-control a{color:#8effa8}#mission-control ul{padding-left:18px}#mission-control [hidden]{display:none!important}#mission-control[data-view=terminal]{bottom:auto;background:transparent}#mission-control[data-view=terminal] main{display:none}#mission-control .spacer{flex:1}
@media(max-width:600px){#mission-control main{padding:12px}#mission-control header{padding:8px;gap:6px}#mission-control h1{font-size:14px}#mission-control button{padding:7px}#mission-control .cards{grid-template-columns:repeat(2,1fr)}}
</style><header><h1>RESIDUAL</h1><span class="muted">MISSION CONTROL</span><span class="spacer"></span><button id="mc-mission" aria-pressed="true">Mission</button><button id="mc-terminal" aria-pressed="false">Terminal</button><button id="mc-connect">Connect provider</button><span id="mc-runtime" class="muted">Guest starting…</span></header>
<main><h2>Give the harness a job.</h2><p class="muted">Your prompt → real Linux execution → checked candidates → inspectable evidence. No scripted model fallback.</p>
<div id="mc-provider-state" class="notice" role="status">Live prompts require a provider connection. Repository audit runs locally without a model.</div><a id="mc-provider-link" hidden target="_blank" rel="noopener noreferrer">Open provider setup tab</a>
<form id="mc-form"><label for="mc-prompt">Mission</label><textarea id="mc-prompt" rows="4" maxlength="4000" placeholder="Explain how this repository rejects invalid worker output. Cite the relevant source lines, and write a review checklist." required></textarea>
<div class="row"><label>Execution<select id="mc-mode"><option value="live">Live prompt / artifact</option><option value="audit">Repository audit · no model</option></select></label><label>Call budget<select id="mc-budget"><option value="1">Quick · at most 1 call</option><option value="2" selected>Bounded · at most 2 calls</option><option value="3">Repair budget · at most 3 calls</option></select></label></div>
<details><summary>Sources and acceptance checks</summary><label for="mc-files">Repository paths · at most 6 files · 32 KB/file · 48 KB total</label><textarea id="mc-files" rows="3">README.md\nresidual/cli.py</textarea><label for="mc-required">Required literal text · one check per line (optional)</label><textarea id="mc-required" rows="2" placeholder="Review checklist"></textarea><div class="row"><label>Model<input id="mc-model" value="gpt-5-nano" maxlength="96"></label><label>Max output tokens<input id="mc-tokens" type="number" min="256" max="1536" value="1024"></label></div><p class="muted">Selected source snapshots, not the entire workspace, can be sent to the provider. Citation checks prove exact excerpt matches, not that the answer is true. Generated text is saved for review; it is not executed, merged, or applied to the repository.</p></details>
<label id="mc-consent-label"><input type="checkbox" id="mc-consent"> I authorize sending this prompt and the selected source snapshots to my provider, up to the chosen call/token budget. Provider charges may apply.</label>
<div class="row"><button id="mc-run" class="primary" disabled>Run mission</button><button id="mc-stop" type="button" disabled>Stop mission</button><span class="muted">One active mission per workspace · 240-second guest limit</span></div></form>
<p id="mc-run-state" class="notice" role="status">Waiting for a mission. The terminal and this interface share the same repository and run files.</p>
<div class="cards"><details><summary>Mission</summary><p>Validated prompt, frozen source snapshots and explicit checks become a real <code>Task</code>.</p><code>residual/workbench/runner.py</code></details><details><summary>Workers</summary><p>Existing Harness dispatch with bounded calls and counterexample feedback. Live mode never substitutes a scripted provider.</p><code>residual/engine.py</code></details><details><summary>Verifiers</summary><p>Mechanical answer shape, literal requirements and exact source quotations. Semantic correctness stays UNKNOWN.</p><code>workbench:answer</code></details><details><summary>Evidence</summary><p>Original hash-linked ledger events and result-bound receipts. Browser display is a projection, not an external anchor.</p><code>residual/storage.py</code></details><details><summary>Integration</summary><p>The Harness accepts contract-passing values and writes review artifacts. This is not Factory patch application or an M4 sandbox certification.</p><code>runs/missions/</code></details><details><summary>Policy / runtime</summary><p>One guest workspace, explicit cloud consent, source/call/token/time limits. Hosted identity, durable quotas and abuse-resistant server admission are not implemented here.</p></details></div>
<section id="mc-result" hidden><h3>Result and verification scope</h3><p id="mc-verdict"></p><pre id="mc-answer"></pre><details id="mc-citations-box" hidden><summary>Checked source quotations</summary><pre id="mc-citations"></pre></details><p id="mc-path"></p><button id="mc-download" type="button">Download run evidence JSON</button><details><summary>Metrics, receipts and result binding</summary><pre id="mc-json"></pre></details></section>
<details open><summary>Live evidence events <span id="mc-count">0</span></summary><div id="mc-events"></div></details>
<details><summary>CLI / existing repository workflows</summary><p>The CLI operates on the same files. A streamed audit launched from the terminal appears here too:</p><pre>mission audit --stream --files README.md residual/cli.py
mission inspect runs/missions/&lt;mission-id&gt;
python3 -m residual run task.json --config provider.toml --output runs/custom
python3 -m residual verify-trace runs/custom/trace.jsonl --result runs/custom/result.json</pre><p class="muted">The old <code>demo</code> command remains a clearly labelled scripted tutorial. Mission Control currently supports source-grounded answers, review artifacts, and deterministic source inspection—not arbitrary autonomous code execution.</p></details></main>`;
  document.body.append(element);
  const $ = id => element.querySelector('#mc-' + id);
  let active = null, result = null, events = [], carry = '', completed = false, terminal = false, running = false;
  const provider = new ProviderSession((state, message) => { $('provider-state').textContent = message; $('connect').textContent = state === 'connected' ? 'Provider connected' : 'Connect provider'; });
  function view(isTerminal) { terminal = isTerminal; element.dataset.view = isTerminal ? 'terminal' : 'mission'; $('terminal').setAttribute('aria-pressed', String(isTerminal)); $('mission').setAttribute('aria-pressed', String(!isTerminal)); if (isTerminal) host.focus(); }
  $('terminal').onclick = () => view(true); $('mission').onclick = () => view(false);
  function connectProvider() {
    try { $('provider-link').href = provider.open(); $('provider-link').hidden = false; view(false); }
    catch { $('provider-state').textContent = 'This browser cannot open the provider channel. Use a supported desktop browser or a locally configured CLI provider.'; }
  }
  $('connect').onclick = connectProvider;
  function reset(mid) { active = mid; result = null; events = []; completed = false; $('events').replaceChildren(); $('count').textContent = '0'; $('result').hidden = true; }
  function state(text) { $('run-state').textContent = text; }
  function consume(event) {
    if (!event || !validId(event.mission_id)) return;
    if (event.kind === 'mission_started' && !active) reset(event.mission_id); // CLI-origin stream
    if (event.mission_id !== active) return;
    const data = event.data;
    if (event.kind === 'mission_started') state(`RUNNING · ${event.mission_id}\nFrozen sources and limits are in ${data.output}/task.json`);
    if (event.kind === 'evidence') {
      if (!data || data.seq !== events.length || events.length >= 300 || typeof data.kind !== 'string') { state('Evidence projection out of sequence. Inspect the retained guest trace.'); return; }
      events.push(data); $('count').textContent = String(events.length);
      const d = document.createElement('details'), s = document.createElement('summary'), p = document.createElement('pre');
      s.textContent = `${data.seq} · ${data.kind}`; p.textContent = JSON.stringify(data, null, 2); d.append(s, p); $('events').append(d);
      state(`RUNNING · ${data.kind} · ${events.length} retained-ledger events projected`);
    }
    if (event.kind === 'inference_requested' && data && validRequest(data.request_id)) {
      const mid = active;
      provider.infer(mid, data).then(reply => host.mailbox(`/${mid}-${data.request_id}.json`, JSON.stringify(reply)))
        .catch(() => state('Provider transport failed. The guest will fail closed or time out; no success claimed.'));
    }
    if (event.kind === 'mission_error') { completed = true; state('MISSION ERROR · no verified result. Inspect the terminal for the failure.'); provider.end(); active = null; }
    if (event.kind === 'mission_finished') {
      if (!data?.verification?.result_bound || !data.result || data.verification.root !== data.result.trace_root) { state('Result projection is missing its trace binding. Inspect in the guest.'); return; }
      result = {summary: data, events: [...events]}; completed = true; provider.end(); active = null;
      $('result').hidden = false;
      const live = data.execution === 'live_provider';
      $('verdict').textContent = `${data.status.toUpperCase()} · evidence integrity checked · ${live ? 'SEMANTIC CORRECTNESS: UNKNOWN — human review required' : 'deterministic source inventory only — not a security audit'}`;
      $('answer').textContent = data.result.values.answer?.text || JSON.stringify(data.result.values.inventory || data.result.unresolved, null, 2);
      $('citations-box').hidden = !live || !data.result.values.answer;
      $('citations').textContent = (data.result.values.answer?.citations || []).map(c => `${data.source_paths[c.artifact_id] || c.artifact_id}:${c.start_line}-${c.end_line}\n${c.quote}`).join('\n\n');
      $('path').textContent = `Same guest files: ${data.output}/result.json · trace.jsonl · ${live ? 'answer.md (only if accepted)' : 'sources.json'}`;
      $('json').textContent = JSON.stringify({metrics: data.result.metrics, receipts: data.result.receipts, verification: data.verification, unresolved: data.result.unresolved}, null, 2);
      state(`${data.status.toUpperCase()} · ${data.output}\n${live ? 'A contract pass does not establish answer truth or code correctness.' : 'No model was called. Findings were computed from the selected current source files.'}`);
    }
  }
  function onOutput(text) {
    carry += text;
    const prefix = '\x1b]777;RESIDUAL;';
    while (true) {
      const start = carry.indexOf(prefix);
      if (start < 0) { carry = carry.slice(-prefix.length); break; }
      if (start) carry = carry.slice(start);
      const end = carry.indexOf('\x07', prefix.length);
      if (end < 0) break;
      try { const bin = atob(carry.slice(prefix.length, end).replace(/-/g, '+').replace(/_/g, '/')); consume(JSON.parse(new TextDecoder().decode(Uint8Array.from(bin, c => c.charCodeAt(0))))); }
      catch { state('Malformed guest projection ignored. Verify the trace in the terminal.'); }
      carry = carry.slice(end + 1);
    }
    if (carry.length > 400000) { carry = ''; state('Guest projection exceeded its byte limit.'); }
  }
  $('mode').onchange = () => { $('consent-label').hidden = $('mode').value === 'audit'; };
  $('form').onsubmit = async event => {
    event.preventDefault(); if (active || running || !host.ready()) return;
    const mode = $('mode').value;
    if (mode === 'live' && (!$('consent').checked || !provider.ready)) { state('Connect a provider and explicitly authorize this mission before running. No prompt was sent.'); return; }
    const req = {id: 'm-' + crypto.randomUUID().replaceAll('-', ''), mode,
      prompt: $('prompt').value, files: $('files').value.split('\n').map(s => s.trim()).filter(Boolean),
      required_text: $('required').value.split('\n').filter(Boolean), model: $('model').value,
      max_calls: Number($('budget').value), max_output_tokens: Number($('tokens').value), cloud_consent: mode === 'live' && $('consent').checked};
    if (!bounded(req)) { state('Mission input exceeds the byte budget.'); return; }
    reset(req.id); running = true; state('Submitting a real guest mission…');
    try {
      if (mode === 'live') provider.begin(req.id, req.max_calls, req.model);
      const exit = await host.run(req);
      if (!completed) state(`Guest returned ${exit?.status ?? 'unknown'} without a verified completion projection. Inspect the terminal.`);
    } catch { state('Guest submission failed. Check the terminal and provider connection. No success claimed.'); }
    finally { provider.end(); active = null; running = false; }
  };
  $('stop').onclick = async () => {
    if (!active) return;
    const mid = active; provider.end();
    try {
      await host.mailbox(`/${mid}-cancel.json`, '{}');
      state('Stop requested. Pending inference may still incur provider charges. Waiting for the guest to finish.');
    } catch {
      state('Provider authorization revoked, but the guest stop signal could not be written. The guest may run until its deadline; inspect the terminal.');
    }
  };
  $('download').onclick = () => {
    if (!result) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], {type: 'application/json'}));
    const a = document.createElement('a'); a.href = url; a.download = `${result.summary.result.task_id}-evidence.json`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const timer = setInterval(() => { provider.checkConnection(); const ready = host.ready(); $('runtime').textContent = ready ? 'LINUX · READY' : 'GUEST STARTING'; $('run').disabled = !ready || !!active || running; $('stop').disabled = !active; }, 300);
  return {onOutput, connectProvider, destroy() { clearInterval(timer); provider.close(); element.remove(); }};
}
