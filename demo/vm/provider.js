import {PROTOCOL, RESPONSE_SCHEMA, validId, validInference, validModel, bounded, errorCode, protocolReply, protocolFailureReason, providerFailureMessage} from './provider-session.js';
const status = document.getElementById('status'), load = document.getElementById('load'), sign = document.getElementById('signin');
const token = location.hash.slice(1);
history.replaceState(null, '', location.pathname);
let channel, sdk, grant = null, busy = false, modelCatalog = null;
const tell = text => { status.textContent = text; };
const send = msg => channel?.postMessage({protocol: PROTOCOL, ...msg});
function state() { send({kind: 'state', connected: !!sdk?.auth?.isSignedIn?.()}); }
function safeFailure(error) {
  const raw = String(error?.error || error?.code || error?.message || '').toLowerCase();
  if (raw === 'provider_protocol_invalid' || raw.includes('protocol_invalid')) return 'provider_protocol_invalid';
  if (raw.includes('timeout')) return 'provider_timeout';
  if (raw.includes('model') && (raw.includes('not') || raw.includes('unknown') || raw.includes('404'))) return 'provider_model_unavailable';
  if (raw.includes('auth') || raw.includes('permission') || raw.includes('forbidden') || raw.includes('401') || raw.includes('403') || raw.includes('billing') || raw.includes('credit') || raw.includes('quota')) return 'provider_authorization_failed';
  return 'provider_request_failed';
}
async function resolveModel(requested) {
  if (!sdk?.ai?.listModels) return requested;
  try {
    if (!modelCatalog) modelCatalog = await sdk.ai.listModels();
    if (!Array.isArray(modelCatalog)) return requested;
    const exact = modelCatalog.find(item => item?.id === requested || (Array.isArray(item?.aliases) && item.aliases.includes(requested)));
    if (exact?.id) return exact.id;
    // Catalogs can lag routing. Never silently substitute another model: send
    // the exact requested ID and let Puter's inference call classify availability.
    return requested;
  } catch {
    return requested;
  }
}
if (!/^[a-f0-9]{64}$/.test(token)) {
  load.disabled = true; tell('Open provider setup from Mission Control. This tab has no connection channel.');
} else {
  channel = new BroadcastChannel(`${PROTOCOL}:${token}`);
  channel.onmessage = event => receive(event.data);
  setInterval(state, 3000); state();
}
load.addEventListener('click', () => {
  load.disabled = true; tell('Loading provider SDK…');
  const script = document.createElement('script'); script.src = 'https://js.puter.com/v2/'; script.async = true;
  let settled = false;
  const fail = () => { if (settled) return; settled = true; clearTimeout(timer); script.remove(); load.disabled = false; tell('SDK could not load. Check content blockers/network and retry. Nothing was sent for inference.'); };
  const timer = setTimeout(fail, 10000);
  script.onerror = fail;
  script.onload = () => {
    if (settled) return;
    if (!window.puter?.auth || !window.puter?.ai) return fail();
    settled = true; clearTimeout(timer); sdk = window.puter; modelCatalog = null;
    sign.disabled = false; tell('SDK loaded. Click Sign in to open authorization. No inference has run.'); state();
  };
  document.head.appendChild(script);
});
sign.addEventListener('click', () => {
  if (!sdk || busy) return;
  sign.disabled = true; tell('Waiting for authorization. Allow the popup or close it to cancel.');
  let auth;
  try { auth = sdk.auth.signIn({attempt_temp_user_creation: false}); }
  catch (error) { sign.disabled = false; tell(`Sign-in failed: ${errorCode(error)}. Retry using this button.`); return; }
  let timer;
  Promise.race([auth, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('timeout')), 60000); })])
    .then(() => { if (!sdk.auth.isSignedIn()) throw new Error('not_signed_in'); tell('Connected. Return to Mission Control; keep this tab open. Model availability and billing are checked on each run.'); })
    .catch(error => tell(`Sign-in did not complete: ${errorCode(error)}. Check popup permission, then retry. No inference was requested.`))
    .finally(() => { clearTimeout(timer); sign.disabled = false; state(); });
});
async function receive(m) {
  if (!m || m.protocol !== PROTOCOL || !bounded(m)) return;
  if (m.kind === 'revoke') { grant = null; return; }
  if (m.kind === 'grant' && validId(m.mission_id) && validModel(m.model) && Number.isInteger(m.max_calls) && m.max_calls >= 1 && m.max_calls <= 3 && !busy && sdk?.auth?.isSignedIn()) {
    grant = {id: m.mission_id, model: m.model, max: m.max_calls, used: 0, seen: new Set(), expires: Date.now() + 240000}; return;
  }
  if (m.kind !== 'request' || !validInference(m) || !validId(m.mission_id)) return;
  const reply = data => send({kind: 'response', mission_id: m.mission_id, request_id: m.request_id, ...data});
  const progress = (stage, model = null) => send({kind: 'progress', mission_id: m.mission_id, request_id: m.request_id, stage, ...(validModel(model) ? {model} : {})});
  const g = grant;
  if (!sdk?.auth?.isSignedIn() || !g || g.id !== m.mission_id || g.model !== m.model) return reply({ok: false, error: 'provider_disconnected'});
  if (busy || Date.now() > g.expires || g.used >= g.max || g.seen.has(m.request_id)) return reply({ok: false, error: 'provider_budget_exhausted'});
  g.used++; g.seen.add(m.request_id); busy = true;
  let timer;
  try {
    const selectedModel = await resolveModel(m.model);
    if (!selectedModel) {
      reply({ok:false,error:'provider_model_unavailable'}); tell(providerFailureMessage('provider_model_unavailable')); return;
    }
    progress('model_selected', selectedModel);
    tell(`Running ${g.used}/${g.max} authorized model calls with ${selectedModel}. Charges may apply even if the browser times out.`);
    const tools = [{type: 'function', function: {
      name: 'residual_submit',
      description: 'Submit a RESIDUAL worker envelope. Arguments must be one object with exactly updates and requests. Put candidate values under updates keyed by obligation id; build candidates use updates.build = {summary, files}. Use requests: [] when no evidence pull is needed.',
      parameters: RESPONSE_SCHEMA
    }}];
    // Puter documents messages + model/max_tokens/stream/normalize/tools. Keep the
    // original harness messages unchanged: the tool description/schema owns the
    // browser transport contract, while RESIDUAL validates the returned envelope.
    const options = {model: selectedModel, max_tokens: m.max_output_tokens, stream: false, normalize: true, tools};
    progress('request_dispatched', selectedModel);
    const result = await Promise.race([
      sdk.ai.chat(m.messages, options),
      new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('provider_timeout')), 80000); })
    ]);
    progress('response_received', selectedModel);
    if (grant !== g) return reply({ok: false, error: 'mission_cancelled'});
    let text;
    try { text = protocolReply(result); }
    catch (error) {
      const detail = protocolFailureReason(error);
      progress('protocol_rejected', selectedModel);
      reply({ok:false,error:'provider_protocol_invalid',...(detail ? {detail} : {})});
      tell(providerFailureMessage('provider_protocol_invalid', detail));
      return;
    }
    const u = result?.usage || {};
    progress('envelope_decoded', selectedModel);
    if (new TextEncoder().encode(text).length > 48000) return reply({ok: false, error: 'provider_response_too_large'});
    const integer = n => Number.isInteger(n) && n >= 0 ? n : null;
    reply({ok: true, text, usage: {input_tokens: integer(u.input_tokens ?? u.prompt_tokens), output_tokens: integer(u.output_tokens ?? u.completion_tokens)}});
    tell('Structured model response returned to the guest. RESIDUAL—not this provider tab—checks the candidate.');
  } catch (error) {
    const code = safeFailure(error);
    reply({ok: false, error: code});
    tell(providerFailureMessage(code));
  } finally { clearTimeout(timer); busy = false; state(); }
}
window.addEventListener('pagehide', () => { send({kind: 'state', connected: false}); channel?.close(); });