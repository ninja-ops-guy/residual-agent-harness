export const runtime="nodejs";
export async function GET(){
 const upstream=process.env.RESIDUAL_FACTORY_API;
 if(!upstream)return new Response("Factory API not configured",{status:503});
 try{const r=await fetch(new URL("/v1/factory/events",upstream),{headers:{accept:"text/event-stream"},cache:"no-store"});if(!r.ok||!r.body)return new Response("Factory event stream unavailable",{status:502});return new Response(r.body,{headers:{"content-type":"text/event-stream","cache-control":"no-cache, no-transform","connection":"keep-alive"}})}catch{return new Response("Factory event stream unavailable",{status:502})}
}
