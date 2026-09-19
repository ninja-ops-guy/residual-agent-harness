import {NextRequest,NextResponse} from "next/server";
export const runtime="nodejs";
const allowed=new Set(["plan","approve","run","cancel","integrate"]);
export async function POST(req:NextRequest){
 const upstream=process.env.RESIDUAL_FACTORY_API;if(!upstream)return NextResponse.json({ok:false,error:"Factory API not configured"},{status:503});
 let body:any;try{body=await req.json()}catch{return NextResponse.json({ok:false,error:"invalid JSON"},{status:400})}
 if(!body||!allowed.has(body.action))return NextResponse.json({ok:false,error:"unsupported Factory action"},{status:400});
 const token=process.env.RESIDUAL_STUDIO_CONTROL_TOKEN;if(!token)return NextResponse.json({ok:false,error:"Studio control is disabled"},{status:403});
 try{const r=await fetch(new URL("/v1/factory/control",upstream),{method:"POST",headers:{"content-type":"application/json","authorization":`Bearer ${token}`},body:JSON.stringify(body),cache:"no-store",signal:AbortSignal.timeout(10000)});const text=await r.text();return new NextResponse(text,{status:r.status,headers:{"content-type":r.headers.get("content-type")||"application/json"}})}catch{return NextResponse.json({ok:false,error:"Factory control unavailable"},{status:502})}
}
