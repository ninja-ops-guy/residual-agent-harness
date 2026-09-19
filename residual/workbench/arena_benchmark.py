"""AX-ARENA workbench: freeze randomized paired protocols and score traces.

This module does not submit results to Arena and does not reproduce Arena's
private production leaderboard. It implements a local, evidence-preserving,
Arena-aligned harness experiment over RESIDUAL traces.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
from pathlib import Path

from ai_providers import DEFAULT_REGISTRY, ProviderError

from ..core import ContractError, canonical, digest, strict_json
from ..eval.arena import AgentEvaluationTrace, extract_arena_aligned_signals
from ..eval_frozen.workload import development_workload, workload_from_json

MANIFEST_SCHEMA = "residual.ax-arena-manifest.v1"
LOCK_SCHEMA = "residual.ax-arena-lock.v1"
REPORT_SCHEMA = "residual.ax-arena-report.v1"


def _write_json(path: Path, value, *, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")


def _percentile(values, q):
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * q
    low = int(position)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (position - low)


def _workload_payload(workload):
    return {
        "schema_version": workload.schema_version,
        "name": workload.name,
        "seed": workload.seed,
        "tasks": [task.payload() for task in workload.tasks],
        "sha256": workload.sha256,
    }


def _load_workload(manifest, manifest_path: Path | None):
    spec = manifest.get("workload")
    if not isinstance(spec, dict):
        raise ContractError("Arena manifest workload must be an object")
    kind = spec.get("kind")
    if kind == "development_fixture":
        return development_workload()
    if kind == "file":
        rel = spec.get("path")
        if not isinstance(rel, str) or not rel:
            raise ContractError("Arena workload file path required")
        base = manifest_path.parent if manifest_path else Path.cwd()
        path = (base / rel).resolve()
        return workload_from_json(path.read_text(encoding="utf-8"))
    raise ContractError("Arena workload kind must be development_fixture or file")


def _validate_manifest(manifest):
    if not isinstance(manifest, dict) or manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise ContractError("invalid AX-ARENA manifest")
    experiment_id = manifest.get("experiment_id")
    if not isinstance(experiment_id, str) or not experiment_id or len(experiment_id) > 120:
        raise ContractError("invalid AX-ARENA experiment id")
    if manifest.get("conditions") != ["control", "residual"]:
        raise ContractError("AX-ARENA requires ordered control/residual conditions")
    repeats = manifest.get("repeats")
    seed = manifest.get("seed")
    if type(repeats) is not int or not 1 <= repeats <= 100:
        raise ContractError("AX-ARENA repeats must be 1..100")
    if type(seed) is not int or seed < 0:
        raise ContractError("AX-ARENA seed must be nonnegative")
    if manifest.get("slice") not in {"development", "evaluation"}:
        raise ContractError("invalid AX-ARENA workload slice")
    if manifest.get("evidence_level") not in {"development_fixture", "live_model"}:
        raise ContractError("invalid AX-ARENA evidence level")
    if manifest.get("allow_provider_fallback") is not False:
        raise ContractError("AX-ARENA provider fallback must be disabled")


def _validate_models(models):
    if not models or len(models) != len(set(models)):
        raise ContractError("AX-ARENA requires distinct model refs")
    for model in models:
        if not isinstance(model, str) or not model.startswith("arena:") or len(model) > 600:
            raise ContractError("AX-ARENA model refs must use arena:<model-id>")
        if not model.removeprefix("arena:"):
            raise ContractError("AX-ARENA model id cannot be empty")


def _source_hashes():
    root = Path(__file__).resolve().parents[2]
    paths = (
        root / "ai_providers" / "adapters" / "arena_adapter.py",
        root / "residual" / "eval" / "arena.py",
        root / "residual" / "workbench" / "arena_benchmark.py",
    )
    result = {}
    for path in paths:
        if path.exists():
            result[path.relative_to(root).as_posix()] = digest(path.read_text(encoding="utf-8"))
    return result


def freeze_protocol(manifest, models, *, manifest_path: Path | None = None):
    _validate_manifest(manifest)
    models = list(models)
    _validate_models(models)
    workload = _load_workload(manifest, manifest_path)
    tasks = workload.slice_tasks(manifest["slice"])
    if not tasks:
        raise ContractError("AX-ARENA selected workload slice is empty")

    schedule = []
    for task in tasks:
        for model in models:
            for repeat in range(manifest["repeats"]):
                for condition in manifest["conditions"]:
                    identity = {
                        "experiment_id": manifest["experiment_id"],
                        "task_id": task.task_id,
                        "model": model,
                        "repeat": repeat,
                        "condition": condition,
                    }
                    schedule.append({
                        **identity,
                        "family": task.family,
                        "observation_id": manifest["experiment_id"] + ":" + digest(identity)[:20],
                    })
    rng = random.Random(manifest["seed"])
    rng.shuffle(schedule)

    protocol = {
        "schema_version": LOCK_SCHEMA,
        "experiment_id": manifest["experiment_id"],
        "title": manifest.get("title", ""),
        "methodology": "Arena-aligned randomized paired harness evaluation",
        "evidence_level": manifest["evidence_level"],
        "manifest_sha256": digest(manifest),
        "workload": _workload_payload(workload),
        "slice": manifest["slice"],
        "conditions": list(manifest["conditions"]),
        "models": models,
        "repeats": manifest["repeats"],
        "seed": manifest["seed"],
        "allow_provider_fallback": False,
        "primary_outcome": "verified_task_success",
        "arena_aligned_signals": [
            "confirmed_success",
            "praise_vs_complaint",
            "steerability",
            "bash_recovery",
            "tool_hallucination",
        ],
        "residual_signals": list(manifest.get("residual_signals", [])),
        "source_hashes": _source_hashes(),
        "schedule": schedule,
        "schedule_sha256": digest(schedule),
        "limitations": [
            "This is a local Arena-aligned evaluation, not an official Arena leaderboard submission or score.",
            "The Arena API is used only as a model gateway; server-side model fallback is disallowed by this protocol.",
            "Development fixtures are apparatus tests and must not be cited as live-model evidence.",
            "Live-model inference remains stochastic unless the selected backend itself guarantees stronger reproducibility.",
        ],
    }
    protocol["sha256"] = digest(protocol)
    return protocol


def _verify_lock(lock):
    if not isinstance(lock, dict) or lock.get("schema_version") != LOCK_SCHEMA:
        raise ContractError("invalid AX-ARENA lock")
    claimed = lock.get("sha256")
    unsigned = {key: value for key, value in lock.items() if key != "sha256"}
    if claimed != digest(unsigned):
        raise ContractError("AX-ARENA lock digest mismatch")
    if lock.get("schedule_sha256") != digest(lock.get("schedule")):
        raise ContractError("AX-ARENA schedule digest mismatch")
    if lock.get("allow_provider_fallback") is not False:
        raise ContractError("AX-ARENA fallback policy changed")
    return lock


def _read_traces(path: Path):
    traces = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            traces.append(AgentEvaluationTrace.from_payload(strict_json(line)))
    return traces


def _aggregate(rows):
    successes = sum(row["success"] for row in rows)
    tool_calls = sum(row["signals"].tool_calls for row in rows)
    hallucinations = sum(row["signals"].tool_hallucinations for row in rows)
    corrections = sum(row["signals"].corrections for row in rows)
    landed = sum(row["signals"].corrections_landed for row in rows)
    failures = sum(row["signals"].bash_failure_episodes for row in rows)
    recovered = sum(row["signals"].bash_recovered_episodes for row in rows)
    recovery_calls = sum(row["signals"].bash_recovery_calls_total for row in rows)
    usage_complete = all(
        type(row["usage"].get("prompt_tokens")) is int
        and type(row["usage"].get("completion_tokens")) is int
        for row in rows
    )
    cost_values = [row["usage"].get("cost_usd") for row in rows]
    cost_complete = all(type(value) in (int, float) and math.isfinite(value) and value >= 0 for value in cost_values)
    return {
        "runs": len(rows),
        "successful": successes,
        "success_rate": successes / len(rows),
        "confirmed_success_rate": (
            sum(row["signals"].confirmed_success is True for row in rows)
            / sum(row["signals"].confirmed_success is not None for row in rows)
            if any(row["signals"].confirmed_success is not None for row in rows) else None
        ),
        "tool_calls": tool_calls,
        "tool_hallucinations": hallucinations,
        "tool_hallucination_rate": hallucinations / tool_calls if tool_calls else None,
        "corrections": corrections,
        "corrections_landed": landed,
        "steerability": landed / corrections if corrections else None,
        "bash_failure_episodes": failures,
        "bash_recovered_episodes": recovered,
        "bash_recovery_rate": recovered / failures if failures else None,
        "bash_recovery_mean_calls": recovery_calls / recovered if recovered else None,
        "input_tokens": sum(row["usage"].get("prompt_tokens", 0) for row in rows) if usage_complete else None,
        "output_tokens": sum(row["usage"].get("completion_tokens", 0) for row in rows) if usage_complete else None,
        "usage_complete": usage_complete,
        "cost_usd_total": sum(cost_values) if cost_complete else None,
        "cost_complete": cost_complete,
    }


def _cluster_bootstrap(task_groups, seed, samples=10000):
    if not task_groups:
        return None
    keys = sorted(task_groups)
    rng = random.Random(seed)
    means = []
    for _ in range(samples):
        selected = [rng.choice(keys) for _ in keys]
        values = [value for key in selected for value in task_groups[key]]
        means.append(statistics.mean(values))
    return [_percentile(means, 0.025), _percentile(means, 0.975)]


def score_protocol(lock, traces):
    lock = _verify_lock(lock)
    expected = {job["observation_id"]: job for job in lock["schedule"]}
    seen = {}
    rows = []

    for trace in traces:
        if trace.observation_id in seen:
            raise ContractError("duplicate AX-ARENA observation")
        job = expected.get(trace.observation_id)
        if job is None:
            raise ContractError("unexpected AX-ARENA observation")
        for field in ("experiment_id", "task_id", "condition", "model"):
            if getattr(trace, field) != job[field]:
                raise ContractError("AX-ARENA trace does not match frozen schedule")
        verdict = trace.verdict
        if type(verdict.get("verified_task_success")) is not bool:
            raise ContractError("AX-ARENA trace requires verified_task_success")
        if lock["evidence_level"] == "live_model":
            provider = trace.provider_metadata
            if provider.get("provider") != "arena" or provider.get("fallback_used") is not False:
                raise ContractError("live AX-ARENA trace lacks single-provider Arena provenance")
        signals = extract_arena_aligned_signals(trace)
        row = {
            "trace": trace,
            "job": job,
            "success": verdict["verified_task_success"],
            "signals": signals,
            "usage": trace.usage,
        }
        seen[trace.observation_id] = row
        rows.append(row)

    missing = sorted(set(expected) - set(seen))
    if missing:
        raise ContractError("AX-ARENA observations are incomplete")

    summary = {}
    for model in lock["models"]:
        summary[model] = {}
        for condition in lock["conditions"]:
            group = [row for row in rows if row["trace"].model == model and row["trace"].condition == condition]
            summary[model][condition] = _aggregate(group)

    paired = []
    for model_index, model in enumerate(lock["models"]):
        pairs = {}
        for row in rows:
            if row["trace"].model != model:
                continue
            key = (row["trace"].task_id, row["job"]["repeat"])
            pairs.setdefault(key, {})[row["trace"].condition] = row
        task_groups = {}
        for (task_id, repeat), pair in pairs.items():
            if set(pair) != {"control", "residual"}:
                raise ContractError("AX-ARENA paired observation missing condition")
            delta = int(pair["residual"]["success"]) - int(pair["control"]["success"])
            task_groups.setdefault(task_id, []).append(delta)
        differences = [value for values in task_groups.values() for value in values]
        paired.append({
            "model": model,
            "pairs": len(differences),
            "tasks": len(task_groups),
            "residual_minus_control_success_rate": statistics.mean(differences),
            "task_cluster_bootstrap_95_interval": _cluster_bootstrap(
                task_groups, lock["seed"] + model_index
            ),
            "interpretation": "Descriptive paired harness-effect estimate; no automatic superiority claim.",
        })

    report = {
        "schema_version": REPORT_SCHEMA,
        "protocol_sha256": lock["sha256"],
        "experiment_id": lock["experiment_id"],
        "evidence_level": lock["evidence_level"],
        "methodology_notice": (
            "Arena-aligned local metrics over RESIDUAL evidence. This is not an official Arena score or leaderboard result."
        ),
        "summary": summary,
        "paired_success_comparisons": paired,
        "trace_sha256": sorted(trace.sha256 for trace in traces),
        "limitations": lock["limitations"],
    }
    report["sha256"] = digest(report)
    return report


def _models():
    provider = DEFAULT_REGISTRY.get("arena")
    return provider.list_models()


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("models", help="List Arena API model IDs using ARENA_API_KEY")

    freeze = sub.add_parser("freeze", help="Freeze an AX-ARENA protocol before outcomes are observed")
    freeze.add_argument("--manifest", required=True, type=Path)
    freeze.add_argument("--model", action="append", required=True, dest="models")
    freeze.add_argument("--output", required=True, type=Path)

    score = sub.add_parser("score", help="Validate complete traces and build an Arena-aligned report")
    score.add_argument("--lock", required=True, type=Path)
    score.add_argument("--traces", required=True, type=Path)
    score.add_argument("--output", required=True, type=Path)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "models":
            print(json.dumps({"provider": "arena", "models": _models()}, indent=2))
            return 0
        if args.command == "freeze":
            manifest = strict_json(args.manifest.read_text(encoding="utf-8"))
            protocol = freeze_protocol(manifest, args.models, manifest_path=args.manifest.resolve())
            _write_json(args.output, protocol, exclusive=True)
            print(json.dumps({
                "experiment_id": protocol["experiment_id"],
                "scheduled_runs": len(protocol["schedule"]),
                "protocol_sha256": protocol["sha256"],
                "output": str(args.output),
            }, indent=2))
            return 0
        lock = strict_json(args.lock.read_text(encoding="utf-8"))
        report = score_protocol(lock, _read_traces(args.traces))
        _write_json(args.output, report)
        print(json.dumps({
            "experiment_id": report["experiment_id"],
            "report_sha256": report["sha256"],
            "output": str(args.output),
        }, indent=2))
        return 0
    except (ContractError, ProviderError, OSError, ValueError, TypeError, KeyError):
        print("AX-ARENA failed: validate credentials, frozen protocol, trace completeness, and evidence fields.", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
