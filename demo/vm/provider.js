import {PROTOCOL, RESPONSE_SCHEMA, validId, validInference, validModel, bounded, errorCode, protocolReply} from './provider-session.js';
const status = document.getElementById('status'), load = document.getElementById('load'), sign = document.getElementById('signin');
const token = location.hash.slice(1);
history.replaceState(null, '', location.pathname);
let channel, sdk, grant = null, busy = false;
const tell = text => { status.textContent = text; };
const send = msg => channel?.postMessage({protocol: PROTOCOL, ...msg});
function state() { send({kind: 'state', connected: !!sdk?.auth?.isSignedIn?.()}); }
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
    settled = true; clearTimeout(timer); sdk = window.puter;
    sign.disabled = false; tell('SDK loaded. Click Sign in to open authorization. No inference has run.'); state();
  };
  document.head.appendChild(script);
});
sign.addEventListener('click', () => {
  if (!sdk || busy) return;
  sign.disabled = true; tell('Waiting for authorization. Allow the popup or close it to cancel.');
  // MUST occur synchronously in this click handler, before any await/timer.
  let auth;
  try { auth = sdk.auth.signIn({attempt_temp_user_creation: false}); }
  catch (error) { sign.disabled = false; tell(`Sign-in failed: ${errorCode(error)}. Retry using this button.`); return; }
  let timer;
  Promise.race([auth, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('timeout')), 60000); })])
    .then(() => { if (!sdk.auth.isSignedIn()) throw new Error('not_signed_in'); tell('Connected. Return to Mission Control; keep this tab open. Model access is checked on each run.'); })
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
  const g = grant;
  if (!sdk?.auth?.isSignedIn() || !g || g.id !== m.mission_id || g.model !== m.model) return reply({ok: false, error: 'provider_disconnected'});
  if (busy || Date.now() > g.expires || g.used >= g.max || g.seen.has(m.request_id)) return reply({ok: false, error: 'provider_budget_exhausted'});
  g.used++; g.seen.add(m.request_id); busy = true;
  tell(`Running ${g.used}/${g.max} authorized model calls for ${g.id}. Charges may apply even if the browser times out.`);
  let timer;
  try {
    const tools = [{type: 'function', function: {
      name: 'residual_submit',
      description: 'Submit the RESIDUAL worker response. Always call this function exactly once instead of returning prose.',
      parameters: RESPONSE_SCHEMA
    }}];
    const result = await Promise.race([
      sdk.ai.chat(m.messages, {model: m.model, max_tokens: m.max_output_tokens, stream: false, normalize: true, tools}),
      new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('provider_timeout')), 80000); })
    ]);
    if (grant !== g) return reply({ok: false, error: 'mission_cancelled'});
    // Tool arguments or a JSON text fallback are independently validated here
    // before anything is returned to the guest. We do not rely on a vendor's
    // strict-schema dialect for RESIDUAL's dynamic obligation map.
    const text = protocolReply(result), u = result?.usage || {};
    if (new TextEncoder().encode(text).length > 48000) return reply({ok: false, error: 'provider_response_too_large'});
    const integer = n => Number.isInteger(n) && n >= 0 ? n : null;
    reply({ok: true, text, usage: {input_tokens: integer(u.input_tokens ?? u.prompt_tokens), output_tokens: integer(u.output_tokens ?? u.completion_tokens)}});
    tell('Structured model response returned to the guest. RESIDUAL—not this provider tab—checks the candidate.');
  } catch (error) {
    const timeout = error?.message === 'provider_timeout';
    const protocol = error?.message === 'provider_protocol_invalid';
    reply({ok: false, error: timeout ? 'provider_timeout' : 'provider_error'});
    tell(protocol ? 'The model did not return the required RESIDUAL response envelope. No result was accepted; retry or choose a stronger model.' : 'Model request failed or timed out. Check model availability/allowance in Puter. A timed-out request may still be billed.');
  } finally { clearTimeout(timer); busy = false; state(); }
}
window.addEventListener('pagehide', () => { send({kind: 'state', connected: false}); channel?.close(); });
