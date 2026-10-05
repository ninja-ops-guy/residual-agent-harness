import { generateKeyPairSync,randomUUID } from 'node:crypto';
import { mkdtempSync,rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { ControlPlane } from '../core.mjs';
import { PROTOCOL,signCommand } from '../protocol.mjs';
export function fixture(t,options={}) {
  const directory=mkdtempSync(join(tmpdir(),'residual-oc-'));
  const keys=generateKeyPairSync('ed25519');
  const config={runtimeId:'runtime-test',agentId:'residual-worker',controllerKeys:{owner:keys.publicKey.export({type:'spki',format:'pem'})},controlEnabled:true,hostVersions:['2026.6.1'],...options.config};
  const runtimeConfig={agents:{list:[{id:'residual-worker',model:'test/model'}]},models:{providers:{test:{baseUrl:'http://127.0.0.1:9999/v1',models:[{id:'model'}]}}}};
  let time=1700000000000,mono=1000,calls=0,plane;
  const host={version:'2026.6.1',config:()=>runtimeConfig,harness:'subagent',guardsAvailable:true,
    dispatch:async p=>{calls++;const decision=plane.beforeAgent({prompt:p.prompt},{agentId:config.agentId,sessionKey:p.sessionKey});
      if(decision?.outcome!=='pass')throw new Error('gate rejected');
      p.onRun('run-'+p.operationId);const probePrefix='Reply with exactly this string and no other text: ';
      return {text:p.prompt.startsWith(probePrefix)?p.prompt.slice(probePrefix.length):'result',provider:p.provider,model:p.model};},...options.host};
  function open(){plane=new ControlPlane({directory,config,host,now:options.now??(()=>time),monotonicNow:options.monotonicNow??(()=>mono),maxEvents:options.maxEvents??100000});return plane;}
  open();t.after(async()=>{try{plane.close();}finally{rmSync(directory,{recursive:true,force:true});}});
  const command=(action,body={},overrides={})=>({protocol:PROTOCOL,operation_id:randomUUID(),runtime_id:plane.runtimeId,
    instance_id:plane.identity().instance_id,config_digest:plane.identity().config_digest,
    issued_at_ms:time,expires_at_ms:time+20000,action,body,...overrides});
  const envelope=(action,body,overrides)=>signCommand(command(action,body,overrides),keys.privateKey,'owner');
  return {directory,keys,config,runtimeConfig,host,open,get plane(){return plane;},get calls(){return calls;},
    time:()=>time,mono:()=>mono,advance:ms=>{time+=ms;if(ms>0)mono+=ms;},advanceWall:ms=>{time+=ms;},advanceMono:ms=>{mono+=ms;},command,envelope,
    send:(action,body,overrides)=>plane.command(envelope(action,body,overrides)),
    lease:()=>plane.command(envelope('lease.renew',{})),
    task:(overrides={})=>({provider:'test',model:'model',timeout_ms:1000,prompt:'Return result',...overrides})};
}
export function isCode(code){return error=>error?.code===code;}
export function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};}
