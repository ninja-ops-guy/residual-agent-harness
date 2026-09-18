from __future__ import annotations

import argparse
import io
import json
import os
import tempfile
import zipfile
from pathlib import Path

from residual.station.models import save_settings
from residual.station.service import Station


MANIFEST = {
    "schema_version": 1,
    "name": "Real Model Dependency DAG Mission",
    "goal": "Build a three-module numeric pipeline with deterministic dependency ordering, repair, review, integration, and release evidence.",
    "tasks": [
        {
            "id": "CORE-001",
            "title": "Implement clamp primitive",
            "instruction": "Create math_core.py with clamp(value, low, high). Return low when value is below low, high when above high, otherwise value. Raise ValueError when low > high. Keep the implementation minimal.",
            "files": ["math_core.py"],
            "context": [],
            "depends_on": [],
            "route": "local",
            "checks": [
                {"kind": "python_compile", "path": "math_core.py"},
                {
                    "kind": "command",
                    "argv": [
                        "{python}",
                        "-c",
                        "from math_core import clamp; assert clamp(-5,0,10)==0; assert clamp(20,0,10)==10; assert clamp(4,0,10)==4\ntry: clamp(1,5,2)\nexcept ValueError: pass\nelse: raise AssertionError('invalid bounds accepted')"
                    ],
                    "timeout": 30
                }
            ]
        },
        {
            "id": "STATS-002",
            "title": "Implement clamped mean",
            "instruction": "Create stats.py with mean_clamped(values, low, high). Import and use math_core.clamp for every input, then return the arithmetic mean of the clamped values. Raise ValueError for an empty input sequence. Do not duplicate the clamp implementation.",
            "files": ["stats.py"],
            "context": ["math_core.py"],
            "depends_on": ["CORE-001"],
            "route": "local",
            "checks": [
                {"kind": "python_compile", "path": "stats.py"},
                {
                    "kind": "command",
                    "argv": [
                        "{python}",
                        "-c",
                        "from stats import mean_clamped; assert mean_clamped([-5,5,20],0,10)==5; assert mean_clamped([2,4,6],0,10)==4\ntry: mean_clamped([],0,10)\nexcept ValueError: pass\nelse: raise AssertionError('empty input accepted')"
                    ],
                    "timeout": 30
                }
            ]
        },
        {
            "id": "REPORT-003",
            "title": "Build summary API",
            "instruction": "Create report.py with summarize(values, low, high). Import stats.mean_clamped and return exactly a dictionary with keys count and mean_clamped, where count is len(values) and mean_clamped is the calculated value. Let ValueError from mean_clamped propagate for empty input.",
            "files": ["report.py"],
            "context": ["math_core.py", "stats.py"],
            "depends_on": ["STATS-002"],
            "route": "local",
            "checks": [
                {"kind": "python_compile", "path": "report.py"},
                {
                    "kind": "command",
                    "argv": [
                        "{python}",
                        "-c",
                        "from report import summarize; assert summarize([-5,5,20],0,10)=={'count':3,'mean_clamped':5}\ntry: summarize([],0,10)\nexcept ValueError: pass\nelse: raise AssertionError('empty input accepted')"
                    ],
                    "timeout": 30
                }
            ]
        }
    ]
}

FENCE = chr(96) * 3
SPEC = (
    "# Real-model dependency DAG mission\n\n"
    "The implementation model receives only this specification and dependency context. "
    "One STATS-002 candidate is deliberately fault-injected after model generation so RESIDUAL must exercise its repair loop.\n\n"
    + FENCE + "json\n"
    + json.dumps(MANIFEST, indent=2)
    + "\n" + FENCE + "\n"
)


