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

CONTRACT = r"""Productionize the M6 ImprovementSpec contract in RESIDUAL.

Create exactly:
- residual/improvement/__init__.py
- residual/improvement/spec.py

Requirements for residual/improvement/spec.py:
1. Define @dataclass(frozen=True) ImprovementSpec with exactly these fields:
   improvement_id: str
   observation: str
   hypothesis: str
   target_metrics: tuple[str, ...]
   preserve_metrics: tuple[str, ...]
   protected_invariants: tuple[str, ...]
   acceptance: dict[str, object]
   human_approval_required: bool = True
2. __post_init__ raises ValueError for blank/whitespace-only improvement_id, observation, hypothesis; empty target_metrics, preserve_metrics, protected_invariants; any blank/whitespace-only metric/invariant; empty acceptance; or human_approval_required=False.
3. to_dict() returns a JSON-serializable dict, converts tuple fields to lists, and copies acceptance.
4. canonical_json() returns deterministic compact JSON with sorted keys, separators=(',', ':'), ensure_ascii=False.
5. sha256() returns lowercase SHA-256 hex of canonical_json().encode('utf-8').
6. Use only Python standard library. No network, subprocess, filesystem, Git, model/provider, verifier, receipt, integration, or promotion operations.
7. Keep the module small and side-effect free: no module-level instances, prints, time-dependent values, or mutable global state.

Requirements for residual/improvement/__init__.py:
- export ImprovementSpec from .spec
- define __all__ = ["ImprovementSpec"]
"""

