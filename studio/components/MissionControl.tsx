"use client";
import {useState} from "react";
export default function MissionControl({runId,planHash,onChanged}:{runId:string;planHash:string;onChanged:()=>void}){
 const [busy,setBusy]=useState(""),[message,setMessage]=useState("");
 async function act(action:string){if(!confirm(`Send Factory action: ${action}?\nPlan: ${planHash}\nRun: ${runId}`))return;setBusy(action);setMessage("");try{const r=await fetch("/api/factory/control",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({action,run_id:runId,plan_hash:planHash})});const j=await r.json().catch(()=>({}));setMessage(r.ok?(j.status||"accepted"):(j.error||"rejected"));if(r.ok)onChanged()}catch{setMessage("control request failed")}finally{setBusy("")}}
 return <div className="controls"><small>HUMAN AUTHORITY</small><div>{["approve","run","cancel","integrate"].map(a=><button key={a} disabled={!!busy||planHash==="—"} onClick={()=>act(a)}>{busy===a?"…":a}</button>)}</div>{message&&<p>{message}</p>}</div>
}
