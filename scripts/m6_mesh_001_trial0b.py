from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, statistics, time, urllib.request
from pathlib import Path

BASE_TASKS=[
 {"id":"A","prompt":"Return ONLY Python source for function clamp(value, low, high): raise ValueError if low > high; otherwise clamp value.","file":"a.py"},
 {"id":"B","prompt":"Return ONLY Python source for function safe_mean(values): raise ValueError on empty input; otherwise return arithmetic mean.","file":"b.py"}
]

def request(base,model,prompt):
    body=json.dumps({"model":model,"prompt":prompt,"stream":False,"options":{"temperature":0}}).encode()
    start=time.perf_counter()
    req=urllib.request.Request(base+"/api/generate",data=body,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=300) as r: out=json.load(r)
    return {"text":out["response"],"elapsed_s":time.perf_counter()-start,
            "prompt_tokens":out.get("prompt_eval_count",0),"completion_tokens":out.get("eval_count",0)}

def clean(text):
    text=text.strip(); fence=chr(96)*3
    if text.startswith(fence):
        lines=text.splitlines()[1:]
        if lines and lines[-1].strip()==fence: lines=lines[:-1]
        text="\n".join(lines)
    return text.strip()+"\n"

def verify(task,text):
    ns={}
    try:
        exec(compile(clean(text),task["file"],"exec"),ns)
        if task["id"]=="A":
            f=ns["clamp"]
            if not (f(-1,0,2)==0 and f(3,0,2)==2 and f(1,0,2)==1): return False
            try: f(1,2,0); return False
            except ValueError: return True
        f=ns["safe_mean"]
        if f([2,4,6])!=4: return False
        try: f([]); return False
        except ValueError: return True
    except Exception:
        return False

def run_condition(base,model,rep,parallel):
    tasks=[dict(t,prompt=t["prompt"]+f"\nReplicate tag: {rep}. Do not include the tag in output.") for t in BASE_TASKS]
    start=time.perf_counter()
    if parallel:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futs=[pool.submit(request,base,model,t["prompt"]) for t in tasks]
            results=[f.result() for f in futs]
    else:
        results=[request(base,model,t["prompt"]) for t in tasks]
    wall=time.perf_counter()-start
    checks=[verify(t,r["text"]) for t,r in zip(tasks,results)]
    return {"condition":"parallel_2" if parallel else "sequential_1","wall_s":wall,
            "passed":sum(checks),"checks":checks,
            "tokens":sum(r["prompt_tokens"]+r["completion_tokens"] for r in results),
            "worker_elapsed_s":sum(r["elapsed_s"] for r in results),
            "overlap_factor":sum(r["elapsed_s"] for r in results)/wall if wall else None,
            "response_hashes":[hashlib.sha256(clean(r["text"]).encode()).hexdigest() for r in results]}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--base-url",default="http://127.0.0.1:11434"); p.add_argument("--model",default="qwen2.5-coder:1.5b"); p.add_argument("--repeats",type=int,default=8); p.add_argument("--output",required=True); a=p.parse_args()
    warm=request(a.base_url,a.model,"Reply with exactly WARM.")
    pairs=[]
    for rep in range(a.repeats):
        order=[False,True] if rep%2==0 else [True,False]
        rows=[run_condition(a.base_url,a.model,rep,x) for x in order]
        seq=next(x for x in rows if x["condition"]=="sequential_1"); par=next(x for x in rows if x["condition"]=="parallel_2")
        verified=(seq["passed"]==2 and par["passed"]==2)
        pairs.append({"repeat":rep,"order":[x["condition"] for x in rows],"verified_pair":verified,
                      "paired_speedup":seq["wall_s"]/par["wall_s"] if verified else None,"rows":rows})
    valid=[x for x in pairs if x["verified_pair"]]
    ratios=[x["paired_speedup"] for x in valid]
    flat=[r for p in pairs for r in p["rows"]]
    def stats(name):
        xs=[x for x in flat if x["condition"]==name]
        return {"runs":len(xs),"verified_missions":sum(x["passed"]==2 for x in xs),
                "mean_wall_s":statistics.mean(x["wall_s"] for x in xs),
                "median_wall_s":statistics.median(x["wall_s"] for x in xs),
                "mean_tokens":statistics.mean(x["tokens"] for x in xs),
                "mean_overlap_factor":statistics.mean(x["overlap_factor"] for x in xs)}
    out={"schema":"m6-mesh-001.trial0b.v1","model":a.model,"warmup":{"elapsed_s":warm["elapsed_s"]},
         "pairs":pairs,"summary":{"sequential_1":stats("sequential_1"),"parallel_2":stats("parallel_2"),
         "verified_pairs":len(valid),"median_paired_speedup":statistics.median(ratios) if ratios else None,
         "mean_paired_speedup":statistics.mean(ratios) if ratios else None},
         "scope":"Warm-controlled two-obligation crossover on one Ollama host; not A2A or general mesh qualification."}
    Path(a.output).parent.mkdir(parents=True,exist_ok=True); Path(a.output).write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))
if __name__=="__main__": main()
