/* Same-origin relay; no credentials cross the channel or enter the guest. */
export const PROTOCOL = 'residual.provider.v1';
export const MAX_WIRE = 65536;
export const validId = value => typeof value === 'string' && /^m-[a-f0-9]{32}$/.test(value);
export const validRequest = value => typeof value === 'string' && /^[a-f0-9]{32}$/.test(value);
export const validModel = value => typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,95}$/.test(value);
export const bounded = value => { try { return new TextEncoder().encode(JSON.stringify(value)).length <= MAX_WIRE; } catch { return false; } };
export const RESPONSE_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['updates', 'requests'],
  properties: {
    updates: {type: 'object'},
    requests: {type: 'array', items: {
      type: 'object', additionalProperties: false,
      required: ['obligation_id', 'artifact_id', 'start_line', 'end_line'],
      properties: {
        obligation_id: {type: 'string'}, artifact_id: {type: 'string'},
        start_line: {type: 'integer', minimum: 1}, end_line: {type: 'integer', minimum: 1}
      }
    }}
  }
};
const PROTOCOL_REASONS = new Set([
  'tool_call_count', 'tool_name', 'tool_arguments_empty', 'tool_arguments_not_json',
  'content_missing', 'content_empty', 'content_not_json', 'envelope_shape'
]);
const PROVIDER_PROGRESS_STAGES = new Set([
  'model_selected', 'request_dispatched', 'response_received', 'envelope_decoded'
]);
export class ProviderProtocolError extends Error {
  constructor(reason) {
    super('provider_protocol_invalid');
    this.name = 'ProviderProtocolError';
    this.code = 'provider_protocol_invalid';
    this.reason = PROTOCOL_REASONS.has(reason) ? reason : 'envelope_shape';
  }
}
export const protocolFailureReason = error => PROTOCOL_REASONS.has(error?.reason) ? error.reason : null;
export function validInference(req) {
  return req && validRequest(req.request_id) && validModel(req.model) &&
    Number.isInteger(req.max_output_tokens) && req.max_output_tokens >= 1 && req.max_output_tokens <= 1536 &&
    Array.isArray(req.messages) && req.messages.length >= 1 && req.messages.length <= 6 &&
    req.messages.every(m => m && ['system', 'user', 'assistant'].includes(m.role) && typeof m.content === 'string') && bounded(req);
}
export function errorCode(error) {
  const code = error?.error || error?.code;
  return ['popup_blocked', 'auth_window_closed', 'not_available_in_app'].includes(code) ? code : 'provider_error';
}
function protocolReasonText(detail) {
  const messages = {
    tool_call_count: 'The model returned an unexpected number of tool calls.',
    tool_name: 'The model called a tool other than residual_submit.',
    tool_arguments_empty: 'The residual_submit tool call had no arguments.',
    tool_arguments_not_json: 'The residual_submit arguments were not valid JSON.',
    content_missing: 'The normalized provider response contained neither a usable tool call nor text.',
    content_empty: 'The provider returned empty text instead of a worker envelope.',
    content_not_json: 'The provider returned text that was not a JSON worker envelope.',
    envelope_shape: 'The returned JSON did not have exactly the required updates/requests worker shape.'
  };
  return messages[detail] || '';
}
export function providerFailureMessage(code, detail = null) {
  const messages = {
    provider_model_unavailable: 'Provider connected, but the selected model is unavailable. Choose another model and retry.',
    provider_authorization_failed: 'Provider connected, but this model request was not authorized/allowed. Check account allowance or billing.',
    provider_protocol_invalid: 'Provider returned a response, but it violated the RESIDUAL worker protocol. No candidate was accepted.',
    provider_timeout: 'Provider request timed out. No candidate was accepted; a timed-out remote request may still be billed.',
    provider_request_failed: 'Provider request failed before a usable candidate was returned. No candidate was accepted.',
    provider_response_too_large: 'Provider response exceeded the browser bridge limit. No candidate was accepted.',
    provider_budget_exhausted: 'Provider call budget was exhausted. RESIDUAL refused another dispatch.',
    provider_disconnected: 'Provider connection was lost before the request completed.',
    mission_cancelled: 'Provider authorization was revoked because the mission was cancelled.'
  };
  const base = messages[code] || 'Provider failed with a bounded safe error code. No candidate was accepted.';
  const why = code === 'provider_protocol_invalid' ? protocolReasonText(detail) : '';
  return why ? `${base} ${why}` : base;
}
export function providerProgressMessage(stage, model = null) {
  if (!PROVIDER_PROGRESS_STAGES.has(stage)) return null;
  const suffix = validModel(model) ? ` · ${model}` : '';
  const messages = {
    model_selected: `Provider stage · model selected${suffix}`,
    request_dispatched: `Provider stage · request dispatched${suffix}`,
    response_received: `Provider stage · response received${suffix}`,
    envelope_decoded: `Provider stage · envelope decoded${suffix}`
  };
  return messages[stage];
}
export function textReply(result) {
  if (typeof result === 'string') return result;
  const content = result?.message?.content ?? result?.text ?? result?.content;
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) return content.map(p => typeof p === 'string' ? p : (p?.text || '')).join('');
  throw new ProviderProtocolError('content_missing');
}
export function validProtocolEnvelope(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const keys = Object.keys(value).sort();
  if (keys.length !== 2 || keys[0] !== 'requests' || keys[1] !== 'updates') return false;
  if (!value.updates || typeof value.updates !== 'object' || Array.isArray(value.updates) || !Array.isArray(value.requests)) return false;
  return value.requests.every(r => r && typeof r === 'object' && !Array.isArray(r) &&
    Object.keys(r).sort().join(',') === 'artifact_id,end_line,obligation_id,start_line' &&
    typeof r.obligation_id === 'string' && typeof r.artifact_id === 'string' &&
    Number.isInteger(r.start_line) && r.start_line >= 1 && Number.isInteger(r.end_line) && r.end_line >= 1);
}
function unwrapJsonFence(text) {
  const trimmed = text.trim();
  const fenced = trimmed.match(/^```(?:json)?\s*\r?\n([\s\S]*?)\r?\n```$/i);
  return fenced ? fenced[1].trim() : trimmed;
}
function parseEnvelope(text, source = 'content') {
  if (typeof text !== 'string' || !text.trim()) throw new ProviderProtocolError(`${source}_empty`);
  let value;
  try { value = JSON.parse(unwrapJsonFence(text)); }
  catch { throw new ProviderProtocolError(`${source}_not_json`); }
  if (!validProtocolEnvelope(value)) throw new ProviderProtocolError('envelope_shape');
  return JSON.stringify(value);
}
export function protocolReply(result) {
  const calls = result?.message?.tool_calls;
  if (Array.isArray(calls) && calls.length > 0) {
    if (calls.length !== 1) throw new ProviderProtocolError('tool_call_count');
    if (calls[0]?.function?.name !== 'residual_submit') throw new ProviderProtocolError('tool_name');
    const args = calls[0]?.function?.arguments;
    if (args === undefined || args === null || args === '') throw new ProviderProtocolError('tool_arguments_empty');
    return parseEnvelope(typeof args === 'string' ? args : JSON.stringify(args), 'tool_arguments');
  }
  return parseEnvelope(textReply(result), 'content');
}
function providerOverlay(url) {
  if (typeof document === 'undefined') return null;
  document.getElementById('residual-provider-overlay')?.remove();
  const overlay = document.createElement('div');
  overlay.id = 'residual-provider-overlay';
  overlay.style.cssText = 'position:fixed;inset:0;z-index:1000;background:#000;display:flex;flex-direction:column;color:#39ff68;font:14px monospace';
  const bar = document.createElement('div');
  bar.style.cssText = 'display:flex;gap:8px;align-items:center;padding:10px;border-bottom:1px solid #245833';
  const title = document.createElement('strong'); title.textContent = 'CONNECT PROVIDER';
  const spacer = document.createElement('span'); spacer.style.flex = '1';
  const external = document.createElement('button'); external.type = 'button'; external.textContent = 'Open separately';
  const close = document.createElement('button'); close.type = 'button'; close.textContent = 'Back to Mission Control';
  for (const button of [external, close]) button.style.cssText = 'font:inherit;color:#d1ffdb;background:#07100a;border:1px solid #2a6940;border-radius:8px;padding:8px';
  external.onclick = () => window.open(url.href, '_blank', 'noopener,noreferrer');
  close.onclick = () => overlay.remove();
  bar.append(title, spacer, external, close);
  const frame = document.createElement('iframe'); frame.src = url.href; frame.title = 'Provider setup'; frame.style.cssText = 'border:0;flex:1;width:100%;background:#000';
  overlay.append(bar, frame); document.body.append(overlay); return overlay;
}
export class ProviderSession {
  constructor(onState = () => {}) {
    this.onState = onState; this.channel = null; this.pending = new Map();
    this.connected = false; this.lastSeen = 0; this.grant = null; this.generation = 0; this.overlay = null;
  }
  get ready() { return this.connected && Date.now() - this.lastSeen < 15000; }
  checkConnection() {
    if (this.connected && !this.ready) {
      this.connected = false;
      this.onState('disconnected', 'Provider stopped responding. Reopen provider setup. No new requests are authorized.');
    }
  }
  open() {
    this.close();
    const bytes = crypto.getRandomValues(new Uint8Array(32));
    const token = [...bytes].map(b => b.toString(16).padStart(2, '0')).join('');
    this.channel = new BroadcastChannel(`${PROTOCOL}:${token}`);
    this.channel.onmessage = event => this.receive(event.data);
    const url = new URL('../provider/', location.href);
    url.hash = token;
    this.overlay = providerOverlay(url);
    if (!this.overlay) window.open(url.href, '_blank', 'noopener,noreferrer');
    this.onState('connecting', this.overlay ? 'Provider setup is open inside Mission Control. Your prompt remains here and unsent.' : 'Complete provider setup, then return to Mission Control.');
    return url.href;
  }
  receive(message) {
    if (!message || message.protocol !== PROTOCOL || !bounded(message)) return;
    if (message.kind === 'state') {
      this.connected = message.connected === true; this.lastSeen = Date.now();
      if (this.ready && this.overlay) { this.overlay.remove(); this.overlay = null; }
      this.onState(this.ready ? 'connected' : 'disconnected', this.ready ? 'Provider signed in. Returned to Mission Control; model access and billing are checked on each run.' : 'Provider not signed in. Open setup to continue.');
      return;
    }
    if (message.kind === 'progress' && validRequest(message.request_id) && validId(message.mission_id)) {
      const entry = this.pending.get(message.request_id);
      const text = providerProgressMessage(message.stage, message.model);
      if (entry && entry.missionId === message.mission_id && text) {
        this.onState(this.ready ? 'connected' : 'disconnected', text, {
          kind: 'provider_progress', stage: message.stage, mission_id: message.mission_id,
          request_id: message.request_id, model: validModel(message.model) ? message.model : null
        });
      }
      return;
    }
    if (message.kind === 'response' && validRequest(message.request_id)) {
      const entry = this.pending.get(message.request_id);
      if (entry && message.mission_id === entry.missionId) {
        if (message.ok === false && typeof message.error === 'string') this.onState(this.ready ? 'connected' : 'disconnected', providerFailureMessage(message.error, message.detail));
        clearTimeout(entry.timer); this.pending.delete(message.request_id);
        entry.resolve(message);
      }
    }
  }
  begin(missionId, calls, model) {
    if (!this.ready || !validId(missionId) || !validModel(model) || !Number.isInteger(calls) || calls < 1 || calls > 3) throw new Error('Provider is not connected or budget is invalid.');
    this.grant = {missionId, calls, model, used: 0, seen: new Set()};
    this.channel.postMessage({protocol: PROTOCOL, kind: 'grant', mission_id: missionId, max_calls: calls, model});
  }
  async infer(missionId, req) {
    const g = this.grant;
    if (!this.ready || !g || g.missionId !== missionId) return {ok: false, error: 'provider_disconnected', request_id: req.request_id};
    if (!validInference(req) || req.model !== g.model || g.seen.has(req.request_id) || g.used >= g.calls) return {ok: false, error: 'provider_budget_exhausted', request_id: req.request_id};
    g.used++; g.seen.add(req.request_id);
    return new Promise(resolve => {
      const timer = setTimeout(() => {
        this.pending.delete(req.request_id);
        const response={ok: false, request_id: req.request_id, error: 'provider_timeout'};
        this.onState(this.ready ? 'connected' : 'disconnected', providerFailureMessage(response.error));
        resolve(response);
      }, 85000);
      this.pending.set(req.request_id, {resolve, timer, missionId});
      this.channel.postMessage({protocol: PROTOCOL, kind: 'request', mission_id: missionId, ...req});
    });
  }
  end() {
    this.grant = null;
    for (const [id, entry] of this.pending) {
      clearTimeout(entry.timer); entry.resolve({ok: false, request_id: id, error: 'mission_cancelled'});
    }
    this.pending.clear();
    this.channel?.postMessage({protocol: PROTOCOL, kind: 'revoke'});
  }
  close() { this.end(); this.channel?.close(); this.channel = null; this.connected = false; this.overlay?.remove(); this.overlay = null; this.generation++; }
}
