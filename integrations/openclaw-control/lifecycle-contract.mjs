// Pure lifecycle action-plan and verification contracts.
// This module never starts/stops processes. Execution belongs to an authorized external operator/supervisor.
import { canonical,sha256,requireThat,boundedText,ControlError } from './protocol.mjs';

function exactObject(value,required,optional=[]){
  requireThat(value&&typeof value==='object'&&!Array.isArray(value),'CAPTURE_INVALID');
  requireThat(required.every(k=>Object.hasOwn(value,k)) &&
    Object.keys(value).every(k=>required.includes(k)||optional.includes(k)),'CAPTURE_INVALID');
}
function wsUrl(value){
  const u=new URL(value);
  requireThat(['ws:','wss:'].includes(u.protocol)&&['127.0.0.1','[::1]','::1','localhost'].includes(u.hostname)&&
    !u.username&&!u.password&&!u.search&&!u.hash,'GATEWAY_URL_DENIED');
  return u.href.replace(/\/$/,'');
}
function cliCapture(value){
  exactObject(value,['exit_code','stdout_sha256','stderr_sha256'],['signal']);
  requireThat(value.exit_code===0&&!value.signal,'CLI_EXECUTION_FAILED');
  for(const name of ['stdout_sha256','stderr_sha256'])requireThat(typeof value[name]==='string'&&/^[a-f0-9]{64}$/.test(value[name]),'CAPTURE_INVALID');
  return value;
}
function abortCapture(value){
  exactObject(value,['ok','aborted','runIds']);
  requireThat(value.ok===true&&typeof value.aborted==='boolean'&&Array.isArray(value.runIds)&&
    value.runIds.every(x=>typeof x==='string'&&x.length<=256),'ABORT_CAPTURE_INVALID');
  return value;
}
function identity(value){
  requireThat(value&&typeof value==='object'&&!Array.isArray(value),'IDENTITY_INVALID');
  for(const name of ['runtime_id','instance_id','host_version','config_digest','plugin_source_sha256'])
    boundedText(value[name],256);
  requireThat(value.evidence_head&&Number.isSafeInteger(value.evidence_head.sequence)&&value.evidence_head.sequence>=0&&
    typeof value.evidence_head.sha256==='string'&&/^[a-f0-9]{64}$/.test(value.evidence_head.sha256),'IDENTITY_INVALID');
  return value;
}
export function buildCancelPlan(status,gateway){
  requireThat(status&&['INVOCATION_STARTED','RUNNING'].includes(status.state),'CANCEL_TARGET_NOT_RUNNING');
  boundedText(status.operation_id,128);boundedText(status.session_key,512);boundedText(status.run_id,256);
  const params=canonical({sessionKey:status.session_key,runId:status.run_id});
  const argv=['gateway','call','chat.abort','--url',wsUrl(gateway),'--params',params,'--json'];
  return {
    schema:'residual.openclaw.lifecycle_plan.v1',action:'cancel',operation_id:status.operation_id,
    credential_transport:'OPENCLAW_GATEWAY_TOKEN_ENV_ONLY',
    steps:[
      {id:'native-abort',executor:'openclaw-cli',argv},
      {id:'revoke-admission',executor:'residual-controller',action:'dispatch.revoke',body:{operation_id:status.operation_id}},
      {id:'native-abort-proof',executor:'openclaw-cli',argv},
    ],
    params_sha256:sha256(Buffer.from(params)),
  };
}
export function verifyCancel({plan,beforeIdentity,afterIdentity,beforeStatus,firstAbort,firstCli,revokedStatus,secondAbort,secondCli}){
  requireThat(plan?.schema==='residual.openclaw.lifecycle_plan.v1'&&plan.action==='cancel','PLAN_INVALID');
  const b=identity(beforeIdentity),a=identity(afterIdentity);
  requireThat(b.runtime_id===a.runtime_id&&b.instance_id===a.instance_id,'INSTANCE_CHANGED_DURING_CANCEL');
  requireThat(beforeStatus.operation_id===plan.operation_id&&beforeStatus.run_id&&beforeStatus.session_key,'CANCEL_CAPTURE_MISMATCH');
  const first=abortCapture(firstAbort),second=abortCapture(secondAbort);cliCapture(firstCli);cliCapture(secondCli);
  requireThat(first.aborted===true&&first.runIds.includes(beforeStatus.run_id),'NATIVE_CANCEL_NOT_OBSERVED');
  requireThat(revokedStatus.operation_id===plan.operation_id&&revokedStatus.revoked===true&&revokedStatus.state==='REVOKED','REVOCATION_NOT_BOUND');
  requireThat(second.aborted===false&&!second.runIds.includes(beforeStatus.run_id),'NATIVE_CANCEL_NOT_SETTLED');
  return {schema:'residual.openclaw.lifecycle_receipt.v1',action:'cancel',result:'NATIVE_CANCEL_VERIFIED',
    operation_id:plan.operation_id,runtime_id:a.runtime_id,instance_id:a.instance_id,run_id:beforeStatus.run_id,
    session_key_sha256:sha256(Buffer.from(beforeStatus.session_key)),params_sha256:plan.params_sha256,
    acceptance:'NOT_EVALUATED',qualification:'NOT_ESTABLISHED'};
}
export function buildRestartPlan(identityBefore,{wait='30s'}={}){
  identity(identityBefore);
  requireThat(/^(?:[1-9]\d*)(?:s|m)$/.test(wait),'RESTART_WAIT_INVALID');
  const amount=Number(wait.slice(0,-1)),unit=wait.at(-1);
  requireThat(amount*(unit==='m'?60:1)<=120,'RESTART_WAIT_INVALID');
  return {schema:'residual.openclaw.lifecycle_plan.v1',action:'restart',credential_transport:'OPENCLAW_GATEWAY_TOKEN_ENV_ONLY',
    argv:['gateway','restart','--safe','--wait',wait,'--json'],
    before:{runtime_id:identityBefore.runtime_id,instance_id:identityBefore.instance_id,
      config_digest:identityBefore.config_digest,plugin_source_sha256:identityBefore.plugin_source_sha256,
      evidence_head:identityBefore.evidence_head}};
}
export function verifyRestart({plan,beforeIdentity,afterIdentity,cli,evidenceDelta}){
  requireThat(plan?.schema==='residual.openclaw.lifecycle_plan.v1'&&plan.action==='restart','PLAN_INVALID');
  const b=identity(beforeIdentity),a=identity(afterIdentity);cliCapture(cli);
  requireThat(plan.before.runtime_id===b.runtime_id&&plan.before.instance_id===b.instance_id,'PLAN_STALE');
  requireThat(a.instance_id!==b.instance_id,'RESTART_REPLACEMENT_NOT_OBSERVED');
  requireThat(a.runtime_id===b.runtime_id&&a.host_version===b.host_version&&
    a.config_digest===b.config_digest&&a.plugin_source_sha256===b.plugin_source_sha256,'RESTART_IDENTITY_MISMATCH');
  requireThat(a.control_connected===false,'STALE_AUTHORITY_SURVIVED_RESTART');
  requireThat(Number.isSafeInteger(a.observed_process_start_ms)&&Number.isSafeInteger(b.observed_process_start_ms)&&
    a.observed_process_start_ms>=b.observed_process_start_ms,'RESTART_PROCESS_TIME_INVALID');
  requireThat(evidenceDelta&&evidenceDelta.sequence===a.evidence_head.sequence&&evidenceDelta.sha256===a.evidence_head.sha256&&
    Array.isArray(evidenceDelta.observations),'RESTART_EVIDENCE_INVALID');
  requireThat(evidenceDelta.observations.some(row=>row.type==='runtime.started'&&row.instance_id===a.instance_id),'RESTART_EVENT_MISSING');
  return {schema:'residual.openclaw.lifecycle_receipt.v1',action:'restart',result:'RESTART_VERIFIED',
    runtime_id:a.runtime_id,before_instance_id:b.instance_id,after_instance_id:a.instance_id,
    before_process_start_ms:b.observed_process_start_ms,after_process_start_ms:a.observed_process_start_ms,
    config_digest:a.config_digest,plugin_source_sha256:a.plugin_source_sha256,
    evidence_tip_sha256:a.evidence_head.sha256,evidence_sequence:a.evidence_head.sequence,
    acceptance:'NOT_EVALUATED',qualification:'NOT_ESTABLISHED'};
}
