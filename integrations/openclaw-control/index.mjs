import { join } from 'node:path';
import { readFileSync } from 'node:fs';
import { ControlPlane } from './core.mjs';
import { canonical, sha256, requireThat, ControlError, MAX_WIRE_BYTES } from './protocol.mjs';
import { ROUTE } from './route.mjs';
export { ROUTE };
export const sourceDigest = () => sha256(Buffer.from(canonical(Object.fromEntries(
  ['index.mjs','core.mjs','protocol.mjs','journal.mjs','route.mjs','openclaw.plugin.json','package.json'].map(name=>[name,sha256(readFileSync(new URL(name,import.meta.url)))])
))));
const loopback = address => ['127.0.0.1','::1','::ffff:127.0.0.1'].includes(address);
function reply(res,status,payload) {
  res.statusCode=status;
  res.setHeader('content-type','application/json');res.setHeader('cache-control','no-store');
  res.setHeader('x-content-type-options','nosniff');res.end(JSON.stringify(payload));
}
async function body(req) {
  let size=0;const chunks=[];
  req.setTimeout?.(5000,()=>req.destroy());
  for await(const chunk of req) {
    size+=Buffer.byteLength(chunk);requireThat(size<=MAX_WIRE_BYTES,'REQUEST_TOO_LARGE');chunks.push(Buffer.from(chunk));
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
  catch { throw new ControlError('SCHEMA_INVALID'); }
}
export function register(api) {
  let plane = null;
  const outputs = new Map();
  const pc = api.pluginConfig || {};
  const managed = ctx => ctx?.agentId === pc.agentId ||
    (typeof ctx?.sessionKey === 'string' && ctx.sessionKey.startsWith(`agent:${pc.agentId}:`));
  requireThat(typeof api.registerService==='function' && typeof api.registerHttpRoute==='function' && typeof api.on==='function','SDK_UNSUPPORTED');
  api.on('before_agent_run',(event,ctx)=>{
    if(plane)return plane.beforeAgent(event,ctx);
    if(managed(ctx) || !ctx?.agentId && !ctx?.sessionKey)return {outcome:'block',reason:'RESIDUAL_NOT_READY'};
  },{priority:10000});
  api.on('before_tool_call',(event,ctx)=> {
    if(plane) return plane.beforeTool(event,ctx);
    if(managed(ctx) || !ctx?.agentId && !ctx?.sessionKey) return {block:true,blockReason:'RESIDUAL_NOT_READY'};
  },{priority:10000});
  for(const name of ['llm_input','llm_output','agent_end','session_start','session_end','after_tool_call']) {
    api.on(name,(event,ctx)=>{
      if(!managed(ctx)) return;
      if(name==='llm_output' && plane && plane.journal.all().some(r=>r.session_key===ctx?.sessionKey && ['INVOCATION_STARTED','RUNNING'].includes(r.state)) && typeof ctx?.sessionKey==='string' && Array.isArray(event.assistantTexts)) {
        const text=event.assistantTexts.filter(x=>typeof x==='string').join('\n');
        if(Buffer.byteLength(text)<=262144 && outputs.size<100) outputs.set(ctx.sessionKey,{text,provider:event.provider,model:event.model,runId:event.runId});
      }
      plane?.observe(`openclaw.${name}`,event,ctx);
    });
  }
  api.registerService({id:'residual-control',start(ctx){
    requireThat(!plane,'ALREADY_STARTED');
    const rt=api.runtime;
    const current=()=>typeof rt.config?.current==='function' ? rt.config.current() : api.config;
    const host={version:rt.version,config:current,harness:'subagent',guardsAvailable:api.registrationMode==='full',
      async dispatch(p){
        requireThat(typeof rt.subagent?.run==='function' && typeof rt.subagent?.waitForRun==='function','SDK_UNSUPPORTED');
        outputs.delete(p.sessionKey);
        try {
          requireThat(!p.signal.aborted,'AUTHORITY_EXPIRED');
          const {runId}=await rt.subagent.run({sessionKey:p.sessionKey,message:p.prompt,
            deliver:false,idempotencyKey:p.operationId,lightContext:true});
          p.onRun(runId);
          const result=await rt.subagent.waitForRun({runId,timeoutMs:p.timeoutMs});
          requireThat(result.status==='ok','HOST_OUTCOME_UNKNOWN');
          const output=outputs.get(p.sessionKey);
          requireThat(output && output.runId===runId,'OUTPUT_PROVENANCE_MISSING');
          return output;
        } finally { outputs.delete(p.sessionKey); }
      }
    };
    plane=new ControlPlane({directory:join(ctx.stateDir,'residual-control'),config:pc,host});
  },async stop(){
    if(!plane)return;
    const old=plane;plane=null;old.stop();
    // No unbounded wait or fabricated cancellation receipt on shutdown.
    await Promise.race([old.settle(),new Promise(resolve=>setTimeout(resolve,500))]);
    old.close();outputs.clear();
  }});
  api.registerHttpRoute({path:ROUTE,match:'exact',auth:'gateway',async handler(req,res){
    try {
      requireThat(loopback(req.socket?.remoteAddress),'LOOPBACK_REQUIRED');
      requireThat(!req.headers.origin,'BROWSER_ORIGIN_DENIED');
      requireThat(req.url===ROUTE,'ROUTE_INVALID');
      requireThat(plane,'RUNTIME_UNAVAILABLE');
      if(req.method==='GET') return reply(res,200,{identity:{...plane.identity(),plugin_source_sha256:sourceDigest()}});
      requireThat(req.method==='POST','METHOD_NOT_ALLOWED');
      requireThat((req.headers['content-type'] || '').split(';')[0].trim()==='application/json','CONTENT_TYPE_REQUIRED');
      const result=await plane.command(await body(req));
      return reply(res,200,{result});
    }catch(error){
      const code=error instanceof ControlError ? error.code : 'INTERNAL_FAILURE';
      return reply(res,code==='RUNTIME_UNAVAILABLE'?503:code==='METHOD_NOT_ALLOWED'?405:400,{error:{code}});
    }
  }});
}
export default {id:'residual-control',name:'RESIDUAL OpenClaw Control',description:'Signed, evidence-producing text-only runtime control candidate',register};
