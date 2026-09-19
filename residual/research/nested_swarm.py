"""EXP-NESTED-SWARM-001: governed nested-agent-runtime evidence."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib, math
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Mapping
from residual.core import canonical

SCHEMA="residual.nested-swarm-experiment.v1"; TRIAL_SCHEMA="residual.nested-swarm-trial.v1"; REPORT_SCHEMA="residual.nested-swarm-report.v1"
EXPERIMENT_ID="EXP-NESTED-SWARM-001"; ARM_IDS=("A","B","C","D")
METRICS=("task_success","verifier_pass_rate","elapsed_ms","input_tokens","output_tokens","api_cost_usd","provider_calls","retries","evidence_requests","failed_tool_calls","human_interventions","integration_conflicts","duplicate_work_items","convergence_iterations","provenance_completeness")

def _sha(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def _hex64(v,label):
    if not isinstance(v,str) or len(v)!=64 or any(c not in "0123456789abcdef" for c in v): raise ValueError(f"{label} must be a lowercase sha256")
    return v
def _finite(v,label):
    if type(v) not in (int,float) or not math.isfinite(v) or v<0: raise ValueError(f"{label} must be finite and non-negative")
    return float(v)

def task_corpus_hash(tasks:Mapping[str,str])->str:
    """Canonical corpus identity over task IDs and their content hashes."""
    if not isinstance(tasks,Mapping) or not tasks: raise ValueError("task corpus must be a non-empty mapping")
    rows=[]
    for task_id,task_sha in sorted(tasks.items()):
        if not isinstance(task_id,str) or not task_id: raise ValueError("task id is required")
        _hex64(task_sha,f"task {task_id}")
        rows.append({"task_id":task_id,"task_sha256":task_sha})
    return _sha(rows)

def _snapshot_contains_credentials(value)->bool:
    forbidden={"api_key","apikey","access_token","refresh_token","bearer_token","token","secret","client_secret","password","authorization","headers"}
    if isinstance(value,Mapping):
        for key,item in value.items():
            normalized=str(key).strip().lower().replace("-","_")
            if normalized in forbidden or _snapshot_contains_credentials(item): return True
        return False
    if isinstance(value,(list,tuple)):
        return any(_snapshot_contains_credentials(item) for item in value)
    return False

@dataclass(frozen=True)
class ExperimentArm:
    id:str; label:str; runtime:str; governance:str; nested:bool; provider_kinds:tuple[str,...]
    def __post_init__(self):
        if self.id not in ARM_IDS or not self.label or not self.runtime or not self.governance or type(self.nested) is not bool or not self.provider_kinds: raise ValueError("invalid experiment arm")

DEFAULT_ARMS=(
 ExperimentArm("A","RESIDUAL native","residual","residual",False,("configured",)),
 ExperimentArm("B","Moonshot / Kimi direct","moonshot","provider_native",False,("moonshot",)),
 ExperimentArm("C","Kimi Claw / OpenClaw","openclaw","provider_native",False,("kimi_claw",)),
 ExperimentArm("D","RESIDUAL heterogeneous nested","residual","residual",True,("moonshot","kimi_claw")),
)

@dataclass(frozen=True)
class ExperimentManifest:
    experiment_id:str; registered_at:str; task_corpus_sha256:str; runtime_revision:str; trials_per_arm:int
    arms:tuple[ExperimentArm,...]; hypotheses:tuple[str,...]; primary_metric:str; secondary_metrics:tuple[str,...]
    maximum_provider_calls:int; maximum_budget_usd:float; notes:str=""; schema_version:str=SCHEMA
    def __post_init__(self):
        if self.schema_version!=SCHEMA or self.experiment_id!=EXPERIMENT_ID: raise ValueError("invalid experiment identity")
        _hex64(self.task_corpus_sha256,"task corpus")
        if not self.registered_at or not self.runtime_revision or type(self.trials_per_arm) is not int or self.trials_per_arm<1: raise ValueError("invalid manifest metadata")
        if tuple(a.id for a in self.arms)!=ARM_IDS: raise ValueError("all four arms are required")
        if not self.hypotheses or self.primary_metric not in METRICS or any(m not in METRICS for m in self.secondary_metrics) or self.primary_metric in self.secondary_metrics: raise ValueError("invalid hypotheses or metrics")
        if type(self.maximum_provider_calls) is not int or self.maximum_provider_calls<1: raise ValueError("invalid provider-call limit")
        _finite(self.maximum_budget_usd,"maximum_budget_usd")
    def payload(self):
        return {"schema_version":self.schema_version,"experiment_id":self.experiment_id,"registered_at":self.registered_at,"task_corpus_sha256":self.task_corpus_sha256,"runtime_revision":self.runtime_revision,"trials_per_arm":self.trials_per_arm,"arms":[asdict(a)|{"provider_kinds":list(a.provider_kinds)} for a in self.arms],"hypotheses":list(self.hypotheses),"primary_metric":self.primary_metric,"secondary_metrics":list(self.secondary_metrics),"maximum_provider_calls":self.maximum_provider_calls,"maximum_budget_usd":self.maximum_budget_usd,"notes":self.notes}
    @property
    def sha256(self): return _sha(self.payload())

def build_manifest(*,registered_at,task_corpus_sha256,runtime_revision,trials_per_arm=3,maximum_provider_calls=1000,maximum_budget_usd=100.0,notes=""):
    return ExperimentManifest(EXPERIMENT_ID,registered_at,task_corpus_sha256,runtime_revision,trials_per_arm,DEFAULT_ARMS,(
      "RESIDUAL governance changes reliability and provenance outcomes relative to provider-native execution.",
      "A heterogeneous nested runtime can improve useful task performance without reducing verifier or provenance quality.",
      "Nested coordination introduces measurable overhead that can be separated from model inference cost.",
    ),"task_success",("verifier_pass_rate","elapsed_ms","input_tokens","output_tokens","api_cost_usd","human_interventions","integration_conflicts","convergence_iterations","provenance_completeness"),maximum_provider_calls,maximum_budget_usd,notes)

@dataclass(frozen=True)
class TrialRecord:
    manifest_sha256:str; arm_id:str; trial_index:int; task_id:str; task_sha256:str; runtime_revision:str
    provider_snapshot:Mapping[str,Any]; worker_contract_sha256:str; trace_root:str; metrics:Mapping[str,Any]
    outcome:str; failure_code:str|None=None; schema_version:str=TRIAL_SCHEMA
    def __post_init__(self):
        if self.schema_version!=TRIAL_SCHEMA or self.arm_id not in ARM_IDS: raise ValueError("invalid trial identity")
        for v,l in ((self.manifest_sha256,"manifest"),(self.task_sha256,"task"),(self.worker_contract_sha256,"worker contract"),(self.trace_root,"trace root")): _hex64(v,l)
        if type(self.trial_index) is not int or self.trial_index<1 or not self.task_id or not self.runtime_revision or self.outcome not in {"pass","fail","inconclusive"}: raise ValueError("invalid trial metadata")
        if set(self.metrics)!=set(METRICS): raise ValueError("trial must contain complete frozen metrics")
        for k in METRICS:
            v=self.metrics[k]
            if k=="task_success":
                if type(v) is not bool: raise ValueError("task_success must be boolean")
            elif k in {"provider_calls","retries","evidence_requests","failed_tool_calls","human_interventions","integration_conflicts","duplicate_work_items","convergence_iterations","input_tokens","output_tokens"}:
                if type(v) is not int or v<0: raise ValueError(f"{k} must be a non-negative integer")
            elif k in {"verifier_pass_rate","provenance_completeness"}:
                if not 0<=_finite(v,k)<=1: raise ValueError(f"{k} must be in [0,1]")
            else: _finite(v,k)
        if (self.outcome=="pass") != (self.metrics["task_success"] is True):
            raise ValueError("trial outcome must agree with measured task_success")
        if _snapshot_contains_credentials(self.provider_snapshot):
            raise ValueError("provider snapshot contains credentials")
    def payload(self):
        return {"schema_version":self.schema_version,"manifest_sha256":self.manifest_sha256,"arm_id":self.arm_id,"trial_index":self.trial_index,"task_id":self.task_id,"task_sha256":self.task_sha256,"runtime_revision":self.runtime_revision,"provider_snapshot":dict(self.provider_snapshot),"worker_contract_sha256":self.worker_contract_sha256,"trace_root":self.trace_root,"metrics":dict(self.metrics),"outcome":self.outcome,"failure_code":self.failure_code}
    @property
    def sha256(self): return _sha(self.payload())

def record_trial(path,trial,*,output_root):
    """Persist evidence only beneath an explicit caller-owned output root."""
    root=Path(output_root).resolve()
    target=Path(path).resolve()
    if target == root or not target.is_relative_to(root):
        raise ValueError("trial output must remain below output_root")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(canonical(trial.payload()|{"sha256":trial.sha256})+"\n",encoding="utf-8")

def verify_trial(trial,manifest):
    if trial.manifest_sha256!=manifest.sha256: raise ValueError("trial does not bind frozen manifest")
    if trial.runtime_revision!=manifest.runtime_revision: raise ValueError("runtime revision drift")
    if trial.trial_index>manifest.trials_per_arm: raise ValueError("trial exceeds preregistered repeat count")

def _stats(v): return {"n":len(v),"mean":mean(v),"median":median(v),"sample_stddev":stdev(v) if len(v)>1 else 0.0,"min":min(v),"max":max(v)}

def summarize_experiment(manifest,trials):
    if not trials: raise ValueError("no trials")
    for t in trials: verify_trial(t,manifest)
    hashes=[t.sha256 for t in trials]
    if len(hashes)!=len(set(hashes)): raise ValueError("duplicate trial evidence")

    tasks={}
    for t in trials:
        prior=tasks.setdefault(t.task_id,t.task_sha256)
        if prior!=t.task_sha256: raise ValueError("task id maps to multiple task hashes")
    if task_corpus_hash(tasks)!=manifest.task_corpus_sha256:
        raise ValueError("observed tasks do not match preregistered task corpus")

    seen=[(t.task_id,t.arm_id,t.trial_index) for t in trials]
    if len(seen)!=len(set(seen)): raise ValueError("duplicate task/arm/repeat cell")
    expected={(task_id,a.id,i) for task_id in tasks for a in manifest.arms for i in range(1,manifest.trials_per_arm+1)}
    if set(seen)!=expected: raise ValueError("experiment is incomplete")
    if sum(t.metrics["provider_calls"] for t in trials)>manifest.maximum_provider_calls: raise ValueError("provider-call stopping rule exceeded")
    if sum(float(t.metrics["api_cost_usd"]) for t in trials)>manifest.maximum_budget_usd+1e-12: raise ValueError("budget stopping rule exceeded")
    arms={}
    for a in manifest.arms:
        rows=[t for t in trials if t.arm_id==a.id]
        arms[a.id]={"label":a.label,"trials":len(rows),"outcomes":{k:sum(t.outcome==k for t in rows) for k in ("pass","fail","inconclusive")},"metrics":{m:_stats([float(t.metrics[m]) for t in rows]) for m in METRICS},"trial_sha256":[t.sha256 for t in rows]}
    payload={"schema_version":REPORT_SCHEMA,"experiment_id":manifest.experiment_id,"manifest_sha256":manifest.sha256,"task_corpus_sha256":manifest.task_corpus_sha256,"runtime_revision":manifest.runtime_revision,"arms":arms,"claim_boundary":"Descriptive evidence only. Cross-arm causal or superiority claims require the preregistered corpus, matched controls, completed repeats, and separate statistical analysis."}
    return payload|{"sha256":_sha(payload)}
