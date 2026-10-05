import {NextResponse} from "next/server";
export const runtime="nodejs";
export async function GET(){
 const upstream=process.env.RESIDUAL_FACTORY_API;
 if(!upstream)return NextResponse.json({connected:false,reason:"RESIDUAL_FACTORY_API is not configured"},{status:503});
 try{const r=await fetch(new URL("/v1/factory/snapshot",upstream),{cache:"no-store",signal:AbortSignal.timeout(3000)});if(!r.ok)throw new Error("upstream "+r.status);return NextResponse.json({connected:true,snapshot:await r.json()});}
 catch(e){return NextResponse.json({connected:false,reason:e instanceof Error?e.message:"Factory unavailable"},{status:503});}
}
