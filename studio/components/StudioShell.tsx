"use client";
import {useMemo,useState} from "react";
import Editor from "@monaco-editor/react";

type Worker={id:string;role:string;state:"running"|"verified"|"blocked"|"idle";task:string;receipt?:string};
const workers:Worker[]=[
{id:"coord-01",role:"Coordinator",state:"running",task:"Plan ready frontier"},
{id:"worker-01",role:"Worker",state:"verified",task:"Implement auth boundary",receipt:"wr:8f91…"},
{id:"worker-02",role:"Worker",state:"running",task:"Add scheduler tests"},
{id:"worker-03",role:"Worker",state:"blocked",task:"Await WorkerReceipt dependency"},
{id:"verify-01",role:"Verifier",state:"running",task:"Acceptance + security checks"}];
const tree=["residual/","  factory/","    runtime.py","    evidence_receipts.py","    m4_integrator.py","tests/","  test_factory_runtime.py","docs/"];
const sample=`from residual.factory import FactoryRuntime\n\n# Studio edits remain subordinate to the approved ExecutionPlan.\ndef run_factory(plan, approval):\n    runtime = FactoryRuntime()\n    return runtime.execute(plan, approval)\n`;
export default function StudioShell(){
 const [tab,setTab]=useState("Editor"); const [selected,setSelected]=useState("runtime.py");
 const verified=useMemo(()=>workers.filter(w=>w.state==="verified").length,[]);
 return <main className="shell">
  <header><div><b>RESIDUAL</b><span>STUDIO</span></div><div className="mission"><i/> FACTORY RUN · ACTIVE</div><button>Observer mode</button></header>
  <section className="workspace">
   <aside className="explorer"><h3>PROJECT</h3><div className="repo">residual-agent-harness <em>main*</em></div>{tree.map((x,i)=><button key={i} className={x.includes(selected)?"sel":""} onClick={()=>x.includes(".py")&&setSelected(x.trim())}>{x}</button>)}<div className="plan"><small>APPROVED PLAN</small><strong>9b74…c18e</strong><span>16 requirements · frozen</span></div></aside>
   <section className="editor"><nav><button className="active">{selected} ×</button><button>m4_integrator.py</button></nav><Editor height="100%" defaultLanguage="python" theme="vs-dark" value={sample} options={{minimap:{enabled:false},fontSize:14,fontLigatures:true,padding:{top:16},automaticLayout:true}}/></section>
   <aside className="swarm"><div className="swarmHead"><div><small>SWARM CONTROL</small><h2>Factory Mission</h2></div><span>05:42</span></div><div className="progress"><div><span>11 / 16 accepted</span><span>69%</span></div><b><i/></b></div>{workers.map(w=><article key={w.id}><div className={"dot "+w.state}/><div><strong>{w.role}</strong><small>{w.id}</small><p>{w.task}</p>{w.receipt&&<code>{w.receipt}</code>}</div><span className={w.state}>{w.state}</span></article>)}<div className="metrics"><div><small>READY</small><b>3</b></div><div><small>BLOCKED</small><b>2</b></div><div><small>RECEIPTS</small><b>{verified+10}</b></div></div></aside>
  </section>
  <section className="bottom"><nav>{["Terminal","Evidence","Receipts","Tests","Git","Timeline"].map(x=><button onClick={()=>setTab(x)} className={tab===x?"active":""} key={x}>{x}</button>)}</nav><div className="console"><code><span>$</span> residual factory status run-7fa2</code><p>plan <b>9b74…c18e</b> · workers 5 · accepted 11/16 · verifier retries 2</p><p className="ok">✓ evidence chain valid &nbsp; ✓ Station signatures valid &nbsp; ✓ source branch unchanged</p></div><div className="status"><span>LOCAL</span><span>qwen2.5-coder:7b</span><span>Evidence Bus ●</span><span>Station ●</span></div></section>
 </main>
}
