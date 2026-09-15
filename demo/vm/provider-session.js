/* Same-origin relay; no credentials cross the channel or enter the guest. */
export const PROTOCOL = 'residual.provider.v1';
export const MAX_WIRE = 65536;
export const validId = value => typeof value === 'string' && /^m-[a-f0-9]{32}$/.test(value);
export const validRequest = value => typeof value === 'string' && /^[a-f0-9]{32}$/.test(value);
export const validModel = value => typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,95}$/.test(value);
export const bounded = value => { try { return new TextEncoder().encode(JSON.stringify(value)).length <= MAX_WIRE; } catch { return false; } };
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
export function textReply(result) {
  if (typeof result === 'string') return result;
  const content = result?.message?.content ?? result?.text ?? result?.content;
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) return content.map(p => typeof p === 'string' ? p : (p?.text || '')).join('');
  throw new Error('provider_response_invalid');
}
export class ProviderSession {
  constructor(onState = () => {}) {
    this.onState = onState; this.channel = null; this.pending = new Map();
    this.connected = false; this.lastSeen = 0; this.grant = null; this.generation = 0;
  }
  get ready() { return this.connected && Date.now() - this.lastSeen < 15000; }
  checkConnection() {
    if (this.connected && !this.ready) {
      this.connected = false;
      this.onState('disconnected', 'Provider tab stopped responding. Reopen setup or return to that tab. No new requests are authorized.');
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
    // Opens on the original click. It is deliberately independent of opener/COOP.
    window.open(url.href, '_blank', 'noopener,noreferrer');
    this.onState('connecting', 'Complete provider setup in the new tab. Allow popups for this site if it did not open.');
    return url.href;
  }
  receive(message) {
    if (!message || message.protocol !== PROTOCOL || !bounded(message)) return;
    if (message.kind === 'state') {
      this.connected = message.connected === true; this.lastSeen = Date.now();
      this.onState(this.ready ? 'connected' : 'disconnected', this.ready ? 'Provider signed in. Model access and billing are checked on each run.' : 'Provider not signed in. Open setup to continue.');
    }
    if (message.kind === 'response' && validRequest(message.request_id)) {
      const entry = this.pending.get(message.request_id);
      if (entry && message.mission_id === entry.missionId) {
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
        resolve({ok: false, request_id: req.request_id, error: 'provider_timeout'});
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
  close() { this.end(); this.channel?.close(); this.channel = null; this.connected = false; this.generation++; }
}
