"""SPEC-EVAL-001: reproducible Factory evaluation and signed comparison reports."""
from __future__ import annotations

import hashlib, itertools, json, math, os, statistics, subprocess, tempfile, time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from residual.core import canonical, strict_json
from .evidence_bus import StationIdentity

EVAL_DOMAIN = b"residual.factory.comparison-report.v1\n"
EVAL_SCHEMA = "factory-evaluation-v1"
CONFIGS = ("single", "fixed", "dynamic")

class EvaluationError(ValueError): pass

def _sha(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def _git_id(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) not in {40,64} or any(c not in "0123456789abcdef" for c in value):
        raise EvaluationError(f"invalid {name}")
    return value

def _finite(value: Any, name: str, minimum=0.0) -> float:
    if type(value) not in (int,float) or not math.isfinite(value) or value < minimum:
        raise EvaluationError(f"invalid {name}")
    return float(value)

def _integer(value: Any, name: str, minimum=0) -> int:
    if type(value) is not int or value < minimum: raise EvaluationError(f"invalid {name}")
    return value

@dataclass(frozen=True, slots=True)
class FrozenEvalTask:
    task_id: str
    requirement_ids: tuple[str,...]
    depends_on: tuple[str,...]
    acceptance: tuple[str,...]
    def __post_init__(self):
        if not self.task_id or not self.requirement_ids or not self.acceptance: raise EvaluationError("invalid evaluation task")
        if len(set(self.requirement_ids)) != len(self.requirement_ids) or len(set(self.depends_on)) != len(self.depends_on): raise EvaluationError("duplicate task binding")
    def to_dict(self): return {"task_id":self.task_id,"requirement_ids":list(self.requirement_ids),"depends_on":list(self.depends_on),"acceptance":list(self.acceptance)}

@dataclass(frozen=True, slots=True)
class FrozenWorkload:
    workload_id: str
    requirements: tuple[str,...]
    tasks: tuple[FrozenEvalTask,...]
    input_commit: str
    expected_output_commit: str
    engine_name: str
    engine_version: str
    temperature: float
    seed: int|None
    driver_argv: tuple[str,...]=()
    schema_version: str=EVAL_SCHEMA
    def __post_init__(self):
        if self.schema_version != EVAL_SCHEMA or not self.workload_id or not self.requirements: raise EvaluationError("invalid workload")
        if len(set(self.requirements)) != len(self.requirements): raise EvaluationError("duplicate requirement")
        _git_id(self.input_commit,"input commit"); _git_id(self.expected_output_commit,"expected output commit")
        if not self.engine_name or not self.engine_version: raise EvaluationError("engine identity required")
        if _finite(self.temperature,"temperature") != 0: raise EvaluationError("frozen evaluation requires temperature=0")
        if self.seed is not None: _integer(self.seed,"seed")
        ids=[t.task_id for t in self.tasks]
        if not ids or len(ids)!=len(set(ids)): raise EvaluationError("unique tasks required")
        ts,rs=set(ids),set(self.requirements)
        for t in self.tasks:
            if set(t.requirement_ids)-rs or set(t.depends_on)-ts: raise EvaluationError("unknown workload binding")
        done=set()
        while len(done)<len(ts):
            ready={t.task_id for t in self.tasks if set(t.depends_on)<=done}
            if not ready-done: raise EvaluationError("workload dependency cycle")
            done|=ready
        if self.driver_argv and any(not isinstance(x,str) or not x for x in self.driver_argv): raise EvaluationError("invalid driver argv")
    def to_dict(self, include_driver=True):
        out={"schema_version":self.schema_version,"workload_id":self.workload_id,"requirements":list(self.requirements),"tasks":[t.to_dict() for t in sorted(self.tasks,key=lambda x:x.task_id)],"input_commit":self.input_commit,"expected_output_commit":self.expected_output_commit,"engine":{"name":self.engine_name,"version":self.engine_version,"temperature":self.temperature,"seed":self.seed}}
        if include_driver: out["driver_argv"]=list(self.driver_argv)
        return out
    @property
    def workload_hash(self): return _sha(self.to_dict(False))
    @classmethod
    def from_dict(cls,v):
        allowed={"schema_version","workload_id","requirements","tasks","input_commit","expected_output_commit","engine","driver_argv"}
        if not isinstance(v,dict) or set(v)-allowed: raise EvaluationError("invalid workload keys")
        e=v.get("engine") or {}
        tasks=tuple(FrozenEvalTask(str(t["task_id"]),tuple(t["requirement_ids"]),tuple(t.get("depends_on",())),tuple(t["acceptance"])) for t in v["tasks"])
        return cls(str(v["workload_id"]),tuple(v["requirements"]),tasks,v["input_commit"],v["expected_output_commit"],str(e["name"]),str(e["version"]),e.get("temperature",0),e.get("seed"),tuple(v.get("driver_argv",())),v.get("schema_version",EVAL_SCHEMA))

@dataclass(frozen=True, slots=True)
class RunMeasurement:
    config:str; run_index:int; elapsed_time_minutes:float; accepted_tasks:int; token_cost_total:int
    gpu_time_minutes:float; coordination_time_minutes:float; rework_tasks:int; merge_conflicts:int
    verifier_rejected:int; verifier_total:int; final_tests_passed:int; final_tests_total:int
    api_cost_usd:float; gpu_cost_usd:float; infrastructure_cost_usd:float
    engine_name:str; engine_version:str; output_commit:str; observation_digest:str; simulation:bool=False
    peak_workers:int=1
    def __post_init__(self):
        if self.config not in CONFIGS: raise EvaluationError("invalid config")
        _integer(self.run_index,"run index",1); elapsed=_finite(self.elapsed_time_minutes,"elapsed")
        if elapsed<=0: raise EvaluationError("elapsed must be positive")
        for n in ("accepted_tasks","token_cost_total","rework_tasks","merge_conflicts","verifier_rejected","verifier_total","final_tests_passed","final_tests_total"): _integer(getattr(self,n),n)
        _integer(self.peak_workers,"peak workers",1)
        for n in ("gpu_time_minutes","coordination_time_minutes","api_cost_usd","gpu_cost_usd","infrastructure_cost_usd"): _finite(getattr(self,n),n)
        if self.coordination_time_minutes>elapsed or self.verifier_rejected>self.verifier_total or self.final_tests_passed>self.final_tests_total: raise EvaluationError("invalid metric numerator")
        if self.config == "single" and self.peak_workers != 1: raise EvaluationError("single configuration must use one worker")
        _git_id(self.output_commit,"output commit")
        if not self.engine_name or not self.engine_version or len(self.observation_digest)!=64 or type(self.simulation) is not bool: raise EvaluationError("invalid provenance")
    def metrics(self):
        total=self.api_cost_usd+self.gpu_cost_usd+self.infrastructure_cost_usd
        return {"elapsed_time_minutes":self.elapsed_time_minutes,"accepted_tasks_per_hour":self.accepted_tasks/(self.elapsed_time_minutes/60),"token_cost_total":float(self.token_cost_total),"gpu_time_minutes":self.gpu_time_minutes,"coordination_overhead_pct":100*self.coordination_time_minutes/self.elapsed_time_minutes,"rework_rate_pct":100*self.rework_tasks/max(1,self.accepted_tasks+self.rework_tasks),"merge_conflicts":float(self.merge_conflicts),"verifier_rejection_rate_pct":100*self.verifier_rejected/max(1,self.verifier_total),"final_test_pass_rate_pct":100*self.final_tests_passed/max(1,self.final_tests_total),"api_cost_usd":self.api_cost_usd,"gpu_cost_usd":self.gpu_cost_usd,"infrastructure_cost_usd":self.infrastructure_cost_usd,"total_cost_usd":total,"cost_per_accepted_task_usd":total/max(1,self.accepted_tasks)}
    def to_dict(self): return {k:getattr(self,k) for k in self.__dataclass_fields__}
    @classmethod
    def from_dict(cls,v):
        data={k:v[k] for k in cls.__dataclass_fields__ if k in v}
        return cls(**data)

class EvaluationDriver(Protocol):
    def run(self,workload:FrozenWorkload,config:str,run_index:int,observe:Callable[[dict],None])->RunMeasurement:...

class CommandEvaluationDriver:
    """Runs explicit argv from the frozen workload; never invokes a shell."""
    def __init__(self,argv,workload_path):
        if not argv: raise EvaluationError("driver_argv required")
        self.argv=tuple(argv); self.workload_path=Path(workload_path)
    def run(self,workload,config,run_index,observe):
        with tempfile.TemporaryDirectory(prefix="residual-eval-") as td:
            out=Path(td)/"measurement.json"; repl={"{config}":config,"{run}":str(run_index),"{workload}":str(self.workload_path),"{output}":str(out)}
            argv=[repl.get(x,x) for x in self.argv]
            observe({"event":"EvaluationDriverStarted","config":config,"run_index":run_index,"argv_sha256":hashlib.sha256("\0".join(argv).encode()).hexdigest()})
            p=subprocess.run(argv,cwd=self.workload_path.parent,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=86400,env={"PATH":os.environ.get("PATH","")})
            if p.returncode or not out.exists(): raise EvaluationError("evaluation driver failed")
            m=RunMeasurement.from_dict(strict_json(out.read_text()))
            if m.config!=config or m.run_index!=run_index: raise EvaluationError("driver identity mismatch")
            return m

class EvaluationObservationLog:
    def __init__(self,path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self._root="0"*64
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                e=strict_json(line); body={k:v for k,v in e.items() if k!="event_hash"}
                if e.get("prev_hash")!=self._root or _sha(body)!=e.get("event_hash"): raise EvaluationError("observation chain invalid")
                self._root=e["event_hash"]
    @property
    def root(self): return self._root
    def emit(self,event):
        body={"schema_version":"factory-eval-observation-v1","prev_hash":self._root,"recorded_at_ns":time.time_ns(),**strict_json(canonical(event))}; row={**body,"event_hash":_sha(body)}
        with self.path.open("a",encoding="utf-8") as f: f.write(canonical(row)+"\n"); f.flush(); os.fsync(f.fileno())
        self._root=row["event_hash"]

def _summary(v): return {"mean":statistics.fmean(v),"median":statistics.median(v),"stddev":statistics.stdev(v) if len(v)>1 else 0.0}

def mann_whitney_u(a,b):
    if not a or not b: raise EvaluationError("empty statistical sample")
    vals=list(a)+list(b); order=sorted(range(len(vals)),key=lambda i:vals[i]); ranks=[0.0]*len(vals); i=0
    while i<len(order):
        j=i+1
        while j<len(order) and vals[order[j]]==vals[order[i]]: j+=1
        r=(i+1+j)/2
        for k in order[i:j]: ranks[k]=r
        i=j
    n1,n2=len(a),len(b); u1=sum(ranks[:n1])-n1*(n1+1)/2; u=min(u1,n1*n2-u1); n=n1+n2
    if n<=14:
        extreme=total=0
        for g in itertools.combinations(range(n),n1):
            uu1=sum(ranks[x] for x in g)-n1*(n1+1)/2; uu=min(uu1,n1*n2-uu1); total+=1; extreme+=uu<=u+1e-12
        p=extreme/total; method="mann-whitney-u-exact-permutation"
    else:
        mean=n1*n2/2; counts={}
        for v in vals: counts[v]=counts.get(v,0)+1
        tie=sum(c**3-c for c in counts.values()); var=n1*n2/12*((n+1)-tie/(n*(n-1))); z=0 if var<=0 else (abs(u1-mean)-.5)/math.sqrt(var); p=math.erfc(abs(z)/math.sqrt(2)); method="mann-whitney-u-normal-approx"
    return {"u":float(u),"p_value":float(max(0,min(1,p))),"method":method}

@dataclass(frozen=True, slots=True)
class ComparisonReport:
    workload_hash:str; run_count:int; configurations:dict[str,Any]; significance:dict[str,Any]; observation_root:str; simulation:bool; generated_at_ns:int; station_key_id:str; station_signature:str; schema_version:str="factory-comparison-report-v1"
    def unsigned_payload(self): return {"schema_version":self.schema_version,"workload_hash":self.workload_hash,"run_count":self.run_count,"configurations":self.configurations,"significance":self.significance,"observation_root":self.observation_root,"simulation":self.simulation,"generated_at_ns":self.generated_at_ns,"station_key_id":self.station_key_id}
    @property
    def report_hash(self): return _sha(self.unsigned_payload())
    def to_dict(self): return {**self.unsigned_payload(),"report_hash":self.report_hash,"station_signature":self.station_signature}
    def verify(self,key): return StationIdentity.verify_hash(self.report_hash,self.station_signature,key,key_id=self.station_key_id,domain=EVAL_DOMAIN)

class EvaluationFramework:
    def __init__(self,identity,log): self.identity,self.log=identity,log
    def evaluate(self,workload,configs,runs,driver):
        if runs<3: raise EvaluationError("minimum 3 runs required")
        if not configs or len(set(configs))!=len(configs) or any(c not in CONFIGS for c in configs): raise EvaluationError("invalid configs")
        rows={c:[] for c in configs}; self.log.emit({"event":"EvaluationStarted","workload_hash":workload.workload_hash,"configs":list(configs),"runs":runs})
        for c in configs:
            for i in range(1,runs+1):
                m=driver.run(workload,c,i,self.log.emit)
                if (m.engine_name,m.engine_version)!=(workload.engine_name,workload.engine_version): raise EvaluationError("engine identity drift")
                if not m.simulation and m.output_commit!=workload.expected_output_commit: raise EvaluationError("unexpected output commit")
                rows[c].append(m); self.log.emit({"event":"EvaluationRunRecorded","workload_hash":workload.workload_hash,"measurement":m.to_dict()})
        names=list(next(iter(rows.values()))[0].metrics()); base=rows.get("single"); summaries={}
        for c,rr in rows.items():
            metrics={n:_summary([x.metrics()[n] for x in rr]) for n in names}; speed=statistics.median(x.elapsed_time_minutes for x in base)/statistics.median(x.elapsed_time_minutes for x in rr) if base else None
            workers=statistics.median(x.peak_workers for x in rr)
            summaries[c]={"metrics":metrics,"speedup_vs_single":speed,"observed_peak_workers":_summary([float(x.peak_workers) for x in rr]),"parallel_efficiency":speed/workers if speed is not None else None,"simulation":any(x.simulation for x in rr)}
        significance={f"{a}_vs_{b}":{n:mann_whitney_u([x.metrics()[n] for x in rows[a]],[x.metrics()[n] for x in rows[b]]) for n in names} for a,b in itertools.combinations(configs,2)}
        sim=any(x.simulation for rr in rows.values() for x in rr); fields={"workload_hash":workload.workload_hash,"run_count":runs,"configurations":summaries,"significance":significance,"observation_root":self.log.root,"simulation":sim,"generated_at_ns":time.time_ns(),"station_key_id":self.identity.key_id}; unsigned={"schema_version":"factory-comparison-report-v1",**fields}; h=_sha(unsigned); sig=self.identity.sign_hash(h,domain=EVAL_DOMAIN); report=ComparisonReport(**fields,station_signature=sig)
        if report.report_hash!=h: raise EvaluationError("report canonicalization mismatch")
        self.log.emit({"event":"ComparisonReportIssued","report_hash":report.report_hash,"simulation":sim}); return report

def run_cli(argv):
    import argparse
    p=argparse.ArgumentParser(prog="residual evaluate"); p.add_argument("--workload",required=True); p.add_argument("--configs",required=True); p.add_argument("--runs",type=int,default=3); p.add_argument("--station-key",required=True); p.add_argument("--output",default="runs/factory-evaluation"); a=p.parse_args(argv)
    wp=Path(a.workload).resolve(); workload=FrozenWorkload.from_dict(strict_json(wp.read_text())); configs=tuple(x.strip() for x in a.configs.split(",") if x.strip()); identity=StationIdentity.load_private(Path(a.station_key).resolve()); out=Path(a.output).resolve(); out.mkdir(parents=True,exist_ok=True); log=EvaluationObservationLog(out/"observations.jsonl"); report=EvaluationFramework(identity,log).evaluate(workload,configs,a.runs,CommandEvaluationDriver(workload.driver_argv,wp)); (out/"comparison-report.json").write_text(json.dumps(report.to_dict(),indent=2,sort_keys=True)+"\n"); print(json.dumps({"status":"complete","report_hash":report.report_hash,"simulation":report.simulation,"output":str(out)},indent=2)); return 0
