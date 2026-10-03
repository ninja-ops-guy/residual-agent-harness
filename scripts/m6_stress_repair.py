from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from residual.station.models import save_settings
from residual.station.service import Station

MANIFEST = {
    "schema_version": 1,
    "name": "Repeated Repair Pressure",
    "goal": "Implement a tiny function while two deterministic candidate corruptions force the repair loop to consume its first two attempts.",
    "tasks": [{
        "id": "REPAIR-001",
        "title": "Implement increment",
        "instruction": "Create counter.py with increment(value) returning value + 1. Keep it minimal and modify only counter.py.",
        "files": ["counter.py"],
        "context": [],
        "depends_on": [],
        "route": "local",
        "checks": [
            {"kind": "python_compile", "path": "counter.py"},
            {"kind": "command", "argv": ["{python}", "-c",
             "from counter import increment; assert increment(1)==2; assert increment(-1)==0; assert increment(2.5)==3.5"], "timeout": 30},
        ],
    }],
}


def read_events(path: Path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="qwen2.5-coder:1.5b")
    p.add_argument("--base-url", default="http://127.0.0.1:11434")
    p.add_argument("--proxy-events", default="/tmp/residual-repair-proxy-events.jsonl")
    p.add_argument("--output", default="runs/m6-stress-repair/evidence.json")
    a = p.parse_args()
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    spec = "# Repeated repair pressure\n\n```json\n" + json.dumps(MANIFEST, indent=2) + "\n```\n"
    with tempfile.TemporaryDirectory(prefix="residual-repair-stress-") as root:
        station = Station(root)
        save_settings(station.store, {
            "local": {"kind": "ollama", "model": a.model, "base_url": a.base_url, "output_token_field": "max_tokens"},
            "review_placement": "local",
            "workers": 1,
            "max_output_tokens": 768,
            "batch_max_passes": 3,
            "batch_token_budget": 30000,
            "batch_wall_clock_s": 900,
        })
        pid = station.create(spec, commands=True)["project_id"]
        result = station.batch(pid)
        project = station.store.project(pid)
        ev = station.store.events(pid, 0, 100000)
        transitions = [e for e in ev if e["event_type"] == "task.transition"]
        injected = read_events(Path(a.proxy_events))
        task = project["tasks"][0]
        data = {
            "schema_version": 1,
            "campaign": "M6-STRESS-B",
            "experiment": "STRESS-B4-repair-pressure",
            "baseline_sha": "699e2869e294fe157b4bfd73a272057683a2f7e0",
            "environment": {"python": sys.version, "platform": platform.platform()},
            "model": a.model,
            "batch": result,
            "metrics": station.metrics(pid),
            "task": {k: task.get(k) for k in ("id","state","attempt","findings","checks_result","review","head_commit","base_commit","checks_hash","verification_receipt")},
            "transitions": transitions,
            "proxy_events": injected,
            "faults_injected": sum(1 for e in injected if e.get("event") == "fault_injected"),
            "corrupted_candidate_integrated": any(
                e["event_type"] == "integration.completed" and
                sum(1 for pe in injected if pe.get("event") == "fault_injected") < 2
                for e in ev
            ),
            "all_events": ev,
        }
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print("STRESS_REPAIR_EVIDENCE=" + json.dumps(data, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
