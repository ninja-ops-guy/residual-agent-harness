from __future__ import annotations

import argparse
import hashlib
import io
import json
import tempfile
import zipfile
from pathlib import Path

from residual.station.models import save_settings
from residual.station.service import Station

SPEC = r"""# M6.0 experiment — ImprovementSpec contract

Implement one new RESIDUAL module: `residual/improvement/spec.py`.

The model receives this behavioral contract only. It must create the implementation without changing RESIDUAL's evaluator, M4, verifier, evidence schemas, or promotion controls.

Requirements:
1. Define an immutable/frozen `ImprovementSpec` dataclass with exactly these fields:
   - improvement_id: str
   - observation: str
   - hypothesis: str
   - target_metrics: tuple[str, ...]
   - preserve_metrics: tuple[str, ...]
   - protected_invariants: tuple[str, ...]
   - acceptance: dict[str, object]
   - human_approval_required: bool = True
2. `__post_init__` MUST reject:
   - blank improvement_id, observation, or hypothesis;
   - empty target_metrics, preserve_metrics, or protected_invariants;
   - any blank metric/invariant entry;
   - empty acceptance;
   - human_approval_required=False.
   Rejection MUST raise ValueError.
3. Provide `to_dict()` returning a JSON-serializable dictionary. Tuple fields MUST serialize as lists. The acceptance mapping MUST be copied so callers cannot mutate internal state through the returned dictionary.
4. Provide `canonical_json()` returning deterministic compact JSON with sorted keys.
5. Provide `sha256()` returning the lowercase SHA-256 hex digest of UTF-8 canonical_json().
6. No network, subprocess, filesystem, model/provider, Git, verifier, M4, receipt, or promotion operations are allowed in this module.
7. Keep the implementation small and dependency-free beyond the Python standard library.

The experiment is successful only if RESIDUAL itself generates a candidate, executes the behavioral checks, obtains model review approval, integrates the candidate into its isolated mission repository, emits a verification receipt, and exports the generated source.
"""

CHECK = r"""import hashlib,json
from residual.improvement.spec import ImprovementSpec

kw=dict(
 improvement_id='RI-0001',
 observation='retry cost is high',
 hypothesis='bounded retry reduces cost',
 target_metrics=('token_cost',),
 preserve_metrics=('task_success',),
 protected_invariants=('M4', 'evidence_integrity'),
 acceptance={'token_reduction_pct': 10, 'max_success_regression_pct': 1},
)
s=ImprovementSpec(**kw)
d=s.to_dict()
assert d['target_metrics']==['token_cost']
assert d['preserve_metrics']==['task_success']
assert d['protected_invariants']==['M4','evidence_integrity']
assert d['human_approval_required'] is True
d['acceptance']['token_reduction_pct']=999
assert s.to_dict()['acceptance']['token_reduction_pct']==10
c=s.canonical_json()
assert c==json.dumps(s.to_dict(),sort_keys=True,separators=(',',':'),ensure_ascii=False)
assert s.sha256()==hashlib.sha256(c.encode('utf-8')).hexdigest()
assert s.sha256()==ImprovementSpec(**kw).sha256()

bad=[
 dict(kw, improvement_id=' '),
 dict(kw, observation=''),
 dict(kw, hypothesis=''),
 dict(kw, target_metrics=()),
 dict(kw, preserve_metrics=()),
 dict(kw, protected_invariants=()),
 dict(kw, target_metrics=('ok',' ')),
 dict(kw, acceptance={}),
 dict(kw, human_approval_required=False),
]
for case in bad:
 try: ImprovementSpec(**case)
 except ValueError: pass
 else: raise AssertionError('invalid ImprovementSpec accepted: '+repr(case))
"""

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--model", default="qwen2.5-coder:7b")
    p.add_argument("--base-url", default="http://127.0.0.1:11434")
    p.add_argument("--output", default="runs/m6-improvementspec/evidence.json")
    a=p.parse_args()
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as root:
        station=Station(root)
        save_settings(station.store,{"local":{"kind":"ollama","model":a.model,"base_url":a.base_url,"output_token_field":"max_tokens"},"review_placement":"local","workers":1,"max_output_tokens":1600,"batch_max_passes":5,"batch_token_budget":30000,"batch_wall_clock_s":600})
        manifest={"schema_version":1,"name":"M6 ImprovementSpec Self-Host","goal":"Have RESIDUAL implement the first bounded recursive-improvement contract.","tasks":[{"id":"M6-SPEC-001","title":"Implement ImprovementSpec","instruction":SPEC,"files":["residual/improvement/spec.py"],"context":[],"depends_on":[],"route":"local","checks":[{"kind":"python_compile","path":"residual/improvement/spec.py"},{"kind":"command","argv":["{python}","-c",CHECK],"timeout":30}]}]}
        mission="# M6 ImprovementSpec self-host experiment\n\n"+SPEC+"\n\n```json\n"+json.dumps(manifest,indent=2)+"\n```\n"
        pid=station.create(mission,commands=True)["project_id"]
        result=station.batch(pid)
        project=station.store.project(pid); task=project["tasks"][0]; metrics=station.metrics(pid)
        source=None; release_files=[]; export_error=None
        if task["state"]=="integrated":
            try:
                art=station.export(pid); _,raw=station.store.artifact(art["id"])
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    release_files=sorted(z.namelist())
                    if "residual/improvement/spec.py" in release_files:
                        source=z.read("residual/improvement/spec.py").decode()
            except Exception as exc:
                export_error=f"{type(exc).__name__}: {exc}"
        events=station.store.events(pid,0,2000)
        evidence={"schema_version":1,"experiment":"M6-SPEC-002","baseline_sha":"699e2869e294fe157b4bfd73a272057683a2f7e0","provider":{"kind":"ollama","model":a.model,"base_url":a.base_url},"spec_sha256":hashlib.sha256(SPEC.encode()).hexdigest(),"batch":result,"metrics":metrics,"task":{"state":task["state"],"attempt":task["attempt"],"findings":task["findings"],"checks_result":task["checks_result"],"review":task.get("review"),"head_commit":task.get("head_commit"),"verification_receipt":task.get("verification_receipt")},"release_files":release_files,"generated_source":source,"generated_source_sha256":hashlib.sha256(source.encode()).hexdigest() if source else None,"export_error":export_error,"events":[{"seq":e["seq"],"type":e["event_type"],"task_id":e["task_id"],"actor":e["actor"],"data":e["data"]} for e in events if e["event_type"] in {"task.transition","task.finding","usage.recorded","checks.completed","review.completed","integration.completed","release.exported"}]}
        out.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
        print("M6_EXPERIMENT_EVIDENCE="+json.dumps(evidence,sort_keys=True,separators=(",",":")))
        ok=result["integrated"]==1 and task["state"]=="integrated" and all(x.get("passed") is True for x in task["checks_result"]) and task.get("review",{}).get("approved") is True and bool(task.get("verification_receipt")) and source is not None and export_error is None
        return 0 if ok else 1

if __name__=="__main__":
    raise SystemExit(main())
