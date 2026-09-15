"""Offline descriptive reconstruction from versioned, retained experiment bundles.

No plugin loading, provider calls, code execution, receipt signing or network IO.
Hashes check content consistency; an unpinned manifest is not an authenticity proof.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

SCHEMA = "residual.experiment-bundle.v1"
REPORT_SCHEMA = "residual.reproduction.v1"
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_BUNDLE_BYTES = 128 * 1024 * 1024
MAX_ARTIFACTS = 4096
MAX_CELLS = 100_000
MAX_PARETO_POINTS = 256
CORE_PATHS = {
    "environment": "metadata/environment.json",
    "git": "metadata/git.json",
    "workload": "metadata/workload.json",
    "models": "metadata/models.json",
    "prompts": "metadata/prompts.json",
    "protocol": "metadata/protocol.json",
    "cells": "records/cells.jsonl",
    "usage": "records/usage.jsonl",
    "timing": "records/timing.jsonl",
    "failures": "records/failures.jsonl",
    "receipts": "evidence/receipts.jsonl",
    "scheduler": "evidence/scheduler.jsonl",
    "verifier": "evidence/verifier.jsonl",
    "stdout": "streams/stdout.bin",
    "stderr": "streams/stderr.bin",
    "reproduction": "reproduce.txt",
}
PAIR_KEYS = {"cell_id", "family_id", "task_id", "repeat_index", "configuration", "model_class", "topology"}
EXECUTION = {"COMPLETED", "TIMEOUT", "CRASH", "ERROR", "UNKNOWN", "NOT_RUN"}
VERDICTS = {"PASS", "FAIL", "UNKNOWN", "ERROR", "SKIPPED"}
CORRECTNESS = {"CORRECT", "INCORRECT", "UNKNOWN", "NOT_GRADED"}


class ReproductionError(ValueError):
    """Unusable or internally inconsistent retained evidence."""


def _require(condition, message):
    if not condition:
        raise ReproductionError(message)


def _keys(value, expected, label):
    _require(isinstance(value, dict) and set(value) == set(expected), f"{label}: incorrect fields")


def _string(value, label):
    _require(isinstance(value, str) and bool(value.strip()) and len(value) <= 4096,
             f"{label}: nonempty bounded string required")


def _identifier(value, label):
    _require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value) is not None,
             f"{label}: invalid identifier")


def _hash(value, label):
    _require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
             f"{label}: lowercase SHA-256 required")


def _number(value, label, *, integer=False, nullable=False):
    if value is None and nullable:
        return
    _require(type(value) is int if integer else type(value) in (int, float), f"{label}: invalid number")
    _require(value >= 0 and math.isfinite(value), f"{label}: finite nonnegative number required")


def _path(value):
    _require(isinstance(value, str) and value and "\\" not in value and "\x00" not in value,
             "invalid artifact path")
    p = PurePosixPath(value)
    _require(not p.is_absolute() and str(p) == value and all(x not in {".", ".."} for x in p.parts),
             f"unsafe artifact path: {value!r}")
    _require(all(len(x.encode("utf-8")) <= 255 for x in p.parts) and len(value) <= 4096,
             "artifact path too long")
    return p.parts


def _no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _finite_float(text):
    value = float(text)
    _require(math.isfinite(value), "nonfinite JSON number")
    return value


def _json(raw, label):
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        return json.loads(text, object_pairs_hook=_no_duplicates, parse_float=_finite_float,
                          parse_constant=lambda x: (_ for _ in ()).throw(ReproductionError(f"nonfinite JSON: {x}")))
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise ReproductionError(f"{label}: invalid JSON ({exc})") from exc


def _jsonl(raw, label):
    if not raw:
        return []
    _require(raw.endswith(b"\n"), f"{label}: torn JSONL final record")
    records = [_json(line, label) for line in raw.splitlines()]
    _require(all(isinstance(row, dict) for row in records), f"{label}: object records required")
    return records


@contextmanager
def _directory(path):
    """Open every path component without following symlinks (POSIX only)."""
    _require(os.name == "posix" and hasattr(os, "O_NOFOLLOW"), "safe replay requires POSIX O_NOFOLLOW")
    absolute = os.path.abspath(os.fspath(path))
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in Path(absolute).parts[1:]:
            new_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = new_fd
        yield fd
    finally:
        os.close(fd)


def _read(root_fd, relative):
    parts = _path(relative)
    parent = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            before = os.fstat(fd)
            _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
                     f"{relative}: single-link regular file required")
            _require(before.st_size <= MAX_FILE_BYTES, f"{relative}: artifact exceeds size limit")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                data = stream.read(MAX_FILE_BYTES + 1)
            after = os.fstat(fd)
            _require(len(data) == before.st_size == after.st_size and
                     before.st_mtime_ns == after.st_mtime_ns and before.st_ctime_ns == after.st_ctime_ns,
                     f"{relative}: artifact changed while reading")
            return data
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def _refs(row, artifacts, label):
    refs = row["source_refs"]
    _require(isinstance(refs, list) and all(isinstance(ref, str) for ref in refs),
             f"{label}: source_refs must be strings")
    _require(len(refs) == len(set(refs)), f"{label}: duplicate source_refs")
    for path in refs:
        _path(path)
        _require(path in artifacts, f"{label}: unretained source reference {path}")


def _validate_manifest(manifest, run_id):
    _keys(manifest, {"schema_version", "run_id", "evidence_mode", "expected_cells", "artifacts", "source_coverage"}, "manifest")
    _require(manifest["schema_version"] == SCHEMA and manifest["run_id"] == run_id, "manifest schema/run mismatch")
    _require(manifest["evidence_mode"] in {"synthetic", "measured"}, "invalid evidence_mode")
    cells = manifest["expected_cells"]
    _require(isinstance(cells, list) and 0 < len(cells) <= MAX_CELLS, "expected_cells must be nonempty and bounded")
    ids = set()
    pairs = set()
    for cell in cells:
        _keys(cell, PAIR_KEYS, "expected cell")
        for name in PAIR_KEYS - {"repeat_index"}:
            _identifier(cell[name], name)
        _number(cell["repeat_index"], "repeat_index", integer=True)
        _require(cell["cell_id"] not in ids, "duplicate expected cell")
        pair = tuple(cell[k] for k in sorted(PAIR_KEYS - {"cell_id"}))
        _require(pair not in pairs, "duplicate pairing tuple")
        ids.add(cell["cell_id"])
        pairs.add(pair)
    artifacts = manifest["artifacts"]
    _require(isinstance(artifacts, list) and len(CORE_PATHS) <= len(artifacts) <= MAX_ARTIFACTS,
             "invalid artifact count")
    by_path = {}
    total = 0
    for artifact in artifacts:
        _keys(artifact, {"path", "sha256", "bytes"}, "artifact")
        path = artifact["path"]
        _path(path)
        _require(path in CORE_PATHS.values() or path.startswith("attachments/"), "unsupported artifact location")
        _require(path not in by_path, "duplicate artifact path")
        _hash(artifact["sha256"], path)
        _number(artifact["bytes"], path, integer=True)
        _require(artifact["bytes"] <= MAX_FILE_BYTES, "artifact exceeds size limit")
        total += artifact["bytes"]
        by_path[path] = artifact
    _require(total <= MAX_BUNDLE_BYTES, "bundle exceeds size limit")
    _require(set(CORE_PATHS.values()) <= set(by_path), "required artifact missing from manifest")
    coverage = manifest["source_coverage"]
    _keys(coverage, {"receipts", "scheduler", "verifier", "stdout", "stderr"}, "source_coverage")
    for name, value in coverage.items():
        _keys(value, {"status", "reason"}, name)
        _require(value["status"] in {"complete", "unavailable", "not_applicable"}, "invalid coverage status")
        _string(value["reason"], "coverage reason")
    return by_path


def _metadata(files, manifest):
    def doc(role, keys):
        value = _json(files[CORE_PATHS[role]], role)
        _keys(value, keys, role)
        return value
    environment = doc("environment", {"os", "python", "dependencies", "details"})
    for name in ("os", "python"):
        _string(environment[name], name)
    _require(isinstance(environment["dependencies"], list) and all(isinstance(x, str) for x in environment["dependencies"]),
             "dependencies must be strings")
    _require(isinstance(environment["details"], dict), "environment details must be object")
    git = doc("git", {"commit", "tree", "dirty", "details"})
    for name in ("commit", "tree"):
        _require(isinstance(git[name], str) and re.fullmatch(r"(?:[a-f0-9]{40}|[a-f0-9]{64})", git[name]) is not None,
                 f"invalid Git {name}")
    _require(type(git["dirty"]) is bool and isinstance(git["details"], dict), "invalid Git metadata")
    workload = doc("workload", {"workload_id", "expected_cells"})
    _identifier(workload["workload_id"], "workload_id")
    _require(workload["expected_cells"] == manifest["expected_cells"], "workload schedule differs from manifest")
    models = doc("models", {"models"})["models"]
    _require(isinstance(models, list), "models must be array")
    model_ids = set()
    for model in models:
        _keys(model, {"model_id", "provider", "requested_revision", "observed_revision", "parameters"}, "model")
        _identifier(model["model_id"], "model_id")
        _require(model["model_id"] not in model_ids, "duplicate model identity")
        model_ids.add(model["model_id"])
        for name in ("provider", "requested_revision"):
            _string(model[name], name)
        if model["observed_revision"] is not None:
            _string(model["observed_revision"], "observed_revision")
        _require(isinstance(model["parameters"], dict), "model parameters must be object")
    prompts = doc("prompts", {"prompts"})["prompts"]
    _require(isinstance(prompts, list), "prompts must be array")
    prompt_ids = set()
    for prompt in prompts:
        _keys(prompt, {"prompt_id", "path", "sha256"}, "prompt")
        _identifier(prompt["prompt_id"], "prompt_id")
        _require(prompt["prompt_id"] not in prompt_ids, "duplicate prompt identity")
        prompt_ids.add(prompt["prompt_id"])
        _path(prompt["path"])
        _hash(prompt["sha256"], "prompt hash")
        _require(prompt["path"] in files and hashlib.sha256(files[prompt["path"]]).hexdigest() == prompt["sha256"],
                 "prompt content mismatch")
    protocol = doc("protocol", {"protocol_id", "status", "document_path", "document_sha256"})
    _identifier(protocol["protocol_id"], "protocol_id")
    _require(protocol["status"] in {"preparation", "frozen"}, "invalid protocol status")
    _path(protocol["document_path"])
    _hash(protocol["document_sha256"], "protocol hash")
    _require(protocol["document_path"] in files and hashlib.sha256(files[protocol["document_path"]]).hexdigest() == protocol["document_sha256"],
             "protocol content mismatch")
    return model_ids, protocol


def _records(files, expected, model_ids):
    ids = set(expected)
    records = {}
    for role in ("cells", "usage", "timing", "failures"):
        records[role] = _jsonl(files[CORE_PATHS[role]], role)
    unique = {role: set() for role in records}
    for role, rows in records.items():
        for row in rows:
            if role == "cells":
                _keys(row, {"cell_id", "execution_status", "verifier_status", "correctness_status", "accepted", "reworked", "merge_conflicts", "tests_passed", "tests_total", "source_refs"}, role)
                _require(row["execution_status"] in EXECUTION and row["verifier_status"] in VERDICTS and row["correctness_status"] in CORRECTNESS,
                         "invalid cell outcome")
                _require(type(row["accepted"]) is bool or row["accepted"] is None, "accepted must be boolean or null")
                _require(type(row["reworked"]) is bool or row["reworked"] is None, "reworked must be boolean or null")
                for name in ("merge_conflicts", "tests_passed", "tests_total"):
                    _number(row[name], name, integer=True, nullable=True)
                _require((row["tests_passed"] is None) == (row["tests_total"] is None), "partial test count")
                if row["tests_total"] is not None:
                    _require(row["tests_passed"] <= row["tests_total"], "passed tests exceed total")
                key = row["cell_id"]
            elif role == "usage":
                _keys(row, {"call_id", "cell_id", "attempt", "provider", "model_id", "role", "status", "input_tokens", "output_tokens", "cost_usd", "elapsed_seconds", "source_refs"}, role)
                _identifier(row["call_id"], "call_id")
                _number(row["attempt"], "attempt", integer=True)
                _string(row["provider"], "provider")
                _require(row["model_id"] in model_ids, "unretained model identity")
                _require(row["role"] in {"worker", "coordinator", "verifier", "grader"}, "invalid call role")
                _require(row["status"] in {"COMPLETED", "TIMEOUT", "ERROR", "UNKNOWN", "RESERVED"}, "invalid call status")
                for name in ("input_tokens", "output_tokens"):
                    _number(row[name], name, integer=True, nullable=True)
                for name in ("cost_usd", "elapsed_seconds"):
                    _number(row[name], name, nullable=True)
                key = row["call_id"]
            elif role == "timing":
                _keys(row, {"cell_id", "elapsed_seconds", "gpu_seconds", "coordination_seconds", "local_cost_usd", "usage_complete", "source_refs"}, role)
                for name in ("elapsed_seconds", "gpu_seconds", "coordination_seconds", "local_cost_usd"):
                    _number(row[name], name, nullable=True)
                _require(type(row["usage_complete"]) is bool, "usage_complete must be boolean")
                if row["elapsed_seconds"] is not None and row["coordination_seconds"] is not None:
                    _require(row["coordination_seconds"] <= row["elapsed_seconds"], "coordination exceeds cell elapsed time")
                key = row["cell_id"]
            else:
                _keys(row, {"failure_id", "cell_id", "stage", "kind", "detail", "source_refs"}, role)
                _identifier(row["failure_id"], "failure_id")
                for name in ("stage", "kind", "detail"):
                    _string(row[name], name)
                key = row["failure_id"]
            _require(isinstance(row["cell_id"], str) and row["cell_id"] in ids, f"{role}: unscheduled cell")
            _require(key not in unique[role], f"{role}: duplicate record")
            unique[role].add(key)
            _refs(row, files, role)
    # Existing native evidence envelopes are retained as opaque JSON objects. Their
    # hashes are checked, but this tool does not authenticate or reinterpret them.
    for role in ("receipts", "scheduler", "verifier"):
        _jsonl(files[CORE_PATHS[role]], role)
    return records


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def _summarize(cells, timings, calls):
    n = len(cells)
    accepted = [c for c in cells if c["accepted"] is True]
    good = sum(c["correctness_status"] == "CORRECT" for c in accepted)
    bad = sum(c["correctness_status"] == "INCORRECT" for c in accepted)
    ungraded = len(accepted) - good - bad
    missing_acceptance = sum(c["accepted"] is None for c in cells)
    known_cost = math.fsum(c["cost_usd"] for c in calls if c["cost_usd"] is not None)
    known_cost += math.fsum(t["local_cost_usd"] for t in timings if t["local_cost_usd"] is not None)
    outcomes_recorded = all(c["execution_status"] != "MISSING" for c in cells)
    calls_finished = all(c["status"] not in {"UNKNOWN", "RESERVED"} for c in calls)
    cost_complete = (outcomes_recorded and calls_finished and len(timings) == n and all(t["usage_complete"] and t["local_cost_usd"] is not None for t in timings)
                     and all(c["cost_usd"] is not None for c in calls))
    tokens_complete = (outcomes_recorded and calls_finished and len(timings) == n and all(t["usage_complete"] for t in timings)
                       and all(c["input_tokens"] is not None and c["output_tokens"] is not None for c in calls))
    tokens_known = sum((c["input_tokens"] or 0) + (c["output_tokens"] or 0) for c in calls)
    aer = _ratio(bad, len(accepted)) if not ungraded and not missing_acceptance else None
    # If acceptance itself is missing, it could add either correct or incorrect
    # acceptances. Bounds explicitly include those unresolved cells.
    bound_denominator = len(accepted) + missing_acceptance
    bounds = [_ratio(bad, bound_denominator), _ratio(bad + ungraded + missing_acceptance, bound_denominator)]
    return {
        "scheduled_cells": n, "recorded_cells": sum(c["execution_status"] != "MISSING" for c in cells),
        "accepted_count": len(accepted), "correct_accepted_count": good, "incorrect_accepted_count": bad,
        "unknown_accepted_correctness_count": ungraded, "unknown_acceptance_count": missing_acceptance,
        "acceptance_rate": _ratio(len(accepted), n) if not missing_acceptance else None,
        "acceptance_rate_bounds": [_ratio(len(accepted), n), _ratio(len(accepted) + missing_acceptance, n)],
        "verified_goodput": _ratio(good, n), "accepted_error_rate": aer,
        "accepted_error_rate_bounds": bounds,
        "execution_counts": dict(sorted(Counter(c["execution_status"] for c in cells).items())),
        "verifier_counts": dict(sorted(Counter(c["verifier_status"] for c in cells).items())),
        "correctness_counts": dict(sorted(Counter(c["correctness_status"] for c in cells).items())),
        "provider_calls": len(calls), "token_cost_total": tokens_known if tokens_complete else None,
        "known_token_subtotal": tokens_known, "tokens_complete": tokens_complete,
        "known_cost_usd_subtotal": known_cost, "cost_complete": cost_complete,
        "total_cost_usd": known_cost if cost_complete else None,
        "cost_per_correct_acceptance_usd": _ratio(known_cost, good) if cost_complete else None,
    }


def _pareto(by_configuration):
    """Unweighted descriptive dominance on complete retained dimensions only.

    If any arm is incomplete, the global frontier is unknown. The complete-point
    frontier is explicitly conditional and cannot establish dominance over that arm.
    Equal points never dominate each other.
    """
    _require(len(by_configuration) <= MAX_PARETO_POINTS, "Pareto configuration count exceeds bounded replay limit")
    points = {}
    eligible = {}
    for configuration, metrics in sorted(by_configuration.items()):
        reasons = []
        if not metrics["cost_complete"] or metrics["total_cost_usd"] is None:
            reasons.append("incomplete_cost")
        if metrics["accepted_count"] == 0:
            reasons.append("zero_acceptance")
        if metrics["unknown_acceptance_count"]:
            reasons.append("unknown_acceptance")
        if metrics["unknown_accepted_correctness_count"]:
            reasons.append("unknown_accepted_correctness")
        values = {key: metrics[key] for key in ("accepted_error_rate", "total_cost_usd", "verified_goodput")}
        if any(value is None for value in values.values()) and not reasons:
            reasons.append("incomplete_dimensions")
        points[configuration] = {
            **values,
            "scheduled_cells": metrics["scheduled_cells"],
            "recorded_cells": metrics["recorded_cells"],
            "accepted_count": metrics["accepted_count"],
            "acceptance_rate": metrics["acceptance_rate"],
            "acceptance_rate_bounds": metrics["acceptance_rate_bounds"],
            "unknown_acceptance_count": metrics["unknown_acceptance_count"],
            "unknown_accepted_correctness_count": metrics["unknown_accepted_correctness_count"],
            "status": "indeterminate" if reasons else "complete",
            "indeterminate_reasons": reasons,
            "dominated_by": [],
        }
        if not reasons:
            eligible[configuration] = (values["accepted_error_rate"], values["total_cost_usd"], -values["verified_goodput"])
    for configuration, candidate in eligible.items():
        points[configuration]["dominated_by"] = [
            other for other, challenger in eligible.items()
            if other != configuration and all(a <= b for a, b in zip(challenger, candidate))
            and any(a < b for a, b in zip(challenger, candidate))
        ]
    conditional_frontier = [name for name in eligible if not points[name]["dominated_by"]]
    complete = len(eligible) == len(points)
    for name in eligible:
        points[name]["status"] = ("dominated" if points[name]["dominated_by"] else
                                  "nondominated" if complete else "nondominated_among_complete_points")
    return {
        "kind": "descriptive",
        "objectives": {"accepted_error_rate": "minimize", "total_cost_usd": "minimize", "verified_goodput": "maximize"},
        "status": "complete" if complete else "indeterminate",
        "frontier": conditional_frontier if complete else None,
        "frontier_among_complete_points": conditional_frontier,
        "points": points,
        "interpretation": "Observed unweighted dominance only; no inference, bootstrap stability, or probability-of-truth claim.",
    }


def _cell_system_metrics(cell, timing, calls):
    """SPEC-EVAL-001 formulas at a single cell, never summed parallel wall time.

    RunCounters forbids absent timing/tests. Keep undefined denominators null here
    rather than manufacture observations to satisfy that older complete-run type.
    Its legacy token_cost_total name counts tokens, not dollars.
    """
    elapsed = timing.get("elapsed_seconds")
    gpu = timing.get("gpu_seconds")
    coordination = timing.get("coordination_seconds")
    tokens_complete = (bool(timing.get("usage_complete")) and
                       all(c["status"] not in {"UNKNOWN", "RESERVED"} and
                           c["input_tokens"] is not None and c["output_tokens"] is not None for c in calls))
    tests_total = cell["tests_total"]
    verdict = cell["verifier_status"]
    return {
        "elapsed_time_minutes": elapsed / 60 if elapsed is not None else None,
        "accepted_tasks_per_hour": (int(cell["accepted"]) * 3600 / elapsed
                                    if elapsed and cell["accepted"] is not None else None),
        "token_cost_total": (sum(c["input_tokens"] + c["output_tokens"] for c in calls)
                             if tokens_complete else None),
        "gpu_time_minutes": gpu / 60 if gpu is not None else None,
        "coordination_overhead_pct": 100 * coordination / elapsed if elapsed and coordination is not None else None,
        "rework_rate_pct": 100 * int(cell["reworked"]) if cell["reworked"] is not None else None,
        "merge_conflicts": cell["merge_conflicts"],
        "verifier_rejection_rate_pct": 100 * int(verdict == "FAIL") if verdict in {"PASS", "FAIL"} else None,
        "final_test_pass_rate_pct": 100 * cell["tests_passed"] / tests_total if tests_total else None,
    }


def _reproduce(run_id, *, runs_dir="runs", manifest_sha256=None):
    """Validate a bounded bundle and rebuild deterministic descriptive metrics."""
    _identifier(run_id, "run_id")
    if manifest_sha256 is not None:
        _hash(manifest_sha256, "manifest pin")
    try:
        with _directory(Path(runs_dir) / run_id) as root_fd:
            raw_manifest = _read(root_fd, "manifest.json")
            actual_hash = hashlib.sha256(raw_manifest).hexdigest()
            _require(manifest_sha256 is None or manifest_sha256 == actual_hash, "manifest pin mismatch")
            manifest = _json(raw_manifest, "manifest")
            artifacts = _validate_manifest(manifest, run_id)
            files = {}
            for path, entry in sorted(artifacts.items()):
                raw = _read(root_fd, path)
                _require(len(raw) == entry["bytes"] and hashlib.sha256(raw).hexdigest() == entry["sha256"],
                         f"{path}: artifact hash/size mismatch")
                files[path] = raw
    except OSError as exc:
        raise ReproductionError(f"cannot safely read bundle: {exc}") from exc
    model_ids, protocol = _metadata(files, manifest)
    expected = {c["cell_id"]: c for c in manifest["expected_cells"]}
    records = _records(files, expected, model_ids)
    observed = {c["cell_id"]: c for c in records["cells"]}
    cells = []
    for cell_id, pair in sorted(expected.items()):
        row = observed.get(cell_id, {"cell_id": cell_id, "execution_status": "MISSING", "verifier_status": "UNKNOWN",
                                    "correctness_status": "UNKNOWN", "accepted": None, "reworked": None,
                                    "merge_conflicts": None, "tests_passed": None, "tests_total": None, "source_refs": []})
        cells.append({**pair, **row})
    timing_by_cell = {t["cell_id"]: t for t in records["timing"]}
    calls_by_cell = defaultdict(list)
    cells_by_configuration = defaultdict(list)
    for call in records["usage"]:
        calls_by_cell[call["cell_id"]].append(call)
    for cell in cells:
        cells_by_configuration[cell["configuration"]].append(cell)
    system_metrics = {c["cell_id"]: _cell_system_metrics(c, timing_by_cell.get(c["cell_id"], {}),
                      calls_by_cell[c["cell_id"]]) for c in cells}
    groups = {}
    for configuration, group in sorted(cells_by_configuration.items()):
        times = [timing_by_cell[c["cell_id"]] for c in group if c["cell_id"] in timing_by_cell]
        calls = [call for c in group for call in calls_by_cell[c["cell_id"]]]
        groups[configuration] = _summarize(group, times, calls)
    report = {
        "schema_version": REPORT_SCHEMA, "run_id": run_id, "evidence_mode": manifest["evidence_mode"],
        "manifest_sha256": actual_hash, "manifest_pin_checked": manifest_sha256 is not None,
        "integrity": "artifact hashes verified; source authenticity and receipt signatures not verified",
        "publication_ready": False, "protocol": protocol, "source_coverage": manifest["source_coverage"],
        "metrics": _summarize(cells, records["timing"], records["usage"]), "by_configuration": groups,
        "pareto": _pareto(groups),
        "cells": cells, "system_metrics_by_cell": system_metrics, "failure_count": len(records["failures"]),
        "invariant_violations": [c["cell_id"] for c in cells if c["accepted"] is True and
                                 (c["verifier_status"] != "PASS" or c["execution_status"] != "COMPLETED")],
        "limitations": [
            "Descriptive reconstruction and Pareto dominance only; inferential analysis is deferred to the frozen science engine.",
            "Reported acceptance/correctness and source coverage are retained assertions, not authenticated authority.",
            "Missing scheduled cells remain MISSING with UNKNOWN grading and acceptance; no demonstrated success is not an incorrect answer.",
            "Cost includes retained per-call fees plus declared local occupancy; incomplete usage or pricing yields null totals.",
        ],
    }
    # Refuse overflow instead of serializing NaN/Infinity after aggregation.
    canonical_bytes(report)
    return report


def reproduce(run_id, *, runs_dir="runs", manifest_sha256=None):
    """Rebuild retained metrics; malformed input always raises ReproductionError."""
    try:
        return _reproduce(run_id, runs_dir=runs_dir, manifest_sha256=manifest_sha256)
    except ReproductionError:
        raise
    except (TypeError, ValueError, OverflowError, KeyError, RecursionError) as exc:
        raise ReproductionError(f"malformed retained evidence: {exc}") from exc


def canonical_bytes(report):
    try:
        return (json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    except (ValueError, OverflowError) as exc:
        raise ReproductionError("report contains nonfinite aggregates") from exc


def _write_new(path, data):
    path = Path(path)
    _require(path.name not in {"", ".", ".."}, "invalid output path")
    with _directory(path.parent) as parent:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(data)
                stream.flush()
                os.fsync(fd)
        finally:
            os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="residual reproduce", description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--runs-dir", default="runs")
    parser.add_argument("--output", help="new output file; parent directory must exist")
    parser.add_argument("--manifest-sha256", help="externally retained manifest SHA-256 commitment")
    args = parser.parse_args(argv)
    try:
        result = canonical_bytes(reproduce(args.run_id, runs_dir=args.runs_dir, manifest_sha256=args.manifest_sha256))
        if args.output:
            _write_new(args.output, result)
        else:
            sys.stdout.write(result.decode("utf-8"))
    except (ReproductionError, OSError, TypeError, OverflowError) as exc:
        print(f"reproduce: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