CHECK = r"""import hashlib,json
from residual.improvement import ImprovementSpec

kw=dict(
 improvement_id='RI-0001',
 observation='retry cost is high',
 hypothesis='bounded retry reduces cost',
 target_metrics=('token_cost',),
 preserve_metrics=('task_success',),
 protected_invariants=('M4','evidence_integrity'),
 acceptance={'token_reduction_pct':10,'max_success_regression_pct':1},
)
s=ImprovementSpec(**kw)
assert s.human_approval_required is True
assert s.to_dict()['target_metrics']==['token_cost']
assert s.to_dict()['preserve_metrics']==['task_success']
assert s.to_dict()['protected_invariants']==['M4','evidence_integrity']
d=s.to_dict(); d['acceptance']['token_reduction_pct']=999
assert s.to_dict()['acceptance']['token_reduction_pct']==10
c=s.canonical_json()
assert c==json.dumps(s.to_dict(),sort_keys=True,separators=(',',':'),ensure_ascii=False)
assert s.sha256()==hashlib.sha256(c.encode('utf-8')).hexdigest()
assert s.sha256()==ImprovementSpec(**kw).sha256()
bad=[
 dict(kw,improvement_id=' '),
 dict(kw,observation='\t'),
 dict(kw,hypothesis=''),
 dict(kw,target_metrics=()),
 dict(kw,preserve_metrics=()),
 dict(kw,protected_invariants=()),
 dict(kw,target_metrics=('ok',' ')),
 dict(kw,preserve_metrics=(' ',)),
 dict(kw,protected_invariants=('M4','\t')),
 dict(kw,acceptance={}),
 dict(kw,human_approval_required=False),
]
for case in bad:
 try: ImprovementSpec(**case)
 except ValueError: pass
 else: raise AssertionError('invalid ImprovementSpec accepted: '+repr(case))
"""

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--model", default="qwen2.5-coder:7b")
    p.add_argument("--base-url", default="http://127.0.0.1:11438")
    p.add_argument("--output", default="runs/m6-roadmap-001b/evidence.json")
    p.add_argument("--source", required=True)
    a=p.parse_args()
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    repo_root=Path(a.source).resolve()

    manifest={
      "schema_version":1,
      "name":"M6 Roadmap 001 — Production ImprovementSpec",
      "goal":"Ship the first M6.2 roadmap contract into the real RESIDUAL repository using RESIDUAL itself.",
      "tasks":[{
        "id":"M6-ROADMAP-001",
        "title":"Productionize ImprovementSpec",
        "instruction":CONTRACT,
        "files":["residual/improvement/__init__.py","residual/improvement/spec.py"],
        "context":[],
        "depends_on":[],
        "route":"local",
        "checks":[
          {"kind":"python_compile","path":"residual/improvement/spec.py"},
          {"kind":"python_compile","path":"residual/improvement/__init__.py"},
          {"kind":"command","argv":["{python}","-c",CHECK],"timeout":30},
        ],
      }]
    }
    fence=chr(96)*3
    spec="# M6 roadmap production task\n\n"+CONTRACT+"\n\n"+fence+"json\n"+json.dumps(manifest,indent=2)+"\n"+fence+"\n"

    with tempfile.TemporaryDirectory() as root:
        station=Station(root)
        save_settings(station.store,{
          "local":{"kind":"ollama","model":a.model,"base_url":a.base_url,"output_token_field":"max_tokens"},
          "review_placement":"local","workers":1,"max_output_tokens":1600,
          "batch_max_passes":5,"batch_token_budget":30000,"batch_wall_clock_s":1800,
        })
        pid=station.create(spec,source=str(repo_root),commands=True)["project_id"]
        result=station.batch(pid)
        project=station.store.project(pid); task=project["tasks"][0]; metrics=station.metrics(pid)
        generated={}; release_files=[]; export_error=None
        if task["state"]=="integrated":
            try:
                art=station.export(pid); _,raw=station.store.artifact(art["id"])
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    release_files=sorted(z.namelist())
                    for name in task["files"]:
                        if name in release_files: generated[name]=z.read(name).decode("utf-8")
            except Exception as exc:
                export_error=f"{type(exc).__name__}: {exc}"
        attempt_artifacts=[]
        for ar in task.get("artifacts",[]):
            try:
                meta,raw=station.store.artifact(ar["id"])
                text=raw.decode("utf-8",errors="replace")
                attempt_artifacts.append({"id":ar["id"],"name":meta["name"],"kind":meta["kind"],"sha256":ar["sha256"],"size":meta["size"],"content":text[:200000],"content_truncated":len(text)>200000})
            except Exception as exc:
                attempt_artifacts.append({"id":ar.get("id"),"artifact_error":f"{type(exc).__name__}: {exc}"})
        events=station.store.events(pid,0,4000)
        evidence={
          "schema_version":1,"experiment":"M6-ROADMAP-001B",
          "baseline_sha":"260b5f9e20bf70a6b9ca087bc91e22a009ed77b9",
          "source_head": __import__("subprocess").check_output(["git","-C",str(repo_root),"rev-parse","HEAD"],text=True).strip(),
          "provider":{"kind":"ollama","model":a.model,"base_url":a.base_url},
          "contract_sha256":hashlib.sha256(CONTRACT.encode()).hexdigest(),
          "batch":result,"metrics":metrics,
          "task":{"state":task["state"],"attempt":task["attempt"],"findings":task["findings"],"checks_result":task["checks_result"],"review":task.get("review"),"head_commit":task.get("head_commit"),"verification_receipt":task.get("verification_receipt")},
          "release_files":release_files,
          "generated_files":generated,
          "generated_file_sha256":{k:hashlib.sha256(v.encode()).hexdigest() for k,v in generated.items()},
          "export_error":export_error,
          "attempt_artifacts":attempt_artifacts,
          "events":[{"seq":e["seq"],"type":e["event_type"],"task_id":e["task_id"],"actor":e["actor"],"data":e["data"]} for e in events if e["event_type"] in {"task.transition","task.finding","usage.recorded","checks.completed","review.completed","integration.completed","release.exported"}],
        }
        out.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
        print("M6_ROADMAP_001_EVIDENCE="+json.dumps(evidence,sort_keys=True,separators=(",",":")))
        ok=(result["integrated"]==1 and task["state"]=="integrated" and all(x.get("passed") is True for x in task["checks_result"]) and task.get("review",{}).get("approved") is True and bool(task.get("verification_receipt")) and set(generated)==set(task["files"]) and export_error is None)
        return 0 if ok else 1

if __name__=="__main__":
    raise SystemExit(main())
