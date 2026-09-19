from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, tempfile, time, urllib.request
from pathlib import Path

TASKS = [
 {"id":"A","prompt":"Return ONLY Python source for function clamp(value, low, high): raise ValueError if low > high; otherwise clamp value.","file":"a.py"},
 {"id":"B","prompt":"Return ONLY Python source for function safe_mean(values): raise ValueError on empty input; otherwise return arithmetic mean.","file":"b.py"}
]

def call(base, model, task):
    payload=json.dumps({"model":model,"prompt":task["prompt"],"stream":False,"options":{"temperature":0}}).encode()
    started=time.perf_counter()
    req=urllib.request.Request(base+"/api/generate",data=payload,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=300) as response: data=json.load(response)
    return {"task":task["id"],"text":data["response"],"elapsed_s":time.perf_counter()-started,
            "prompt_tokens":data.get("prompt_eval_count",0),"completion_tokens":data.get("eval_count",0)}

def source(text):
    text=text.strip(); fence=chr(96)*3
    if text.startswith(fence):
        lines=text.splitlines()[1:]
        if lines and lines[-1].strip()==fence: lines=lines[:-1]
        text="\n".join(lines)
    return text.strip()+"\n"

def verify(task, text):
    ns={}
    try:
        exec(compile(source(text),task["file"],"exec"),ns)
        if task["id"]=="A":
            f=ns["clamp"]; ok=(f(-1,0,2)==0 and f(3,0,2)==2 and f(1,0,2)==1)
            try: f(1,2,0); ok=False
            except ValueError: pass
        else:
            f=ns["safe_mean"]; ok=(f([2,4,6])==4)
            try: f([]); ok=False
            except ValueError: pass
        return bool(ok)
    except Exception:
        return False

def condition(base,model,parallel):
    started=time.perf_counter()
    if parallel:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(call,base,model,t) for t in TASKS]
            results=[f.result() for f in futures]
    else:
        results=[call(base,model,t) for t in TASKS]
    wall=time.perf_counter()-started
    checks=[verify(t,r["text"]) for t,r in zip(TASKS,results)]
    return {"wall_s":wall,"passed":sum(checks),"checks":checks,
            "tokens":sum(r["prompt_tokens"]+r["completion_tokens"] for r in results),
            "worker_elapsed_s":sum(r["elapsed_s"] for r in results),
            "response_hashes":[hashlib.sha256(source(r["text"]).encode()).hexdigest() for r in results]}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--base-url",default="http://127.0.0.1:11434"); p.add_argument("--model",default="qwen2.5-coder:1.5b"); p.add_argument("--repeats",type=int,default=3); p.add_argument("--output",required=True); a=p.parse_args()
    rows=[]
    for i in range(a.repeats):
        for parallel in ([False,True] if i%2==0 else [True,False]):
            rows.append({"repeat":i,"condition":"parallel_2" if parallel else "sequential_1",**condition(a.base_url,a.model,parallel)})
    summary={}
    for name in ("sequential_1","parallel_2"):
        xs=[x for x in rows if x["condition"]==name]
        summary[name]={"success_rate":sum(x["passed"]==2 for x in xs)/len(xs),"mean_wall_s":sum(x["wall_s"] for x in xs)/len(xs),"mean_tokens":sum(x["tokens"] for x in xs)/len(xs)}
    out={"schema":"m6-mesh-001.v1","model":a.model,"rows":rows,"summary":summary,
         "parallel_speedup":summary["sequential_1"]["mean_wall_s"]/summary["parallel_2"]["mean_wall_s"],
         "scope":"Two independent real-model obligations on one Ollama host; not A2A or general swarm qualification."}
    Path(a.output).parent.mkdir(parents=True,exist_ok=True); Path(a.output).write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))
if __name__=="__main__": main()
