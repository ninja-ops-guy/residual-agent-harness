from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path

from residual.station.models import save_settings
from residual.station.service import Station


INSTRUCTION = """Implement residual/improvement/spec.py as the first production M6.2 roadmap contract.

Requirements:
1. Define a frozen dataclass ImprovementSpec with exactly these fields:
   improvement_id: str
   observation: str
   hypothesis: str
   target_metrics: tuple[str, ...]
   preserve_metrics: tuple[str, ...]
   protected_invariants: tuple[str, ...]
   acceptance: dict[str, object]
   human_approval_required: bool = True
2. __post_init__ must raise ValueError for blank/whitespace-only improvement_id, observation, or hypothesis; empty target_metrics, preserve_metrics, protected_invariants, or acceptance; any blank/whitespace-only item in the tuple fields; or human_approval_required=False.
3. to_dict() must return a JSON-serializable dictionary, serialize tuple fields as lists, and copy acceptance so callers cannot mutate internal state through the returned object.
4. canonical_json() must return deterministic compact UTF-8-safe JSON with sorted keys.
5. sha256() must return the lowercase SHA-256 hex digest of canonical_json() encoded as UTF-8.
6. Importing the module must have no side effects. Use only Python standard library and/or stable RESIDUAL core utilities already provided in context. Do not add network, filesystem, subprocess, Git, provider, verifier, integration, receipt, or promotion behavior.
7. Keep the implementation small and readable. Do not modify any other file.
"""

