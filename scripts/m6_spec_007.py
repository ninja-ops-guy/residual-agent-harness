from __future__ import annotations

import argparse
import hashlib
import io
import json
import tempfile
import zipfile
from pathlib import Path

from residual.core import canonical
from residual.station.models import save_settings
from residual.station.service import Station
from residual.station import workspace as ws


RUNS = [
    {
        "id": "M6-SPEC-006",
        "outcome": "success",
        "runner_attempts": 3,
        "first_request_bytes": 5614,
        "first_call_elapsed_ms": 213211,
        "model_calls": 4,
        "reported_tokens": 9217,
        "wall_clock_s": 759.722,
        "provider_timeouts": 0,
        "identical_failure_repeats": 0,
        "evidence_sha256": "ab7d8cfb639557510fff9789aa4c14a2ed940ecc71b37a5190fba0de84f13e61",
    },
    {
        "id": "M6-ROADMAP-001B",
        "outcome": "success",
        "runner_attempts": 1,
        "first_request_bytes": 5535,
        "first_call_elapsed_ms": 231142,
        "model_calls": 2,
        "reported_tokens": 4384,
        "wall_clock_s": 435.182,
        "provider_timeouts": 0,
        "identical_failure_repeats": 0,
        "evidence_sha256": "908b3b748b7d4841bdf92330e2cee5708bc65547663788dd5d0de29a4477effc",
    },
    {
        "id": "M6-SHIP-001",
        "outcome": "failed",
        "runner_attempts": 5,
        "first_request_bytes": 30606,
        "first_call_elapsed_ms": 269391,
        "model_calls": 5,
        "reported_tokens": 12825,
        "wall_clock_s": 823.616,
        "provider_timeouts": 0,
        "identical_failure_repeats": 4,
        "evidence_sha256": "69480331425268d01d08dd41c9778f94b347d2668328f4400fbe08d462cc7ffd",
    },
    {
        "id": "M6-SHIP-003",
        "outcome": "aborted",
        "runner_attempts": 1,
        "first_request_bytes": 32652,
        "first_call_elapsed_ms": 300097,
        "model_calls": 1,
        "reported_tokens": 0,
        "wall_clock_s": 300.205,
        "provider_timeouts": 1,
        "identical_failure_repeats": 0,
        "evidence_sha256": "bc62f566fbacb23600bab3348a7071b40ea0844fe8d8a45486bc8458617f2702",
    },
    {
        "id": "M6-SHIP-004",
        "outcome": "success",
        "runner_attempts": 5,
        "first_request_bytes": 7663,
        "first_call_elapsed_ms": 275152,
        "model_calls": 6,
        "reported_tokens": 16558,
        "wall_clock_s": 1163.466,
        "provider_timeouts": 0,
        "identical_failure_repeats": 0,
        "evidence_sha256": "7a6b9b31c9ca7116a73ea49ea9ba85c71a7ecd24097942e86af9b0aaf70ced69",
    },
]

METRIC_CATALOG = [
    "shipping_task_success_rate",
    "provider_timeout_rate",
    "mean_runner_attempts",
    "mean_first_request_bytes",
    "context_bytes_success_mean",
    "context_bytes_non_success_mean",
    "mean_wall_clock_s",
    "successful_mean_wall_clock_s",
    "identical_failure_repeats_total",
    "mean_reported_tokens_per_run",
]


def metrics():
    success = [r for r in RUNS if r["outcome"] == "success"]
    nonsuccess = [r for r in RUNS if r["outcome"] != "success"]
    n = len(RUNS)
    return {
        "shipping_task_success_rate": round(len(success) / n, 6),
        "provider_timeout_rate": round(sum(r["provider_timeouts"] for r in RUNS) / n, 6),
        "mean_runner_attempts": round(sum(r["runner_attempts"] for r in RUNS) / n, 6),
        "mean_first_request_bytes": round(sum(r["first_request_bytes"] for r in RUNS) / n, 6),
        "context_bytes_success_mean": round(sum(r["first_request_bytes"] for r in success) / len(success), 6),
        "context_bytes_non_success_mean": round(sum(r["first_request_bytes"] for r in nonsuccess) / len(nonsuccess), 6),
        "mean_wall_clock_s": round(sum(r["wall_clock_s"] for r in RUNS) / n, 6),
        "successful_mean_wall_clock_s": round(sum(r["wall_clock_s"] for r in success) / len(success), 6),
        "identical_failure_repeats_total": sum(r["identical_failure_repeats"] for r in RUNS),
        "mean_reported_tokens_per_run": round(sum(r["reported_tokens"] for r in RUNS) / n, 6),
    }


