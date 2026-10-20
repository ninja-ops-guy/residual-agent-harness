from __future__ import annotations

import argparse
import io
import json
import platform
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from residual.station.models import save_settings
from residual.station.service import Station

MANIFEST = {
    "schema_version": 1,
    "name": "Six Task Dependency DAG Pressure",
    "goal": "Build a small numeric processing pipeline through parallel roots, dependent integration, accumulated checks, review receipts, and final release export.",
    "tasks": [
        {
            "id": "DAG-A",
            "title": "Clamp primitive",
            "instruction": "Create math_core.py with clamp(value, low, high). Raise ValueError when low > high; otherwise clamp inclusively.",
            "files": ["math_core.py"], "context": [], "depends_on": [], "route": "local",
            "checks": [
                {"kind": "python_compile", "path": "math_core.py"},
                {"kind": "command", "argv": ["{python}", "-c",
                 "from math_core import clamp; assert clamp(-1,0,10)==0; assert clamp(20,0,10)==10; assert clamp(4,0,10)==4\ntry: clamp(1,2,1)\nexcept ValueError: pass\nelse: raise AssertionError('bounds')"], "timeout": 30},
            ],
        },
        {
            "id": "DAG-B",
            "title": "Integer parser",
            "instruction": "Create parsing.py with parse_ints(values). Return a list of int(str(v).strip()) for each input. Let ValueError propagate.",
            "files": ["parsing.py"], "context": [], "depends_on": [], "route": "local",
            "checks": [
                {"kind": "python_compile", "path": "parsing.py"},
                {"kind": "command", "argv": ["{python}", "-c",
                 "from parsing import parse_ints; assert parse_ints([' 1 ','-2',3])==[1,-2,3]"], "timeout": 30},
            ],
        },
        {
            "id": "DAG-C",
            "title": "Label formatter",
            "instruction": "Create formatting.py with label(name, value) returning exactly f'{name.upper()}={value}'.",
            "files": ["formatting.py"], "context": [], "depends_on": [], "route": "local",
            "checks": [
                {"kind": "python_compile", "path": "formatting.py"},
                {"kind": "command", "argv": ["{python}", "-c",
                 "from formatting import label; assert label('count',3)=='COUNT=3'"], "timeout": 30},
            ],
        },
        {
            "id": "DAG-D",
            "title": "Clamped mean",
            "instruction": "Create stats.py with mean_clamped(values, low, high). Import math_core.clamp, clamp every value, raise ValueError for empty input, then return arithmetic mean.",
            "files": ["stats.py"], "context": ["math_core.py"], "depends_on": ["DAG-A"], "route": "local",
            "checks": [
                {"kind": "python_compile", "path": "stats.py"},
                {"kind": "command", "argv": ["{python}", "-c",
                 "from stats import mean_clamped; assert mean_clamped([-5,5,20],0,10)==5\ntry: mean_clamped([],0,10)\nexcept ValueError: pass\nelse: raise AssertionError('empty')"], "timeout": 30},
            ],
        },
        {
            "id": "DAG-E",
            "title": "Pipeline summary",
            "instruction": "Create pipeline.py with summarize(raw_values, low, high). Import parsing.parse_ints and stats.mean_clamped. Return exactly {'count': len(parsed), 'mean': mean_clamped(parsed, low, high)}.",
            "files": ["pipeline.py"], "context": ["parsing.py", "stats.py"], "depends_on": ["DAG-B", "DAG-D"], "route": "local",
            "checks": [
                {"kind": "python_compile", "path": "pipeline.py"},
                {"kind": "command", "argv": ["{python}", "-c",
                 "from pipeline import summarize; assert summarize(['-5','5','20'],0,10)=={'count':3,'mean':5}"], "timeout": 30},
            ],
        },
        {
            "id": "DAG-F",
            "title": "Final report",
            "instruction": "Create report.py with render(raw_values, low, high). Import pipeline.summarize and formatting.label. Return exactly COUNT=<count> followed by one space and MEAN=<mean>.",
            "files": ["report.py"], "context": ["pipeline.py", "formatting.py"], "depends_on": ["DAG-C", "DAG-E"], "route": "local",
            "checks": [
                {"kind": "python_compile", "path": "report.py"},
                {"kind": "command", "argv": ["{python}", "-c",
                 "from report import render; assert render(['-5','5','20'],0,10)=='COUNT=3 MEAN=5.0'"], "timeout": 30},
            ],
        },
    ],
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="qwen2.5-coder:3b")
    p.add_argument("--output", default="runs/m6-stress-dag/evidence.json")
    a = p.parse_args()
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    spec = "# Six-task DAG pressure\n\n```json\n" + json.dumps(MANIFEST, indent=2) + "\n```\n"
    with tempfile.TemporaryDirectory(prefix="residual-dag-stress-") as root:
        station = Station(root)
        save_settings(station.store, {
            "local": {"kind": "ollama", "model": a.model, "base_url": "http://127.0.0.1:11434", "output_token_field": "max_tokens"},
            "review_placement": "local",
            "workers": 3,
            "max_output_tokens": 1100,
            "batch_max_passes": 18,
            "batch_token_budget": 150000,
            "batch_wall_clock_s": 1800,
        })
        pid = station.create(spec, commands=True)["project_id"]
        result = station.batch(pid)
        project = station.store.project(pid)
        ev = station.store.events(pid, 0, 100000)
        integration_order = [e["task_id"] for e in ev if e["event_type"] == "integration.completed"]
        transition_order = [
            {"seq": e["seq"], "task_id": e["task_id"], "from": e["data"].get("from"), "to": e["data"].get("to")}
            for e in ev if e["event_type"] == "task.transition"
        ]
        export = {"attempted": False, "succeeded": False, "files": [], "error": None}
        if all(t["state"] == "integrated" for t in project["tasks"]):
            export["attempted"] = True
            try:
                art = station.export(pid)
                _, raw = station.store.artifact(art["id"])
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    export["files"] = sorted(z.namelist())
                export["succeeded"] = True
                export["artifact_id"] = art["id"]
            except Exception as exc:
                export["error"] = f"{type(exc).__name__}: {exc}"
        task_data = []
        for t in station.store.project(pid)["tasks"]:
            task_data.append({
                k: t.get(k) for k in (
                    "id","state","attempt","depends_on","findings","checks_result","review",
                    "base_commit","head_commit","checks_hash","verification_receipt","artifacts"
                )
            })
        data = {
            "schema_version": 1,
            "campaign": "M6-STRESS-A",
            "experiment": "STRESS-A5-dag-pressure",
            "baseline_sha": "699e2869e294fe157b4bfd73a272057683a2f7e0",
            "environment": {"python": sys.version, "platform": platform.platform()},
            "model": a.model,
            "manifest": MANIFEST,
            "batch": result,
            "metrics": station.metrics(pid),
            "tasks": task_data,
            "integration_order": integration_order,
            "transition_order": transition_order,
            "repair_transitions": sum(1 for x in transition_order if x["to"] == "repair_required"),
            "export": export,
            "events": ev,
            "report": station.store.report(pid),
        }
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print("STRESS_DAG_EVIDENCE=" + json.dumps(data, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
