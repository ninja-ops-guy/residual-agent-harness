"""Execution adapters for Portal Research Workbench experiments."""
from __future__ import annotations

import hashlib
import io
import json
import re
import tempfile
import platform
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from residual.core import ContractError, canonical
from residual.station.models import save_settings
from residual.station.service import Station
from residual import research

PILOT_DOCUMENT = {
    "schema_version": 1,
    "experiment_id": "M6-WB-001",
    "hypothesis": "the Research Workbench can execute a governed trial and retain complete evidence",
    "target_metrics": ["task_success", "evidence_integrity"],
    "preserve_metrics": ["M4", "human_authority"],
    "acceptance": {
        "all_checks_pass": True,
        "human_approval_required": True,
    },
    "authority": {
        "candidate_code_execution": False,
        "promotion_authority": "human",
    },
}

PILOT_SPEC = """Create exactly one UTF-8 JSON file at research/workbench_result.json.
The file is a declarative research artifact, not executable code. Do not create Python, shell,
JavaScript, configuration hooks, or any other executable content.

The JSON object must contain exactly the following semantic values:
- schema_version: 1
- experiment_id: M6-WB-001
- hypothesis: the Research Workbench can execute a governed trial and retain complete evidence
- target_metrics: ["task_success", "evidence_integrity"]
- preserve_metrics: ["M4", "human_authority"]
- acceptance.all_checks_pass: true
- acceptance.human_approval_required: true
- authority.candidate_code_execution: false
- authority.promotion_authority: "human"

Whitespace and JSON key order are irrelevant. Return the complete file content through the
normal RESIDUAL files transport. Do not claim the experiment passed; host-owned checks,
review, integration, receipts, and export determine the result."""


def _safe_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{2,80}", value):
        raise ContractError("Invalid experiment id")
    return value

def workbench_root(station):
    root = Path(station.store.root) / "research"
    root.mkdir(parents=True, exist_ok=True)
    return root

def prepare(station, experiment_id, *, refresh=True, require_runnable=False):
    experiment_id = _safe_id(experiment_id)
    if refresh:
        try:
            catalog, commit = research.sync()
        except (OSError, ValueError, RuntimeError, FileNotFoundError, json.JSONDecodeError):
            catalog, commit = research.current()
    else:
        catalog, commit = research.current()
    exp = research.get_experiment(experiment_id, catalog)
    if require_runnable:
        adapter=exp.get("adapter")
        if exp.get("status")!="runnable" or adapter not in ADAPTERS:
            raise ContractError("This experiment is installed but not runnable yet")
        preflight=PREFLIGHTS.get(adapter)
        if preflight: preflight(station)
    definition_sha=research._sha(research._json_bytes(exp))
    history_root=workbench_root(station)/experiment_id
    authoritative=[]
    for prior in history_root.glob("*/manifest.json") if history_root.exists() else ():
        try:
            prior_manifest=json.loads(prior.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError):
            continue
        status=prior_manifest.get("run_status")
        if status not in {"RUNNING","COMPLETED","FAILED"}:
            continue
        authoritative.append(prior_manifest)
        previous=prior_manifest.get("experiment_sha256")
        if previous and previous != definition_sha:
            raise ContractError("Experiment definition changed after a retained run; publish a new experiment id")
    trial_limit=exp.get("trials",1)
    if type(trial_limit) is not int or trial_limit < 1 or trial_limit > 1000:
        raise ContractError("Experiment trial count is invalid")
    if len(authoritative) >= trial_limit:
        raise ContractError("All preregistered authoritative trials for this experiment already exist")
    trial_index=len(authoritative)+1
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    out = workbench_root(station) / experiment_id / run_id
    _, manifest = research.import_experiment(experiment_id, output=out, do_sync=False)
    manifest["run_id"] = run_id
    manifest["adapter"] = exp.get("adapter")
    manifest["trial_index"] = trial_index
    manifest["trial_limit"] = trial_limit
    manifest["run_status"] = "PREPARED"
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"run_id": run_id, "experiment": exp, "catalog_commit": commit, "output": str(out)}

def _load_run(station, experiment_id, run_id):
    experiment_id = _safe_id(experiment_id)
    if not re.fullmatch(r"[0-9TZ-]{16,32}[a-f0-9]{8}", run_id or ""):
        raise ContractError("Invalid research run id")
    path = workbench_root(station) / experiment_id / run_id
    manifest_path = path / "manifest.json"
    if not manifest_path.is_file():
        raise ContractError("Research run not found")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return path, manifest