def read_proxy_events(path: str | None) -> list[dict]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    events = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(json.loads(line))
    return events


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--station-model", default="residual-role-proxy")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--runner-model", required=True)
    parser.add_argument("--reviewer-model", required=True)
    parser.add_argument("--proxy-events", default=os.environ.get("ROLE_PROXY_EVENTS", ""))
    parser.add_argument("--output", default="runs/dag-real-model-mission/evidence.json")
    args = parser.parse_args()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as root:
        station = Station(root)
        save_settings(station.store, {
            "local": {
                "kind": "ollama",
                "model": args.station_model,
                "base_url": args.base_url,
                "output_token_field": "max_tokens"
            },
            "review_placement": "local",
            "workers": 1,
            "max_output_tokens": 1024,
            "batch_max_passes": 9,
            "batch_token_budget": 60000,
            "batch_wall_clock_s": 900
        })

        pid = station.create(SPEC, commands=True)["project_id"]
        result = station.batch(pid)
        project = station.store.project(pid)
        metrics = station.metrics(pid)
        tasks = {task["id"]: task for task in project["tasks"]}
        events = station.store.events(pid, 0, 2000)
        proxy_events = read_proxy_events(args.proxy_events)

        release_files = []
        generated_sources = {}
        export_error = None
        if result["integrated"] == 3:
            try:
                artifact = station.export(pid)
                _, release = station.store.artifact(artifact["id"])
                with zipfile.ZipFile(io.BytesIO(release)) as bundle:
                    release_files = sorted(bundle.namelist())
                    for name in ("math_core.py", "stats.py", "report.py"):
                        if name in release_files:
                            generated_sources[name] = bundle.read(name).decode("utf-8")
            except Exception as exc:
                export_error = f"{type(exc).__name__}: {exc}"

        usage = [
            event["data"]
            for event in events
            if event["event_type"] == "usage.recorded"
        ]
        station_runner_models = sorted({item.get("model") for item in usage if item.get("role") == "runner"})
        station_reviewer_models = sorted({item.get("model") for item in usage if item.get("role") == "reviewer"})
        routed_runner_models = sorted({
            item.get("routed_model") for item in proxy_events
            if item.get("event") == "route" and item.get("role") == "runner"
        })
        routed_reviewer_models = sorted({
            item.get("routed_model") for item in proxy_events
            if item.get("event") == "route" and item.get("role") == "reviewer"
        })

        repair_transitions = [
            event for event in events
            if event["event_type"] == "task.transition"
            and event["task_id"] == "STATS-002"
            and event["data"].get("to") == "repair_required"
        ]

        evidence = {
            "schema_version": 1,
            "mission": project["name"],
            "goal": project["goal"],
            "provider": {
                "station_model": args.station_model,
                "runner_model": args.runner_model,
                "reviewer_model": args.reviewer_model,
                "base_url": args.base_url
            },
            "project_id": pid,
            "batch": result,
            "metrics": metrics,
            "tasks": {
                task_id: {
                    "state": task["state"],
                    "attempt": task["attempt"],
                    "findings": task["findings"],
                    "checks_result": task["checks_result"],
                    "review": task.get("review"),
                    "head_commit": task.get("head_commit"),
                    "verification_receipt": task.get("verification_receipt")
                }
                for task_id, task in tasks.items()
            },
            "station_runner_models_observed": station_runner_models,
            "station_reviewer_models_observed": station_reviewer_models,
            "routed_runner_models_observed": routed_runner_models,
            "routed_reviewer_models_observed": routed_reviewer_models,
            "repair_transition_count": len(repair_transitions),
            "proxy_events": proxy_events,
            "release_files": release_files,
            "generated_sources": generated_sources,
            "export_error": export_error,
            "events": [
                {
                    "seq": event["seq"],
                    "type": event["event_type"],
                    "task_id": event["task_id"],
                    "actor": event["actor"],
                    "data": event["data"]
                }
                for event in events
                if event["event_type"] in {
                    "task.transition", "task.finding", "usage.recorded",
                    "checks.completed", "review.completed", "integration.completed",
                    "project.note", "release.exported"
                }
            ]
        }

        out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("DAG_REAL_MODEL_EVIDENCE=" + json.dumps(evidence, sort_keys=True, separators=(",", ":")))

        fault_events = [
            event for event in proxy_events
            if event.get("event") == "fault_injected" and event.get("task_id") == "STATS-002"
        ]
        all_integrated = result["integrated"] == 3 and all(task["state"] == "integrated" for task in tasks.values())
        all_checks_pass = all(
            task["checks_result"] and all(check.get("passed") is True for check in task["checks_result"])
            for task in tasks.values()
        )
        all_reviews_approved = all(task.get("review", {}).get("approved") is True for task in tasks.values())
        all_receipts = all(bool(task.get("verification_receipt")) for task in tasks.values())
        model_separation = (
            routed_runner_models == [args.runner_model]
            and routed_reviewer_models == [args.reviewer_model]
            and args.runner_model != args.reviewer_model
        )
        repair_exercised = tasks["STATS-002"]["attempt"] >= 2 and len(repair_transitions) >= 1 and len(fault_events) == 1
        release_ok = set(["math_core.py", "stats.py", "report.py"]).issubset(release_files)

        success = all((
            all_integrated,
            all_checks_pass,
            all_reviews_approved,
            all_receipts,
            model_separation,
            repair_exercised,
            release_ok,
            export_error is None,
        ))
        return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
