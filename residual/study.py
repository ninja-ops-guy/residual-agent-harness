"""Frozen, independently graded controller experiments with durable call receipts.

This evaluates the original obligation harness. It does not certify station
integration, model reasoning, or arbitrary task decomposition.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import random
import statistics
import sys
import time
import urllib.parse
from dataclasses import asdict
from pathlib import Path

from .config import build_harness, load_config
from .core import ContractError, Task, canonical, digest, positive_int, strict_json
from .engine import MODES, Limits
from .providers import Provider, ProviderError, Reply
from .storage import verify_ledger
from .study_tasks import grade, validate_grader


DEFAULT_MODES = ["local_only", "full_cloud", "cascade", "residual_fixed", "residual", "no_pull", "no_feedback", "no_solvers"]
ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def append_json(path, value):
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(canonical(value) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def finite_nonnegative(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ContractError("invalid " + name)
    return value


def sources():
    # Pin the implementations of checkers, packet builders, providers and graders.
    return {p.relative_to(ROOT).as_posix(): digest(p.read_text(encoding="utf-8"))
            for package in ("residual", "ai_providers", "observation_layer")
            for p in sorted((ROOT / package).rglob("*.py"))}


def load_suite(path):
    path = Path(path).resolve()
    data = strict_json(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"schema_version", "name", "evidence_level", "cases"}:
        raise ContractError("invalid study suite")
    if data["schema_version"] != "residual.study-suite.v1" or data["evidence_level"] not in {"development_fixture", "independently_authored"}:
        raise ContractError("invalid study evidence declaration")
    if not isinstance(data["cases"], list) or not 1 <= len(data["cases"]) <= 1000:
        raise ContractError("invalid case count")
    families, ids, task_ids, fingerprints = {}, set(), set(), set()
    loaded = []
    for entry in data["cases"]:
        if not isinstance(entry, dict) or set(entry) != {"id", "family", "split", "task", "grader"}:
            raise ContractError("invalid case entry")
        if any(not isinstance(entry[k], str) or not entry[k] for k in entry):
            raise ContractError("case fields must be nonempty strings")
        if entry["split"] not in {"development", "evaluation"} or entry["id"] in ids:
            raise ContractError("invalid split or duplicate case")
        if families.setdefault(entry["family"], entry["split"]) != entry["split"]:
            raise ContractError("family appears in both splits")
        ids.add(entry["id"])
        paths = [(path.parent / entry[k]).resolve() for k in ("task", "grader")]
        if any(not p.is_relative_to(path.parent) for p in paths):
            raise ContractError("case path escapes suite directory")
        task = Task.load(paths[0])
        raw_task = strict_json(paths[0].read_text(encoding="utf-8"))
        if any("path" in a and (paths[0].parent / a["path"]).resolve() == paths[1]
               for a in raw_task.get("artifacts", [])):
            raise ContractError("grader file cannot be a task artifact")
        grader = validate_grader(strict_json(paths[1].read_text(encoding="utf-8")))
        # Renaming a case must not evade duplicate-task checks across splits.
        task_content = asdict(task)
        task_content.pop("id")
        fingerprint = digest(task_content)
        if task.id in task_ids or fingerprint in fingerprints:
            raise ContractError("duplicate task identity or content")
        task_ids.add(task.id)
        fingerprints.add(fingerprint)
        targets = set(grader["values"]) if grader["kind"] == "exact" else (
            {grader["obligation"]} if grader["obligation"] is not None else set(grader["constraints"]["domains"]))
        if not targets <= task.by_id.keys():
            raise ContractError("grader references unknown obligations")
        loaded.append((entry, task, grader))
    return data, loaded


def validate_config(config):
    # The normal provider interface uses environment references. Never persist keys.
    def visit(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key.lower() in {"api_key", "password", "secret", "token", "authorization", "headers"}:
                    raise ContractError("study config must use environment references")
                if key.endswith("url") and isinstance(child, str):
                    url = urllib.parse.urlsplit(child)
                    if url.username or url.password or url.query or url.fragment:
                        raise ContractError("study URLs cannot contain credentials, queries or fragments")
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(config)
    if set(config) - {"local", "expert", "limits", "plugins", "cache"}:
        raise ContractError("unknown config sections")
    # External plugin source/dependencies need a separate reproducibility contract.
    if any(p != "residual.study_tasks:register" for p in config.get("plugins", [])):
        raise ContractError("locked study currently supports bundled plugins only")
    Limits(**config.get("limits", {}))
    if not config.get("local") or not config.get("expert") or any(config[r].get("kind") == "disabled" for r in ("local", "expert")):
        raise ContractError("comparative study requires both configured tiers")


def make_protocol(suite_path, config, modes, repeats, seed, max_calls, max_remote_bytes,
                  local_cost_per_hour=None, split="evaluation"):
    validate_config(config)
    for value, name in ((repeats, "repeats"), (max_calls, "max_calls"), (max_remote_bytes, "max_remote_bytes")):
        positive_int(value, name)
    positive_int(seed, "seed", allow_zero=True)
    if not isinstance(modes, list) or not modes or len(modes) != len(set(modes)) or set(modes) - MODES:
        raise ContractError("invalid or duplicate modes")
    if split not in {"development", "evaluation"}:
        raise ContractError("invalid study split")
    if local_cost_per_hour is not None:
        finite_nonnegative(local_cost_per_hour, "local cost rate")
    suite, cases = load_suite(suite_path)
    selected = [(e, t, g) for e, t, g in cases if e["split"] == split]
    if not selected or len(selected) * repeats * len(modes) > 100000:
        raise ContractError("empty or oversized study schedule")
    config = strict_json(canonical(config))
    config["cache"] = {"enabled": False}
    protocol = {"schema_version": "residual.study-protocol.v1", "suite_name": suite["name"],
        "suite_sha256": digest(suite), "evidence_level": suite["evidence_level"],
        "split": split, "config": config, "source_hashes": sources(),
        "cases": [{"id": e["id"], "family": e["family"], "task_sha256": digest(asdict(t)), "grader_sha256": digest(g)} for e, t, g in selected],
        "modes": modes, "repeats": repeats, "seed": seed,
        "max_total_calls": max_calls, "max_total_remote_bytes": max_remote_bytes,
        "local_cost_per_hour_usd": local_cost_per_hour, "cache_policy": "disabled",
        "cost_scope": "Configured inference prices plus optional modeled local host occupancy; excludes engineering effort and unreported upstream charges."}
    protocol["sha256"] = digest(protocol)
    return protocol


def schedule(protocol):
    rng = random.Random(protocol["seed"])
    blocks = [(case, repeat) for repeat in range(protocol["repeats"]) for case in protocol["cases"]]
    rng.shuffle(blocks)
    rows = []
    for case, repeat in blocks:
        modes = list(protocol["modes"])
        rng.shuffle(modes)
        for mode in modes:
            rows.append({"run_id": f"run-{len(rows):06d}", "case_id": case["id"], "family": case["family"],
                         "repeat": repeat, "mode": mode})
    return rows


class StudyBudget:
    def __init__(self, max_calls, max_remote_bytes, journal):
        self.max_calls, self.max_remote_bytes = max_calls, max_remote_bytes
        self.calls, self.remote_bytes, self.exhausted = 0, 0, False
        self.journal = journal

    def reserve(self, run_id, role, provider, size):
        remote = size if provider.placement == "remote" else 0
        if self.exhausted or self.calls >= self.max_calls or self.remote_bytes + remote > self.max_remote_bytes:
            self.exhausted = True
            raise ProviderError("study_budget_exhausted")
        self.calls += 1
        self.remote_bytes += remote
        event = {"event": "reserved", "call_id": self.calls, "run_id": run_id, "role": role,
                 "provider": provider.name, "placement": provider.placement, "request_bytes": size}
        append_json(self.journal, event)  # Persist before transport; never refund errors.
        return event


class MeteredProvider(Provider):
    def __init__(self, provider, budget, run_id, role):
        self.provider, self.budget, self.run_id, self.role = provider, budget, run_id, role
        self.name, self.placement, self.prices = provider.name, provider.placement, provider.prices
        self.records = []

    def wire_size(self, packet, max_output_tokens):
        return self.provider.wire_size(packet, max_output_tokens)

    def generate(self, packet, max_output_tokens):
        record = self.budget.reserve(self.run_id, self.role, self.provider, self.wire_size(packet, max_output_tokens))
        record = {**record, "event": "finished", "cost_usd": None, "usage": None, "error": None}
        self.records.append(record)
        start = time.monotonic()
        try:
            reply = self.provider.generate(packet, max_output_tokens)
            if not isinstance(reply, Reply):
                raise ProviderError("invalid_reply")
            record["usage"] = asdict(reply.usage)
            record["cost_usd"] = self.prices.cost(reply.usage) if self.prices else (
                0.0 if self.placement == "local" else None)
            return reply
        except Exception:
            record["error"] = "provider_call_failed"
            raise
        finally:
            record["elapsed_ms"] = (time.monotonic() - start) * 1000
            append_json(self.budget.journal, record)


def run_study(lock_path, output):
    lock_path, output = Path(lock_path).resolve(), Path(output).resolve()
    lock = strict_json(lock_path.read_text(encoding="utf-8"))
    p = lock["protocol"]
    if p["sha256"] != digest({k: v for k, v in p.items() if k != "sha256"}):
        raise ContractError("protocol digest mismatch")
    suite_path = (lock_path.parent / lock["suite"]).resolve()
    expected = make_protocol(suite_path, p["config"], p["modes"], p["repeats"], p["seed"],
                             p["max_total_calls"], p["max_total_remote_bytes"], p["local_cost_per_hour_usd"], p["split"])
    if expected != p:
        raise ContractError("suite, grader, or implementation changed after freeze")
    _, cases = load_suite(suite_path)
    lookup = {e["id"]: (task, grader) for e, task, grader in cases}
    # Provider construction validates credentials/configuration before making a run directory.
    probe = build_harness(p["config"], disable_cache=True)
    if any(task_o.check not in probe.registry.checks for task, _ in lookup.values() for task_o in task.obligations):
        raise ContractError("unregistered study check")
    output.mkdir(parents=True, exist_ok=False)
    jobs = schedule(p)
    write_json(output / "protocol.json", p)
    write_json(output / "schedule.json", jobs)
    write_json(output / "environment.json", {"python": platform.python_version(), "platform": platform.platform(),
        "started_at_unix": time.time(), "simulation_configured": any(p["config"][r]["kind"] in {"demo", "study_fixture"} for r in ("local", "expert"))})
    budget = StudyBudget(p["max_total_calls"], p["max_total_remote_bytes"], output / "calls.jsonl")
    for job in jobs:
        if budget.exhausted:
            append_json(output / "runs.jsonl", {**job, "status": "not_run_budget", "controller_success": False, "success": False})
            continue
        harness = build_harness(p["config"], mode=job["mode"], disable_cache=True)
        local = MeteredProvider(harness.local, budget, job["run_id"], "local")
        expert = MeteredProvider(harness.expert, budget, job["run_id"], "expert")
        harness.local, harness.expert = local, expert
        task, grader = lookup[job["case_id"]]
        append_json(output / "lifecycle.jsonl", {"event": "run_started", **job})
        started = time.monotonic()
        row = {**job, "status": "error", "controller_success": False, "success": False}
        try:
            result = harness.run(task)
            grading_started = time.monotonic()
            verdict = grade(result["values"], grader)
            row.update(status="completed", controller_success=result["success"],
                       success=bool(result["success"] and verdict["pass"]), grade=verdict,
                       grading_elapsed_ms=(time.monotonic() - grading_started) * 1000,
                       metrics=result["metrics"], result_sha256=digest(result))
            # Separate files; grader inputs are never appended to the harness trace.
            run_dir = output / job["run_id"]
            write_json(run_dir / "result.json", result)
            harness.ledger.write(run_dir / "trace.jsonl")
        except Exception:
            # Do not drop the run or serialize exception bodies containing secrets.
            row["error"] = "run_or_grader_failed"
        row["elapsed_ms"] = (time.monotonic() - started) * 1000
        row["budget_exhausted"] = budget.exhausted
        row["transport_calls"] = len(local.records) + len(expert.records)
        append_json(output / "runs.jsonl", row)
        append_json(output / "lifecycle.jsonl", {"event": "run_finished", "run_id": job["run_id"]})
    return report_study(output)


def read_jsonl(path):
    if not path.exists():
        return []
    # A torn final write is not silently discarded; preserve the journal for diagnosis.
    return [strict_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def percentile(values, q):
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * q
    low = int(position)
    return values[low] + (values[min(low + 1, len(values) - 1)] - values[low]) * (position - low)


def summarize_rows(rows, calls, protocol, simulation=False):
    summary = []
    for mode in protocol["modes"]:
        group = [r for r in rows if r["mode"] == mode]
        ids = {r["run_id"] for r in group}
        used = [c for c in calls if c["run_id"] in ids]
        successful = sum(r["success"] for r in group)
        completed = all(r["status"] == "completed" and not r.get("budget_exhausted") for r in group)
        elapsed = [r["elapsed_ms"] for r in group if "elapsed_ms" in r]
        known = [c["cost_usd"] for c in used if c.get("cost_usd") is not None]
        inference = sum(known) if len(known) == len(used) and completed else None
        local_rate = protocol["local_cost_per_hour_usd"]
        local_cost = sum(elapsed) / 3_600_000 * local_rate if local_rate is not None and completed else None
        # Simulation never becomes a dollar result, including zero-call fixtures.
        total = inference + local_cost if not simulation and inference is not None and local_cost is not None else None
        usage_complete = not simulation and completed and all(
            isinstance(c.get("usage"), dict) and c["usage"].get("source") == "reported"
            and c["usage"].get("input_tokens") is not None and c["usage"].get("output_tokens") is not None for c in used)
        false_accepts = sum(r["controller_success"] and not r["success"] for r in group)
        verification_ms = sum(r.get("metrics", {}).get("verification_elapsed_ms", 0) for r in group)
        solver_ms = sum(r.get("metrics", {}).get("solver_elapsed_ms", 0) for r in group)
        grading_ms = sum(r.get("grading_elapsed_ms", 0) for r in group)
        provider_ms = sum(c.get("elapsed_ms", 0) for c in used)
        by_placement = {}
        for placement in ("local", "remote"):
            subset = [c for c in used if c["placement"] == placement]
            reported = [(c.get("usage") or {}) for c in subset if (c.get("usage") or {}).get("source") == "reported"]
            by_placement[placement] = {"calls": len(subset),
                "input_tokens_reported": sum(u.get("input_tokens") or 0 for u in reported),
                "output_tokens_reported": sum(u.get("output_tokens") or 0 for u in reported),
                "cached_input_tokens_reported": sum(u.get("cached_input_tokens") or 0 for u in reported),
                "cache_write_input_tokens_reported": sum(u.get("cache_write_input_tokens") or 0 for u in reported),
                "usage_complete": not simulation and completed and len(reported) == len(subset)
                    and all(u.get("input_tokens") is not None and u.get("output_tokens") is not None for u in reported)}
        summary.append({"mode": mode, "scheduled": len(group), "completed": sum(r["status"] == "completed" for r in group),
            "successful": successful, "success_rate": successful / len(group),
            "controller_successful": sum(r["controller_success"] for r in group), "false_acceptances": false_accepts,
            "complete": completed, "calls": len(used), "calls_without_usage": sum(not c.get("usage") or c["usage"].get("source") != "reported" or c["usage"].get("input_tokens") is None or c["usage"].get("output_tokens") is None for c in used),
            "usage_complete": usage_complete, "remote_request_bytes": sum(c["request_bytes"] for c in used if c["placement"] == "remote"),
            "usage_by_placement": by_placement,
            "input_tokens_reported": sum(c["usage"].get("input_tokens") or 0 for c in used if (c.get("usage") or {}).get("source") == "reported"),
            "output_tokens_reported": sum(c["usage"].get("output_tokens") or 0 for c in used if (c.get("usage") or {}).get("source") == "reported"),
            "cached_input_tokens_reported": sum(c["usage"].get("cached_input_tokens") or 0 for c in used if (c.get("usage") or {}).get("source") == "reported"),
            "known_inference_cost_subtotal_usd": sum(known), "inference_cost_usd": None if simulation else inference,
            "modeled_local_cost_usd": None if simulation else local_cost, "total_cost_usd": total,
            "total_cost_per_success_usd": total / successful if total is not None and successful else None,
            "median_elapsed_ms": statistics.median(elapsed) if elapsed else None, "p95_elapsed_ms": percentile(elapsed, .95),
            "verification_elapsed_ms": verification_ms, "solver_elapsed_ms": solver_ms,
            "grading_elapsed_ms": grading_ms, "provider_elapsed_ms": provider_ms,
            "other_host_elapsed_ms": max(0, sum(elapsed) - verification_ms - solver_ms - grading_ms - provider_ms)})
    return summary


def paired_intervals(rows, protocol):
    """Family-cluster bootstrap: repeated trials are not independent tasks."""
    if "residual" not in protocol["modes"]:
        return []
    by_key = {(r["case_id"], r["repeat"], r["mode"]): r for r in rows}
    result = []
    for mode in protocol["modes"]:
        if mode == "residual":
            continue
        families = {}
        for row in rows:
            if row["mode"] == "residual":
                other = by_key[(row["case_id"], row["repeat"], mode)]
                families.setdefault(row["family"], []).append(int(row["success"]) - int(other["success"]))
        groups = list(families.values())
        rng = random.Random(protocol["seed"])
        samples = []
        if len(groups) >= 2:
            for _ in range(2000):
                sample = [value for _ in groups for value in rng.choice(groups)]
                samples.append(statistics.mean(sample))
        differences = [v for group in groups for v in group]
        result.append({"baseline": mode, "pairs": len(differences), "families": len(groups),
            "success_rate_delta": statistics.mean(differences),
            "family_bootstrap_95_interval": [percentile(samples, .025), percentile(samples, .975)] if samples else None,
            "interpretation": "Descriptive paired estimate; small family counts, selected suites and repeated inspection limit generalization. No automatic equivalence or superiority claim."})
    return result


def report_study(output):
    output = Path(output)
    p = strict_json((output / "protocol.json").read_text(encoding="utf-8"))
    if p["sha256"] != digest({k: v for k, v in p.items() if k != "sha256"}):
        raise ContractError("report protocol digest mismatch")
    jobs = strict_json((output / "schedule.json").read_text(encoding="utf-8"))
    if jobs != schedule(p):
        raise ContractError("schedule differs from frozen protocol")
    records = read_jsonl(output / "runs.jsonl")
    by_id = {}
    expected = {j["run_id"]: j for j in jobs}
    for row in records:
        if row["run_id"] in by_id or row["run_id"] not in expected or any(row[k] != v for k, v in expected[row["run_id"]].items()):
            raise ContractError("duplicate or mismatched run receipt")
        by_id[row["run_id"]] = row
        if row["status"] == "completed":
            run_dir = output / row["run_id"]
            value = strict_json((run_dir / "result.json").read_text(encoding="utf-8"))
            if digest(value) != row["result_sha256"] or value["success"] != row["controller_success"]:
                raise ContractError("run result differs from receipt")
            if row["success"] != bool(row["controller_success"] and row["grade"]["pass"]):
                raise ContractError("independent outcome differs from receipt")
            trace = verify_ledger(run_dir / "trace.jsonl")
            terminal = read_jsonl(run_dir / "trace.jsonl")[-1]
            if trace["root"] != value["trace_root"] or terminal["data"]["result_sha256"] != digest({k: v for k, v in value.items() if k != "trace_root"}):
                raise ContractError("run trace does not bind result")
    rows = [by_id.get(j["run_id"], {**j, "status": "not_recorded", "controller_success": False, "success": False}) for j in jobs]
    reserved, finished = {}, {}
    for call in read_jsonl(output / "calls.jsonl"):
        target = reserved if call["event"] == "reserved" else finished if call["event"] == "finished" else None
        if target is None or call["call_id"] in target or call["run_id"] not in expected:
            raise ContractError("invalid call journal")
        target[call["call_id"]] = call
    if set(finished) - reserved.keys():
        raise ContractError("unreserved finished call")
    calls = []
    for cid, reservation in reserved.items():
        completion = finished.get(cid)
        if completion and any(completion[k] != v for k, v in reservation.items() if k != "event"):
            raise ContractError("call reservation mismatch")
        calls.append(completion or {**reservation, "usage": None, "cost_usd": None, "error": "completion_missing"})
    for row in records:
        if sum(c["run_id"] == row["run_id"] for c in calls) != row.get("transport_calls", 0):
            raise ContractError("call journal is incomplete for a recorded run")
    environment = strict_json((output / "environment.json").read_text(encoding="utf-8"))
    simulation = any(p["config"][r]["kind"] in {"demo", "study_fixture"} for r in ("local", "expert")) or any((c.get("usage") or {}).get("source") == "simulation" for c in calls)
    summary = summarize_rows(rows, calls, p, simulation)
    report = {"schema_version": "residual.study-report.v1", "protocol_sha256": p["sha256"],
        "simulation": simulation, "evidence_level": p["evidence_level"], "split": p["split"],
        "comparison_complete": all(s["complete"] for s in summary) and len(reserved) == len(finished),
        "environment": environment,
        "scheduled_runs": len(jobs), "recorded_runs": len(records), "reserved_calls": len(calls),
        "missing_call_completions": len(reserved) - len(finished), "summary": summary,
        "paired_success_comparisons": paired_intervals(rows, p), "runs": rows,
        "limitations": ["Public bundled tasks are development fixtures; an evaluation split is not independent external validation.",
            "A frozen protocol prevents silent input/code changes; it is not a signature or tamper-proof execution attestation.",
            "Hidden grader inputs are excluded from model packets; trusted in-process plugins and repository access are outside this isolation boundary.",
            "The order seed controls scheduling, not provider sampling or reproducible model outputs.",
            "Costs use configured prices, include failures, and remain unknown when accounting is incomplete; they are not invoice reconciliation.",
            "Local cost is modeled host occupancy including I/O wait. Local placements without inference prices have no separate API fee; their resource cost still requires the local rate. Engineering effort, actual energy and upstream gateway work are not measured.",
            "Global reservations bound top-level provider calls and request bytes, not dollars, hidden gateway attempts or hung executors.",
            "No observed success rate, confidence interval, or smaller byte count automatically establishes matched quality or cost superiority."]}
    report["sha256"] = digest(report)
    write_json(output / "report.json", report)
    lines = ["# RESIDUAL controlled evaluation", "",
        "Scripted fixtures — no live quality or savings claim." if simulation else "Configured provider experiment — interpret within the frozen suite and accounting scope.", "",
        "| Mode | Independent successes / scheduled | False acceptances | Calls | Total cost / success | Complete |",
        "| --- | ---: | ---: | ---: | ---: | --- |"]
    for s in summary:
        cost = "unknown" if s["total_cost_per_success_usd"] is None else f"${s['total_cost_per_success_usd']:.6f}"
        lines.append(f"| {s['mode']} | {s['successful']}/{s['scheduled']} | {s['false_acceptances']} | {s['calls']} | {cost} | {s['complete']} |")
    lines += ["", *["- " + note for note in report["limitations"]], ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Freeze and run an independently graded RESIDUAL study")
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--suite", required=True)
    freeze.add_argument("--config", required=True)
    freeze.add_argument("--output", required=True)
    freeze.add_argument("--split", choices=["development", "evaluation"], default="evaluation")
    freeze.add_argument("--modes", nargs="+", choices=sorted(MODES), default=DEFAULT_MODES)
    freeze.add_argument("--repeats", type=int, default=3)
    freeze.add_argument("--seed", type=int, default=42)
    freeze.add_argument("--max-total-calls", type=int, default=2000)
    freeze.add_argument("--max-total-remote-bytes", type=int, default=20_000_000)
    freeze.add_argument("--local-cost-per-hour", type=float)
    run = sub.add_parser("run")
    run.add_argument("--lock", required=True)
    run.add_argument("--output", required=True)
    report = sub.add_parser("report")
    report.add_argument("output")
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            output = Path(args.output).resolve()
            protocol = make_protocol(args.suite, load_config(args.config), args.modes, args.repeats, args.seed,
                args.max_total_calls, args.max_total_remote_bytes, args.local_cost_per_hour, args.split)
            write_json(output, {"suite": os.path.relpath(Path(args.suite).resolve(), output.parent), "protocol": protocol}, exclusive=True)
            print(f"Frozen {len(protocol['cases'])} cases; {len(schedule(protocol))} runs; protocol {protocol['sha256']}")
            return 0
        result = run_study(args.lock, args.output) if args.command == "run" else report_study(args.output)
        print(f"Recorded {result['recorded_runs']}/{result['scheduled_runs']} runs; simulation={result['simulation']}")
        return 0 if all(s["complete"] for s in result["summary"]) and not result["missing_call_completions"] else 2
    except (ContractError, OSError, ValueError, TypeError, KeyError, ImportError, AttributeError):
        print("residual study: protocol, configuration, or result validation failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
