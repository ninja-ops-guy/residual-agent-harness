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

BASELINE = "260b5f9e20bf70a6b9ca087bc91e22a009ed77b9"

CONTRACT = r"""Productionize the M6 ImprovementSpec content-identity contract in RESIDUAL.

Create exactly:
- residual/improvement/__init__.py
- residual/improvement/spec.py

Requirements:
1. Define @dataclass(frozen=True) ImprovementSpec with these public fields:
   improvement_id: str
   observation: str
   hypothesis: str
   target_metrics: tuple[str, ...]
   preserve_metrics: tuple[str, ...]
   protected_invariants: tuple[str, ...]
   acceptance: mapping/dict of string keys to strict JSON-compatible values
   human_approval_required: bool = True
2. Reject blank/whitespace-only improvement_id, observation, hypothesis.
3. Reject empty target_metrics, preserve_metrics, protected_invariants and blank/whitespace-only entries.
4. Reject empty acceptance and human_approval_required=False.
5. acceptance is part of the content identity and MUST become deeply immutable inside the object:
   - mutating the caller's original acceptance object after construction MUST NOT change the ImprovementSpec;
   - direct mutation through spec.acceptance, including nested mappings/sequences, MUST fail rather than alter identity.
6. acceptance MUST contain only strict JSON-compatible data with string object keys and finite numeric values. Reject unsupported objects and NaN/Infinity.
7. to_dict() returns a fully detached, JSON-serializable mutable representation. Mutating any nested object returned by to_dict() MUST NOT mutate the ImprovementSpec.
8. Tuple metric/invariant fields serialize as JSON arrays/lists.
9. canonical_json() returns deterministic compact strict JSON with sorted keys, separators=(',', ':'), ensure_ascii=False and no NaN/Infinity.
10. sha256() returns lowercase SHA-256 of canonical_json().encode('utf-8') and MUST remain stable after attempted caller/output mutations.
11. Use only Python standard library. Keep the module side-effect free.
12. residual/improvement/__init__.py exports ImprovementSpec and __all__ = ["ImprovementSpec"].

Do not add unrelated files or modify protected RESIDUAL authority/evaluation code.
"""

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--model", default="qwen2.5-coder:7b")
    p.add_argument("--base-url", default="http://127.0.0.1:11441")
    p.add_argument("--output", default="runs/m6-roadmap-001d/evidence.json")
    p.add_argument("--check-script", required=True)
    a=p.parse_args()
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    source=Path(a.source).resolve()
    source_head=subprocess.check_output(["git","-C",str(source),"rev-parse","HEAD"],text=True).strip()

    manifest={"schema_version":1,"name":"M6 Roadmap 001D — Immutable ImprovementSpec","goal":"Ship a stable content-addressed ImprovementSpec into RESIDUAL using RESIDUAL itself.","tasks":[{
      "id":"M6-ROADMAP-001D","title":"Implement immutable ImprovementSpec","instruction":CONTRACT,
      "files":["residual/improvement/__init__.py","residual/improvement/spec.py"],"context":[],"depends_on":[],"route":"local",
      "checks":[
        {"kind":"python_compile","path":"residual/improvement/spec.py"},
        {"kind":"python_compile","path":"residual/improvement/__init__.py"},
        {"kind":"command","argv":["{python}",str(Path(a.check_script).resolve())],"timeout":30},
      ]}]}
    fence=chr(96)*3
    spec="# M6 roadmap immutable ImprovementSpec\n\n"+CONTRACT+"\n\n"+fence+"json\n"+json.dumps(manifest,indent=2)+"\n"+fence+"\n"

    with tempfile.TemporaryDirectory() as root:
        station=Station(root)
        save_settings(station.store,{"local":{"kind":"ollama","model":a.model,"base_url":a.base_url,"output_token_field":"max_tokens"},"review_placement":"local","workers":1,"max_output_tokens":2000,"batch_max_passes":5,"batch_token_budget":40000,"batch_wall_clock_s":1800})
        pid=station.create(spec,source=str(source),commands=True)["project_id"]
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
                meta,raw=station.store.artifact(ar["id"]); txt=raw.decode("utf-8",errors="replace")
                attempt_artifacts.append({"id":ar["id"],"name":meta["name"],"kind":meta["kind"],"sha256":ar["sha256"],"size":meta["size"],"content":txt[:200000],"content_truncated":len(txt)>200000})
            except Exception as exc: attempt_artifacts.append({"id":ar.get("id"),"artifact_error":f"{type(exc).__name__}: {exc}"})
        events=station.store.events(pid,0,4000)
        evidence={"schema_version":1,"experiment":"M6-ROADMAP-001D","baseline_sha":BASELINE,"source_head":source_head,"harness_head":"8801d5e0ba0f7c5aaee9346761cd1916a6254c53",
          "acceptance_fixture_sha256":hashlib.sha256(Path(a.check_script).read_bytes()).hexdigest(),"provider":{"kind":"ollama","model":a.model,"base_url":a.base_url},"contract_sha256":hashlib.sha256(CONTRACT.encode()).hexdigest(),"batch":result,"metrics":metrics,"task":{"state":task["state"],"attempt":task["attempt"],"findings":task["findings"],"checks_result":task["checks_result"],"review":task.get("review"),"head_commit":task.get("head_commit"),"verification_receipt":task.get("verification_receipt")},"release_files":release_files,"generated_files":generated,"generated_file_sha256":{k:hashlib.sha256(v.encode()).hexdigest() for k,v in generated.items()},"export_error":export_error,"attempt_artifacts":attempt_artifacts,"events":[{"seq":e["seq"],"type":e["event_type"],"task_id":e["task_id"],"actor":e["actor"],"data":e["data"]} for e in events if e["event_type"] in {"task.transition","task.finding","usage.recorded","checks.completed","review.completed","integration.completed","release.exported"}]}
        out.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
        print("M6_ROADMAP_001D_EVIDENCE="+json.dumps(evidence,sort_keys=True,separators=(",",":")))
        ok=(source_head==BASELINE and result["integrated"]==1 and task["state"]=="integrated" and all(x.get("passed") is True for x in task["checks_result"]) and task.get("review",{}).get("approved") is True and bool(task.get("verification_receipt")) and set(generated)==set(task["files"]) and export_error is None)
        return 0 if ok else 1

if __name__=="__main__":
    raise SystemExit(main())
