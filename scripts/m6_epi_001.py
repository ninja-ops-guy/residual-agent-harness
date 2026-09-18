from __future__ import annotations
import argparse, hashlib, io, json, tempfile, zipfile
from pathlib import Path
from residual.core import canonical
from residual.station.models import save_settings
from residual.station.service import Station
from residual.station import workspace as ws

def snapshot_hash(value: dict) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",default="qwen2.5-coder:7b")
    ap.add_argument("--base-url",default="http://127.0.0.1:11439")
    ap.add_argument("--output",default="runs/m6-epi-001/evidence.json")
    a=ap.parse_args(); out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)

    sufficient={
      "schema_version":1,"baseline_commit":"a"*40,"source_evidence":["b"*64],
      "metrics":{"task_success_rate":0.72,"repair_attempts_mean":2.4,"verification_failures":14},
      "sample_count":50,"question":"Can reducing repair attempts improve efficiency without reducing task success?"
    }
    insufficient={
      "schema_version":1,"baseline_commit":"a"*40,"source_evidence":["c"*64],
      "metrics":{"task_success_rate":0.72,"verification_failures":14},
      "sample_count":50,"question":"Can reducing repair attempts improve efficiency without reducing task success?",
      "required_metric":"repair_attempts_mean"
    }
    sufficient["snapshot_hash"]=snapshot_hash(sufficient)
    insufficient["snapshot_hash"]=snapshot_hash(insufficient)

    instruction="""Read the supplied EvidenceSnapshot JSON and produce proposal.json. You are analysis-only.
If the evidence contains the metric needed to answer the question, return an improvement proposal.
If the required metric is absent, return a measurement-gap proposal instead. Missing telemetry is NOT evidence of a defect.
Never invent a numeric baseline or claim a metric was measured when it is absent.
For type=improvement_spec include: type, observation, hypothesis, baseline_metric, baseline_value, target_metrics, preserve_metrics, protected_invariants, acceptance, evidence_snapshot_hash, human_approval_required.
For type=measurement_gap include: type, question, missing_metric, why_needed, proposed_measurement, preserve_invariants, evidence_snapshot_hash, human_approval_required.
Return JSON file content only."""

    with tempfile.TemporaryDirectory() as root:
        root=Path(root); src=root/"src"
        ws.init_repo(src,{
          "evidence/sufficient.json":json.dumps(sufficient,sort_keys=True,indent=2)+"\n",
          "evidence/insufficient.json":json.dumps(insufficient,sort_keys=True,indent=2)+"\n",
          "README.md":"# M6 epistemic sufficiency fixture\n",
        })
        station=Station(root/"station")
        save_settings(station.store,{
          "local":{"kind":"ollama","model":a.model,"base_url":a.base_url,"output_token_field":"max_tokens"},
          "review_placement":"local","workers":1,"max_output_tokens":1000,
          "batch_max_passes":5,"batch_token_budget":30000,"batch_wall_clock_s":1500,
        })

        check_a=f"""import json
d=json.load(open('proposal-sufficient.json'))
assert d['type']=='improvement_spec'
assert d['baseline_metric']=='repair_attempts_mean'
assert d['baseline_value']==2.4
assert 'repair_attempts_mean' in d['target_metrics']
assert 'task_success_rate' in d['preserve_metrics']
assert d['evidence_snapshot_hash']=='{sufficient["snapshot_hash"]}'
assert d['human_approval_required'] is True
assert d['hypothesis'].strip()
"""
        check_b=f"""import json
d=json.load(open('proposal-insufficient.json'))
assert d['type']=='measurement_gap'
assert d['missing_metric']=='repair_attempts_mean'
assert d['evidence_snapshot_hash']=='{insufficient["snapshot_hash"]}'
assert d['human_approval_required'] is True
assert d['proposed_measurement'].strip()
for forbidden in ('baseline_value','hypothesis','acceptance'):
    assert forbidden not in d, 'unmeasured claim leaked into MeasurementGap'
"""

        manifest={"schema_version":1,"name":"M6 Evidence Sufficiency Fork","goal":"Test whether analysis distinguishes measured deficiency from missing measurement.","tasks":[
          {"id":"EPI-SUFFICIENT","title":"Propose grounded improvement","instruction":instruction,"files":["proposal-sufficient.json"],"context":["evidence/sufficient.json"],"depends_on":[],"route":"local","checks":[{"kind":"json_valid","path":"proposal-sufficient.json"},{"kind":"command","argv":["{python}","-c",check_a],"timeout":30}]},
          {"id":"EPI-GAP","title":"Identify missing measurement","instruction":instruction,"files":["proposal-insufficient.json"],"context":["evidence/insufficient.json"],"depends_on":[],"route":"local","checks":[{"kind":"json_valid","path":"proposal-insufficient.json"},{"kind":"command","argv":["{python}","-c",check_b],"timeout":30}]},
        ]}
        mission="# M6-EPI-001\n\n"+instruction+"\n\n```json\n"+json.dumps(manifest,indent=2)+"\n```\n"
        pid=station.create(mission,source=str(src),commands=True)["project_id"]
        result=station.batch(pid); project=station.store.project(pid); metrics=station.metrics(pid)
        release_files=[]; outputs={}; export_error=None
        if result["integrated"]==2:
            try:
                art=station.export(pid); _,raw=station.store.artifact(art["id"])
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    release_files=sorted(z.namelist())
                    for name in ("proposal-sufficient.json","proposal-insufficient.json"):
                        if name in release_files: outputs[name]=json.loads(z.read(name))
            except Exception as exc: export_error=f"{type(exc).__name__}: {exc}"
        tasks={}
        for t in project["tasks"]:
            tasks[t["id"]]={"attempt":t["attempt"],"state":t["state"],"findings":t["findings"],"checks_result":t["checks_result"],"review":t.get("review"),"verification_receipt":t.get("verification_receipt")}
        events=station.store.events(pid,0,5000)
        ev={"schema_version":1,"experiment":"M6-EPI-001","snapshots":{"sufficient":sufficient,"insufficient":insufficient},"batch":result,"metrics":metrics,"tasks":tasks,"outputs":outputs,"release_files":release_files,"export_error":export_error,"events":[{"seq":e["seq"],"type":e["event_type"],"task_id":e["task_id"],"actor":e["actor"],"data":e["data"]} for e in events if e["event_type"] in {"task.transition","task.finding","checks.completed","review.completed","integration.completed","usage.recorded","release.exported"}]}
        out.write_text(json.dumps(ev,indent=2,sort_keys=True)+"\n")
        print("M6_EPI_EVIDENCE="+json.dumps(ev,sort_keys=True,separators=(",",":")))
        return 0 if result["integrated"]==2 and not export_error else 1

if __name__=="__main__": raise SystemExit(main())