def list_runs(station):
    root = workbench_root(station)
    rows = []
    for manifest_path in root.glob("*/*/manifest.json"):
        try:
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            evidence_path = manifest_path.parent / "evidence.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.is_file() else None
            rows.append({"experiment_id": m["experiment_id"], "run_id": m.get("run_id", manifest_path.parent.name),
                         "status": m.get("run_status", m.get("status", "UNKNOWN")), "catalog_commit": m.get("catalog_commit"),
                         "created_at": m.get("created_at"), "trial_index": m.get("trial_index"), "trial_limit": m.get("trial_limit"), "outcome": evidence.get("outcome") if evidence else None})
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            continue
    return sorted(rows, key=lambda x: x.get("created_at") or "", reverse=True)[:100]

def _write_sums(root):
    rows=[]
    for p in sorted(x for x in root.rglob("*") if x.is_file() and x.name!="SHA256SUMS"):
        rows.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}")
    (root/"SHA256SUMS").write_text("\n".join(rows)+"\n",encoding="utf-8")

def _workbench_json_pilot(host_station, out, exp, progress):
    settings = host_station.store.settings()
    local = dict(settings.get("local") or {})
    runtime_status = host_station.ollama.status()
    if local.get("kind") != "ollama" or not local.get("model"):
        raise ContractError("M6-WB-001 requires an onboarded local Ollama model")
    controls = exp.get("frozen_controls") or {}
    progress("Freezing model and experiment identity", 5)
    with tempfile.TemporaryDirectory(prefix="residual-research-", dir=out) as root:
        station = Station(root)
        save_settings(station.store, {
            "local": local,
            "review_placement": "local",
            "workers": 1,
            "max_output_tokens": int(controls.get("max_output_tokens", 1600)),
            "batch_max_passes": int(controls.get("batch_max_passes", 5)),
            "batch_token_budget": int(controls.get("batch_token_budget", 30000)),
            "batch_wall_clock_s": int(controls.get("batch_wall_clock_s", 600)),
        })
        checks = [
            {"kind": "json_valid", "path": "research/workbench_result.json"},
            {"kind": "json_exact", "path": "research/workbench_result.json", "value": PILOT_DOCUMENT},
        ]
        manifest = {
            "schema_version": 1,
            "name": "M6 Workbench Governance Pilot",
            "goal": "Exercise the Research Workbench end-to-end without executing model-authored code.",
            "tasks": [{
                "id": "M6-WB-001",
                "title": "Produce declarative governed research artifact",
                "instruction": PILOT_SPEC,
                "files": ["research/workbench_result.json"],
                "context": [],
                "depends_on": [],
                "route": "local",
                "checks": checks,
            }],
        }
        mission = "# M6 Workbench governance pilot\n\n" + PILOT_SPEC + "\n\n```json\n" + json.dumps(manifest, indent=2) + "\n```\n"
        progress("Creating isolated experimental mission", 10)
        pid = station.create(mission, commands=False)["project_id"]
        progress("Running frozen model trial and verification gates", 20)
        result = station.batch(pid, lambda detail, pct=None: progress("Trial: " + detail, 20 + int((pct or 0) * 0.65)))
        project = station.store.project(pid)
        task = project["tasks"][0]
        metrics = station.metrics(pid)
        generated = None
        release_files = []
        export_error = None
        if task["state"] == "integrated":
            try:
                progress("Exporting accepted artifact and receipts", 90)
                art = station.export(pid)
                _, raw = station.store.artifact(art["id"])
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    release_files = sorted(z.namelist())
                    if "research/workbench_result.json" in release_files:
                        generated = z.read("research/workbench_result.json").decode("utf-8")
            except Exception as exc:
                export_error = f"{type(exc).__name__}: {exc}"
        attempt_artifacts = []
        for ref in task.get("artifacts", []):
            try:
                meta, raw = station.store.artifact(ref["id"])
                txt = raw.decode("utf-8", errors="replace")
                attempt_artifacts.append({
                    "id": ref["id"], "name": meta["name"], "kind": meta["kind"],
                    "sha256": ref["sha256"], "size": meta["size"],
                    "content": txt[:200000], "content_truncated": len(txt) > 200000,
                })
            except Exception as exc:
                attempt_artifacts.append({"id": ref.get("id"), "artifact_error": f"{type(exc).__name__}: {exc}"})
        events = station.store.events(pid, 0, 2000)
        (out / "events.jsonl").write_text("".join(canonical(x) + "\n" for x in events), encoding="utf-8")
        ok = (
            result["integrated"] == 1
            and task["state"] == "integrated"
            and all(x.get("passed") is True for x in task["checks_result"])
            and task.get("review", {}).get("approved") is True
            and bool(task.get("verification_receipt"))
            and generated is not None
            and export_error is None
        )
        evidence = {
            "schema_version": 1,
            "experiment": "M6-WB-001",
            "outcome": "PASS" if ok else "FAIL",
            "hypothesis": exp.get("hypothesis"),
            "acceptance_policy": exp.get("acceptance_policy"),
            "provider": {"kind": "ollama", "model": local["model"]},
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "cpu_count": runtime_status.get("cpu_count"),
                "ollama_connected": runtime_status.get("connected"),
                "model_record": next((m for m in runtime_status.get("models", []) if m.get("name") == local["model"]), None),
            },
            "pilot_document_sha256": hashlib.sha256(canonical(PILOT_DOCUMENT).encode("utf-8")).hexdigest(),
            "batch": result,
            "metrics": metrics,
            "task": {
                "state": task["state"], "attempt": task["attempt"], "findings": task["findings"],
                "checks_result": task["checks_result"], "review": task.get("review"),
                "head_commit": task.get("head_commit"), "verification_receipt": task.get("verification_receipt"),
            },
            "release_files": release_files,
            "generated_artifact": generated,
            "generated_artifact_sha256": hashlib.sha256(generated.encode("utf-8")).hexdigest() if generated else None,
            "export_error": export_error,
            "attempt_artifacts": attempt_artifacts,
            "events": [
                {"seq": x["seq"], "type": x["event_type"], "task_id": x["task_id"], "actor": x["actor"], "data": x["data"]}
                for x in events
                if x["event_type"] in {
                    "task.transition", "task.finding", "usage.recorded", "checks.completed",
                    "review.completed", "integration.completed", "release.exported",
                }
            ],
        }
        return evidence