INSTRUCTION = """Act as RESIDUAL's analysis-only Improvement Scientist.

You are given a hash-bound EvidenceSnapshot containing actual retained measurements from prior M6 self-development/shipping runs. No improvement question, target metric, or hypothesis is supplied.

Choose the single most defensible improvement opportunity supported by the measured evidence. Prefer an improvement_spec when the existing metrics support a falsifiable claim. Use measurement_gap only when a defensible hypothesis genuinely requires a missing dimension.

Do not invent measurements, numeric baselines, run outcomes, or evidence. Do not treat missing telemetry as proof of a defect. You have no implementation, Git, evaluator, integration, or promotion authority.

Write proposal.json only.

For type=improvement_spec use exactly:
{
  "type":"improvement_spec",
  "observation":{
    "metric":"<measured metric id>",
    "value":<exact measured numeric value>,
    "comparison_metric":"<optional measured metric id>",
    "comparison_value":<exact measured numeric value if comparison_metric is present>
  },
  "hypothesis":"<falsifiable statement connecting a proposed change to measured outcomes>",
  "target_metrics":["<measured metric ids>"],
  "preserve_metrics":["<different measured metric ids>"],
  "protected_invariants":["M4"|"evidence_integrity"|"verification_integrity"|"promotion_authority"],
  "acceptance":[
    {"metric":"<declared target or preserve metric>","operator":"<="|">="|"=="|"<"|">","threshold":<finite number>}
  ],
  "evidence_snapshot_hash":"<exact snapshot hash>",
  "human_approval_required":true
}

For type=measurement_gap use exactly:
{
  "type":"measurement_gap",
  "question":"<specific unanswered empirical question>",
  "missing_metric":"<metric not already present>",
  "why_needed":"<why current measured dimensions cannot answer the question>",
  "proposed_measurement":"<mechanically collectible measurement>",
  "preserve_invariants":["M4"|"evidence_integrity"|"verification_integrity"|"promotion_authority"],
  "evidence_snapshot_hash":"<exact snapshot hash>",
  "human_approval_required":true
}

Do not optimize for novelty. Optimize for evidence quality, falsifiability, and preserving existing verified behavior."""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="qwen2.5-coder:7b")
    p.add_argument("--base-url", default="http://127.0.0.1:11443")
    p.add_argument("--output", default="runs/m6-spec-007c/evidence.json")
    args = p.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parents[1]

    payload = {
        "schema_version": 1,
        "baseline_commit": "60d0c5a8fc2044a22619248292ce89c9b43edd37",
        "source_evidence": [r["evidence_sha256"] for r in RUNS],
        "sample_count": len(RUNS),
        "metric_catalog": METRIC_CATALOG,
        "metrics": metrics(),
        "protected_invariant_catalog": [
            "M4", "evidence_integrity", "verification_integrity", "promotion_authority"
        ],
        "scope": "Aggregate M6 self-development/shipping measurements; raw run artifacts remain bound by source_evidence hashes",
    }
    snapshot_hash = hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()
    snapshot = {**payload, "snapshot_hash": snapshot_hash}

    with tempfile.TemporaryDirectory() as root:
        root = Path(root)
        source = root / "source"
        checker = (repo_root / "scripts" / "m6_spec_007_check.py").read_text(encoding="utf-8")
        ws.init_repo(source, {
            "evidence/m6-discovery-snapshot.json": json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            "scripts/m6_spec_007_check.py": checker,
            "README.md": "# M6-SPEC-007 autonomous discovery fixture\n",
        })

        station = Station(root / "station")
        save_settings(station.store, {
            "local": {
                "kind": "ollama",
                "model": args.model,
                "base_url": args.base_url,
                "output_token_field": "max_tokens",
            },
            "review_placement": "local",
            "workers": 1,
            "max_output_tokens": 1200,
            "batch_max_passes": 5,
            "batch_token_budget": 30000,
            "batch_wall_clock_s": 1500,
        })

        manifest = {
            "schema_version": 1,
            "name": "M6-SPEC-007 Autonomous Improvement Discovery",
            "goal": "Originate one defensible improvement hypothesis or evidence gap from retained RESIDUAL measurements.",
            "tasks": [{
                "id": "M6-DISCOVER-001",
                "title": "Discover improvement opportunity from evidence",
                "instruction": INSTRUCTION,
                "files": ["proposal.json"],
                "context": [
                    "evidence/m6-discovery-snapshot.json",
                ],
                "depends_on": [],
                "route": "local",
                "checks": [
                    {"kind": "json_valid", "path": "proposal.json"},
                    {"kind": "command", "argv": ["{python}", "scripts/m6_spec_007_check.py"], "timeout": 30},
                ],
            }],
        }
        mission = "# M6-SPEC-007\n\n" + INSTRUCTION + "\n\n```json\n" + json.dumps(manifest, indent=2) + "\n```\n"
        pid = station.create(mission, source=str(source), commands=True)["project_id"]
        result = station.batch(pid)
        project = station.store.project(pid)
        task = project["tasks"][0]
        usage = station.metrics(pid)
        events = station.store.events(pid, 0, 5000)

        proposal = None
        release_files = []
        export_error = None
        if task["state"] == "integrated":
            try:
                artifact = station.export(pid)
                _, raw = station.store.artifact(artifact["id"])
                with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
                    release_files = sorted(bundle.namelist())
                    if "proposal.json" in release_files:
                        proposal = json.loads(bundle.read("proposal.json"))
            except Exception as exc:
                export_error = f"{type(exc).__name__}: {exc}"

        attempt_artifacts = []
        for ref in task.get("artifacts", []):
            try:
                meta, raw = station.store.artifact(ref["id"])
                text = raw.decode("utf-8", errors="replace")
                attempt_artifacts.append({
                    "id": ref["id"],
                    "name": meta["name"],
                    "kind": meta["kind"],
                    "sha256": ref["sha256"],
                    "size": meta["size"],
                    "content": text[:200000],
                    "content_truncated": len(text) > 200000,
                })
            except Exception as exc:
                attempt_artifacts.append({
                    "id": ref.get("id"),
                    "artifact_error": f"{type(exc).__name__}: {exc}",
                })

        evidence = {
            "schema_version": 1,
            "experiment": "M6-SPEC-007C",
            "snapshot": snapshot,
            "instruction_sha256": hashlib.sha256(INSTRUCTION.encode()).hexdigest(),
            "batch": result,
            "metrics": usage,
            "task": {
                "attempt": task["attempt"],
                "state": task["state"],
                "findings": task["findings"],
                "checks_result": task["checks_result"],
                "review": task.get("review"),
                "verification_receipt": task.get("verification_receipt"),
            },
            "proposal": proposal,
            "attempt_artifacts": attempt_artifacts,
            "release_files": release_files,
            "export_error": export_error,
            "events": [{
                "seq": e["seq"],
                "type": e["event_type"],
                "task_id": e["task_id"],
                "actor": e["actor"],
                "data": e["data"],
            } for e in events if e["event_type"] in {
                "task.transition", "task.finding", "checks.completed",
                "review.completed", "integration.completed", "usage.recorded",
                "release.exported", "project.note",
            }],
        }
        out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("M6_SPEC_007_EVIDENCE=" + json.dumps(evidence, sort_keys=True, separators=(",", ":")))

        ok = (
            result["integrated"] == 1
            and task["state"] == "integrated"
            and all(check.get("passed") is True for check in task["checks_result"])
            and task.get("review", {}).get("approved") is True
            and bool(task.get("verification_receipt"))
            and proposal is not None
            and export_error is None
        )
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
