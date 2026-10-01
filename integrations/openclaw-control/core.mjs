import { randomUUID } from 'node:crypto';
import { Journal } from './journal.mjs';
import { PROTOCOL, canonical, sha256, requireThat, exactKeys, identifier, boundedText, publicKey, verifyCommand, ControlError } from './protocol.mjs';
export const VERSION = '0.2.1';
const TERMINAL = new Set(['COMPLETED','FAILED','INDETERMINATE','REVOKED']);
const MUTATIONS = new Set(['lease.renew','dispatch.submit','provider.probe','dispatch.revoke']);
const ordered = (a,b) => a < b ? -1 : a > b ? 1 : 0;
function endpoint(value) {
  if (typeof value !== 'string') return null;
  try { const u=new URL(value);return {origin:u.origin,path:u.pathname,has_credentials:Boolean(u.username || u.password),has_query:Boolean(u.search)}; }
  catch { return {invalid:true}; }
}
function strings(value) { return Array.isArray(value) ? value.filter(v => typeof v === 'string').sort() : []; }
export function configProjection(cfg) {
  // This deliberately does not serialize whole configuration or hash secret values.
  return {
    gateway:{bind:typeof cfg.gateway?.bind === 'string' ? cfg.gateway.bind : null, port:Number.isSafeInteger(cfg.gateway?.port) ? cfg.gateway.port : null},
    agents:(cfg.agents?.list || []).map(a => ({id:a.id, model:typeof a.model === 'string' ? a.model : a.model?.primary || null,
      fallbacks:strings(a.model?.fallbacks), toolsAllow:strings(a.tools?.allow), toolsDeny:strings(a.tools?.deny)})).sort((a,b)=>ordered(String(a.id),String(b.id))),
    defaults:{model:typeof cfg.agents?.defaults?.model === 'string' ? cfg.agents.defaults.model : cfg.agents?.defaults?.model?.primary || null,
      fallbacks:strings(cfg.agents?.defaults?.model?.fallbacks)},
    providers:Object.entries(cfg.models?.providers || {}).map(([id,p])=>({id,endpoint:endpoint(p.baseUrl),api:typeof p.api==='string'?p.api:null,models:(p.models || []).map(m=>m.id).filter(x=>typeof x === 'string').sort()})).sort((a,b)=>ordered(a.id,b.id)),
    toolPolicy:{allow:strings(cfg.tools?.allow),deny:strings(cfg.tools?.deny)},
  };
}
export class ControlPlane {
  constructor({directory, config, host, now = Date.now, monotonicNow = () => Number(process.hrtime.bigint()/1000000n), maxEvents = 100000}) {
    exactKeys(config, ['runtimeId','agentId','controllerKeys'], ['controlEnabled','hostVersions']);
    this.runtimeId = identifier(config.runtimeId); this.agentId = identifier(config.agentId);
    requireThat(/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(this.agentId), 'AGENT_ID_NONCANONICAL');
    requireThat(config.controllerKeys && typeof config.controllerKeys === 'object' && !Array.isArray(config.controllerKeys) && Object.keys(config.controllerKeys).length > 0, 'KEYS_REQUIRED');
    this.keys = Object.fromEntries(Object.entries(config.controllerKeys).map(([id,pem])=>[identifier(id),publicKey(pem)]));
    this.config = config; this.host = host; this.monotonicNow = monotonicNow; this.lastClock=now();this.clockFault=false;
    this.now = ()=>{const t=now();if(t<this.lastClock)this.clockFault=true;this.lastClock=Math.max(t,this.lastClock);return t;};
    this.leaseUntil = 0; this.jobs = new Map(); this.startTickets=new Map();
    this.journal = new Journal(directory, this.runtimeId, this.now, maxEvents);
    this.initialConfigDigest = this.configDigest(); this.stopping = false;
  }
  projection() { return configProjection(this.host.config()); }
  configDigest() { return sha256(Buffer.from(canonical(this.projection()))); }
  identity() {
    this.journal.fence();
    const digest = this.configDigest();
    return {protocol:PROTOCOL,runtime_id:this.runtimeId,instance_id:this.journal.instance,
      plugin_version:VERSION, host_version:this.host.version || 'UNKNOWN', config_digest:digest,
      config_state:digest === this.initialConfigDigest ? 'MATCH' : 'DRIFT_DETECTED',
      configuration_source:'NATIVE_RUNTIME_CONFIG_PROJECTION', secret_rotation_coverage:false,
      pid:process.pid, observed_process_start_ms:Math.floor(Date.now()-process.uptime()*1000),
      control_enabled:this.config.controlEnabled === true,
      compatibility:this.compatible() ? 'DECLARED_CANDIDATE' : 'OBSERVE_ONLY',
      qualification:'NOT_ESTABLISHED', control_connected:this.leaseUntil > this.now(),
      evidence_head:this.journal.head(),
      capabilities:{observe:true,signed_dispatch:this.compatible(),provider_probe:this.compatible(),
        revoke:true,native_cancel:false,gateway_restart:false,tool_execution:false,sc_mesh:false,acceptance:false}};
  }
  compatible() {
    return this.config.controlEnabled === true && Array.isArray(this.config.hostVersions) &&
      this.config.hostVersions.includes(this.host.version) && this.host.guardsAvailable === true &&
      this.host.harness === 'subagent' && typeof this.host.dispatch === 'function';
  }
  gate() {
    this.now();this.journal.fence(); requireThat(!this.clockFault,'CLOCK_ROLLBACK');requireThat(!this.stopping, 'STOPPING');
    requireThat(this.compatible(), 'OBSERVE_ONLY');
    requireThat(this.configDigest() === this.initialConfigDigest, 'CONFIG_DRIFT');
    requireThat(this.projection().agents.filter(a=>a.id===this.agentId).length===1,'MANAGED_AGENT_MISSING');
    requireThat(this.leaseUntil > this.now(), 'CONTROL_PLANE_DISCONNECTED');
  }
  status(id, content = false) {
    const found = this.journal.existing(identifier(id)); requireThat(found, 'NOT_FOUND');
    const result = {...found.record};
    if (!content) delete result.output_text;
    return result;
  }
  async command(envelope) {
    this.now();requireThat(!this.clockFault,'CLOCK_ROLLBACK');
    const {command:c,digest,key_id} = verifyCommand(envelope,this.keys,this.identity(),this.now());
    switch(c.action) {
      case 'runtime.inspect': exactKeys(c.body, []); return this.identity();
      case 'config.inspect': exactKeys(c.body, []); return {projection:this.projection(),identity:this.identity()};
      case 'evidence.read': exactKeys(c.body,['after','limit']); return {events:this.journal.events(c.body.after,c.body.limit)};
      case 'dispatch.inspect': exactKeys(c.body,['operation_id']); return this.status(c.body.operation_id);
      case 'dispatch.result': exactKeys(c.body,['operation_id']); return this.status(c.body.operation_id,true);
    }
    requireThat(MUTATIONS.has(c.action), 'UNSUPPORTED_CAPABILITY');
    const previous = this.journal.existing(c.operation_id);
    if (previous) { requireThat(previous.digest === digest, 'IDEMPOTENCY_CONFLICT'); return this.status(c.operation_id); }
    this.journal.fence();
    if (c.action === 'lease.renew') {
      exactKeys(c.body, []); requireThat(this.compatible() && !this.stopping, 'OBSERVE_ONLY');
      requireThat(this.configDigest() === this.initialConfigDigest,'CONFIG_DRIFT');
      this.journal.transaction(()=>{
        this.journal.insert(c.operation_id,digest,{operation_id:c.operation_id,state:'RECORDED',action:c.action,expires_at_ms:c.expires_at_ms,acceptance:'NOT_EVALUATED'});
        this.journal.event('control.lease', {operation_id:c.operation_id,key_id,expires_at_ms:c.expires_at_ms});
      });
      this.leaseUntil = Math.max(this.leaseUntil,c.expires_at_ms);
      return this.status(c.operation_id);
    }
    if (c.action === 'dispatch.revoke') {
      exactKeys(c.body,['operation_id']);
      const target = this.status(c.body.operation_id,true);
      requireThat(['dispatch.submit','provider.probe'].includes(target.action), 'NOT_DISPATCH');
      this.journal.transaction(()=>{
        target.revoked = true;
        if (!TERMINAL.has(target.state)) target.state = 'REVOKED';
        this.journal.put(target.operation_id,target);
        this.journal.insert(c.operation_id,digest,{operation_id:c.operation_id,action:c.action,state:'RECORDED',target:target.operation_id,acceptance:'NOT_EVALUATED'});
        this.journal.event('dispatch.revoked',{operation_id:target.operation_id,revocation_id:c.operation_id,native_stop_verified:false});
      });
      this.jobs.get(target.operation_id)?.abort.abort();
      return this.status(c.operation_id);
    }
    this.gate();
    const probe = c.action === 'provider.probe';
    const projection=this.projection();
    requireThat(projection.defaults.fallbacks.length===0 && projection.agents.filter(a=>a.id===this.agentId).every(a=>a.fallbacks.length===0),'UNQUALIFIED_FALLBACK_CONFIG');
    exactKeys(c.body, probe ? ['provider','model','timeout_ms'] : ['provider','model','timeout_ms','prompt']);
    identifier(c.body.provider); boundedText(c.body.model,256);
    requireThat(/^[A-Za-z0-9][A-Za-z0-9_./:-]{0,255}$/.test(c.body.model),'INVALID_MODEL');
    requireThat(Number.isSafeInteger(c.body.timeout_ms) && c.body.timeout_ms >= 100 && c.body.timeout_ms <= 60000, 'TIMEOUT_OUT_OF_RANGE');
    if (!probe) boundedText(c.body.prompt, 220000);
    const managedAgent=projection.agents.find(a=>a.id===this.agentId);
    requireThat(managedAgent?.model===`${c.body.provider}/${c.body.model}`,'ROUTE_NOT_CONFIGURED');
    requireThat(this.jobs.size === 0 && !this.journal.all().some(x=>['INDETERMINATE','REVOKED'].includes(x.state) && !x.resolved), 'RUNTIME_NOT_IDLE');
    const sessionKey = `agent:${this.agentId}:residual:${c.operation_id}`;
    const startedMono=this.monotonicNow();
    const deadlineMono=startedMono+c.body.timeout_ms;
    const record = {operation_id:c.operation_id,action:c.action,instance_id:this.journal.instance,input_sha256:digest,
      config_digest:this.initialConfigDigest,session_key:sessionKey,provider:c.body.provider,model:c.body.model,
      state:'INVOCATION_STARTED',started_at_ms:this.now(),deadline_ms:this.now()+c.body.timeout_ms,
      revoked:false,acceptance:'NOT_EVALUATED',trust:'RUNTIME_REPORTED'};
    this.journal.transaction(()=>{
      this.gate();
      this.journal.insert(c.operation_id,digest,record);
      this.journal.event('invocation.started',{operation_id:c.operation_id,action:c.action,input_sha256:digest,provider:c.body.provider,model:c.body.model});
    });
    const abort = new AbortController();
    const job = {abort,done:null,deadlineMono}; this.jobs.set(c.operation_id,job);
    job.done = this.execute(c,record,abort,deadlineMono).finally(()=>this.jobs.delete(c.operation_id));
    return this.status(c.operation_id);
  }
  async execute(command,record,abort,deadlineMono) {
    const probe = command.action === 'provider.probe';
    const challenge = `RESIDUAL_PROBE_${randomUUID()}`;
    const timer = setTimeout(()=>abort.abort(),command.body.timeout_ms); timer.unref?.();
    try {
      // Revalidate after durable intent and immediately before crossing into the native runtime.
      this.gate();
      const executionPrompt=probe ? `Reply with exactly this string and no other text: ${challenge}` : command.body.prompt;
      this.startTickets.set(record.session_key,sha256(Buffer.from(executionPrompt)));
      const result = await this.host.dispatch({
        operationId:record.operation_id,sessionKey:record.session_key,agentId:this.agentId,
        provider:record.provider,model:record.model,timeoutMs:command.body.timeout_ms,
        prompt:executionPrompt,
        signal:abort.signal,onRun:runId=>{
          identifier(runId);
          this.journal.transaction(()=>{
            const live = this.status(record.operation_id,true); live.run_id=runId;
            if (!live.revoked) live.state='RUNNING';
            this.journal.put(record.operation_id,live);
            this.journal.event('execution.running',{operation_id:record.operation_id,run_id:runId});
          });
        }
      });
      this.journal.fence();
      const live = this.status(record.operation_id,true);
      const finishedWall=this.now();const finishedMono=this.monotonicNow();
      requireThat(!this.clockFault && !this.stopping && !abort.signal.aborted && !live.revoked &&
        finishedWall <= live.deadline_ms && finishedMono <= deadlineMono, 'OUTCOME_AFTER_FENCE');
      requireThat(this.configDigest() === record.config_digest, 'CONFIG_DRIFT');
      if(!probe)requireThat(live.start_admitted===true,'NATIVE_ADMISSION_UNPROVEN');
      boundedText(result.text,262144);
      for(const k of ['provider','model'])if(result[k]!==undefined)boundedText(result[k],256);
      const routeMatched = result.provider === record.provider && result.model === record.model;
      const state = routeMatched && (!probe || result.text.trim() === challenge) ? 'COMPLETED' : 'FAILED';
      this.journal.transaction(()=>{
        this.journal.put(record.operation_id,{...live,state,finished_at_ms:finishedWall,output_text:result.text,
          output_sha256:sha256(Buffer.from(result.text)),observed_provider:typeof result.provider==='string'?result.provider:'UNKNOWN',
          observed_model:typeof result.model==='string'?result.model:'UNKNOWN',
          route_matched:routeMatched,probe_observation:probe ? (state === 'COMPLETED' ? 'CHALLENGE_MATCHED' : 'CHALLENGE_OR_ROUTE_FAILED') : 'NOT_APPLICABLE',
          qualification:'NOT_ESTABLISHED'});
        this.journal.event('execution.result',{operation_id:record.operation_id,state,route_matched:routeMatched,
          output_sha256:sha256(Buffer.from(result.text)),qualification:'NOT_ESTABLISHED'});
      });
    } catch(error) {
      try {
        this.journal.transaction(()=>{
          const live = this.status(record.operation_id,true);
          live.state = live.revoked ? 'REVOKED' : 'INDETERMINATE';
          live.reason = error instanceof ControlError ? error.code : 'HOST_OUTCOME_UNKNOWN';
          // Never persist provider exception strings, prompts, headers, or credentials.
          this.journal.put(record.operation_id,live);
          this.journal.event('execution.indeterminate',{operation_id:record.operation_id,reason:live.reason});
        });
      } catch { /* Stale instance cannot modify the successor's authoritative journal. */ }
    } finally { clearTimeout(timer);this.startTickets.delete(record.session_key); }
  }
  isManaged(context) {
    return context?.agentId === this.agentId || (typeof context?.sessionKey === 'string' && context.sessionKey.startsWith(`agent:${this.agentId}:`));
  }
  beforeAgent(event,context) {
    if(!this.isManaged(context) && (context?.agentId || context?.sessionKey))return undefined;
    try {
      this.gate();
      requireThat(typeof context?.sessionKey==='string' && typeof event?.prompt==='string' && (!context.agentId || context.agentId===this.agentId),'UNBOUND_NATIVE_RUN');
      const ticket=this.startTickets.get(context.sessionKey);
      requireThat(ticket && sha256(Buffer.from(event.prompt))===ticket,'UNAUTHORIZED_NATIVE_RUN');
      const record=this.journal.all().find(x=>x.session_key===context.sessionKey);
      requireThat(record && ['dispatch.submit','provider.probe'].includes(record.action) && !record.revoked && !record.start_admitted &&
        ['INVOCATION_STARTED','RUNNING'].includes(record.state) && record.deadline_ms>=this.now(),'UNAUTHORIZED_NATIVE_RUN');
      this.journal.transaction(()=>{
        record.start_admitted=true;this.journal.put(record.operation_id,record);
        this.journal.event('native.admitted',{operation_id:record.operation_id});
      });
      this.startTickets.delete(context.sessionKey);
      return {outcome:'pass'};
    }catch{return {outcome:'block',reason:'RESIDUAL_NATIVE_ADMISSION_DENIED'};}
  }
  beforeTool(_event,context) {
    // The initial candidate surface is text-only. No exception can turn into fail-open tool execution.
    if (this.isManaged(context) || !context?.agentId && !context?.sessionKey) return {block:true,blockReason:'RESIDUAL_TEXT_ONLY_PROFILE'};
    return undefined;
  }
  observe(type,event,context) {
    if (!this.isManaged(context)) return;
    const operation = this.journal.all().find(x=>x.session_key===context.sessionKey && (!x.run_id || !event.runId || x.run_id===event.runId));
    if (!operation) return;
    const payload = {operation_id:operation.operation_id};
    // No unbounded/unknown event properties are copied into ordinary evidence.
    for (const k of ['provider','model','runId','toolName']) if (typeof event[k]==='string' && Buffer.byteLength(event[k])<=256) payload[k]=event[k];
    if (typeof event.success === 'boolean') payload.success=event.success;
    try { this.journal.append(type,payload); } catch { this.leaseUntil=0; }
  }
  async settle() { await Promise.all([...this.jobs.values()].map(j=>j.done)); }
  stop() { this.stopping=true;this.leaseUntil=0;for(const j of this.jobs.values())j.abort.abort(); }
  close() { this.stop(); this.journal.close(); }
}