def _workbench_pilot_preflight(station):
    settings=station.store.settings()
    local=dict(settings.get("local") or {})
    if local.get("kind")!="ollama" or not local.get("model"):
        raise ContractError("M6-WB-001 requires an onboarded local Ollama model")
    status=station.ollama.status()
    if not status.get("connected"):
        raise ContractError("Start the local Ollama runtime before beginning M6-WB-001")
    installed={m.get("name") for m in status.get("models",[]) if isinstance(m,dict)}
    if local["model"] not in installed:
        raise ContractError("The configured local model is not installed in Ollama")

PREFLIGHTS={"workbench_json_pilot":_workbench_pilot_preflight}
ADAPTERS={"workbench_json_pilot":_workbench_json_pilot}

def run(station, experiment_id, run_id, progress=lambda *a: None):
    out, manifest = _load_run(station, experiment_id, run_id)
    exp = json.loads((out/"experiment.json").read_text(encoding="utf-8"))
    adapter = exp.get("adapter")
    if adapter not in ADAPTERS:
        raise ContractError("This experiment is staged but its execution adapter is not installed")
    manifest["run_status"]="RUNNING"; (out/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    try:
        evidence=ADAPTERS[adapter](station,out,exp,progress)
        (out/"evidence.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        manifest["run_status"]="COMPLETED"; manifest["outcome"]=evidence["outcome"]
        (out/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
        _write_sums(out); progress("Research evidence bundle complete",100)
        return {"experiment_id":experiment_id,"run_id":run_id,"outcome":evidence["outcome"],"evidence":str(out/"evidence.json")}
    except Exception as exc:
        manifest["run_status"]="FAILED"; (out/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
        safe_message=str(exc)[:500] if isinstance(exc, ContractError) else "internal experiment execution error"
        (out/"failure.json").write_text(json.dumps({"type":type(exc).__name__,"message":safe_message},indent=2,sort_keys=True)+"\n",encoding="utf-8")
        _write_sums(out)
        raise


def export_bundle(station, experiment_id, run_id):
    out, _ = _load_run(station, experiment_id, run_id)
    _write_sums(out)
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,"w",zipfile.ZIP_DEFLATED) as z:
        for p in sorted(x for x in out.rglob("*") if x.is_file()):
            z.write(p, arcname=p.relative_to(out).as_posix())
    return buffer.getvalue()
