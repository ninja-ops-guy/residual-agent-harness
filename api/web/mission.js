// RESIDUAL Web mock gateway. Preview only: no worker/provider/tool dispatch.
const crypto = require('crypto');
const MAX_BODY=8192, MAX_MISSION=4096;
const allowed=new Set(['mission','mode']);
function send(res,status,obj){res.statusCode=status;res.setHeader('content-type','application/json');res.setHeader('cache-control','no-store');res.end(JSON.stringify(obj))}
module.exports=async function handler(req,res){
 const rid=crypto.randomUUID();res.setHeader('x-residual-request-id',rid);
 if(req.method!=='POST')return send(res,405,{ok:false,error:'METHOD_NOT_ALLOWED',request_id:rid});
 let raw='';for await(const c of req){raw+=c;if(Buffer.byteLength(raw)>MAX_BODY)return send(res,413,{ok:false,error:'PAYLOAD_TOO_LARGE',request_id:rid})}
 let body;try{body=JSON.parse(raw)}catch{return send(res,400,{ok:false,error:'INVALID_JSON',request_id:rid})}
 if(!body||Array.isArray(body)||typeof body!=='object')return send(res,400,{ok:false,error:'INVALID_ENVELOPE',request_id:rid});
 const unknown=Object.keys(body).filter(k=>!allowed.has(k));if(unknown.length)return send(res,400,{ok:false,error:'UNKNOWN_FIELDS',request_id:rid});
 if(body.mode!=='demo')return send(res,403,{ok:false,error:'CAPABILITY_DENIED',request_id:rid});
 if(typeof body.mission!=='string'||!body.mission.trim()||Buffer.byteLength(body.mission)>MAX_MISSION)return send(res,400,{ok:false,error:'INVALID_MISSION',request_id:rid});
 const digest=crypto.createHash('sha256').update(body.mission,'utf8').digest('hex');
 return send(res,202,{ok:true,authoritative:false,execution:'scripted-mock',mode:'demo',request_id:rid,mission_digest:digest,capabilities:['read-only'],worker_credentials_issued:false,status:'PREVIEW_ACCEPTED'});
}