CHECK = r"""import hashlib,json
from dataclasses import FrozenInstanceError
from residual.improvement.spec import ImprovementSpec

kw=dict(
 improvement_id='RI-ROADMAP-001',
 observation='repair attempts consume measurable resources',
 hypothesis='bounded repair context can reduce repeated implementation failures',
 target_metrics=('task_success_rate','repair_attempts'),
 preserve_metrics=('verification_integrity',),
 protected_invariants=('M4','evidence_integrity','promotion_authority'),
 acceptance={'success_rate_min':0.9,'max_regression':0.0},
)
s=ImprovementSpec(**kw)
d=s.to_dict()
assert d['target_metrics']==['task_success_rate','repair_attempts']
assert d['preserve_metrics']==['verification_integrity']
assert d['protected_invariants']==['M4','evidence_integrity','promotion_authority']
assert d['human_approval_required'] is True
d['acceptance']['success_rate_min']=0
assert s.to_dict()['acceptance']['success_rate_min']==0.9
c=s.canonical_json()
assert c==json.dumps(s.to_dict(),sort_keys=True,separators=(',',':'),ensure_ascii=False)
assert s.sha256()==hashlib.sha256(c.encode('utf-8')).hexdigest()
assert s.sha256()==ImprovementSpec(**kw).sha256()
try:
 s.improvement_id='changed'
except FrozenInstanceError:
 pass
else:
 raise AssertionError('ImprovementSpec is not frozen')

bad=[
 dict(kw, improvement_id=' '),
 dict(kw, observation='\t'),
 dict(kw, hypothesis=''),
 dict(kw, target_metrics=()),
 dict(kw, preserve_metrics=()),
 dict(kw, protected_invariants=()),
 dict(kw, target_metrics=('ok',' ')),
 dict(kw, preserve_metrics=(' ',)),
 dict(kw, protected_invariants=('M4','')),
 dict(kw, acceptance={}),
 dict(kw, human_approval_required=False),
]
for case in bad:
 try:
  ImprovementSpec(**case)
 except ValueError:
  pass
 else:
  raise AssertionError('invalid ImprovementSpec accepted: '+repr(case))
"""


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--model", default="qwen2.5-coder:7b")
    p.add_argument("--base-url", default="http://127.0.0.1:11438")
    p.add_argument("--output", default="runs/m6-roadmap-ship-003/improvementspec-evidence.json")
    a=p.parse_args()
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    repo_root=Path(__file__).resolve().parents[1]

    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp)
        clean_source=tmp/"source"
        subprocess.run(["git","clone","--no-hardlinks",str(repo_root),str(clean_source)],check=True,capture_output=True)
        source_head=subprocess.check_output(["git","-C",str(clean_source),"rev-parse","HEAD"],text=True).strip()

        station=Station(tmp/"station")
        save_settings(station.store,{
            "local":{"kind":"ollama","model":a.model,"base_url":a.base_url,"output_token_field":"max_tokens"},
            "review_placement":"local",
            "workers":1,
            "max_output_tokens":1600,
            "batch_max_passes":5,
            "batch_token_budget":30000,
            "batch_wall_clock_s":1800,
        })

        manifest={
            "schema_version":1,
            "name":"M6 Roadmap Ship — ImprovementSpec",
            "goal":"Ship the first production M6.2 contract using RESIDUAL's bounded development path.",
            "tasks":[{
                "id":"M6-ROADMAP-001",
                "title":"Implement production ImprovementSpec",
                "instruction":INSTRUCTION,
                "files":["residual/improvement/spec.py"],
                "context":["residual/core.py","residual/goalspec.py","scripts/m6_ship_improvementspec_check.py"],
                "depends_on":[],
                "route":"local",
                "checks":[
                    {"kind":"python_compile","path":"residual/improvement/spec.py"},
                    {"kind":"command","argv":["{python}","scripts/m6_ship_improvementspec_check.py"],"timeout":30},
                ],
            }],
        }
        mission="# M6 roadmap shipping experiment\n\n"+INSTRUCTION+"\n\n```json\n"+json.dumps(manifest,indent=2)+"\n```\n"
        pid=station.create(mission,source=str(clean_source),commands=True)["project_id"]
        result=station.batch(pid)
        project=station.store.project(pid)
        task=project["tasks"][0]
        metrics=station.metrics(pid)
        events=station.store.events(pid,0,5000)

        source=None; release_files=[]; export_error=None
        if task["state"]=="integrated":
            try:
                art=station.export(pid); _,raw=station.store.artifact(art["id"])
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    release_files=sorted(z.namelist())
                    if "residual/improvement/spec.py" in release_files:
                        source=z.read("residual/improvement/spec.py").decode("utf-8")
            except Exception as exc:
                export_error=f"{type(exc).__name__}: {exc}"

        artifacts=[]
        for ref in task.get("artifacts",[]):
            try:
                meta,raw=station.store.artifact(ref["id"])
                text=raw.decode("utf-8",errors="replace")
                artifacts.append({
                    "id":ref["id"],"name":meta["name"],"kind":meta["kind"],
                    "sha256":ref["sha256"],"size":meta["size"],
                    "content":text[:200000],"content_truncated":len(text)>200000,
                })
            except Exception as exc:
                artifacts.append({"id":ref.get("id"),"artifact_error":f"{type(exc).__name__}: {exc}"})

        evidence={
            "schema_version":1,
            "experiment":"M6-SHIP-003",
            "roadmap_issue":222,
            "roadmap_task":"ImprovementSpec first-class contract",
            "source_head":source_head,
            "provider":{"kind":"ollama","model":a.model,"base_url":a.base_url},
            "instruction_sha256":hashlib.sha256(INSTRUCTION.encode()).hexdigest(),
            "batch":result,
            "metrics":metrics,
            "task":{
                "id":task["id"],"attempt":task["attempt"],"state":task["state"],
                "findings":task["findings"],"checks_result":task["checks_result"],
                "review":task.get("review"),"head_commit":task.get("head_commit"),
                "verification_receipt":task.get("verification_receipt"),
            },
            "attempt_artifacts":artifacts,
            "release_files":release_files,
            "generated_source":source,
            "generated_source_sha256":hashlib.sha256(source.encode()).hexdigest() if source else None,
            "export_error":export_error,
            "events":[{
                "seq":e["seq"],"type":e["event_type"],"task_id":e["task_id"],
                "actor":e["actor"],"data":e["data"]
            } for e in events if e["event_type"] in {
                "task.transition","task.finding","usage.recorded","checks.completed",
                "review.completed","integration.completed","release.exported","project.note"
            }],
        }
        out.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print("M6_SHIP_EVIDENCE="+json.dumps(evidence,sort_keys=True,separators=(",",":")))
        ok=(
            result["integrated"]==1 and task["state"]=="integrated"
            and all(x.get("passed") is True for x in task["checks_result"])
            and task.get("review",{}).get("approved") is True
            and bool(task.get("verification_receipt"))
            and source is not None and export_error is None
        )
        return 0 if ok else 1


if __name__=="__main__":
    raise SystemExit(main())
