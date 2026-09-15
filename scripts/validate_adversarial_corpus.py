#!/usr/bin/env python3
"""Validate/export inert challenges and score retained decisions without execution.

This is an engineering accounting utility, not an M4 verifier, signature verifier,
statistical estimator, or authorization path. Candidate source is never executed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys


DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "experiments/preflight/adversarial"
FROZEN_MANIFEST_SHA256 = "ee94c35c2fa823386b195c778b5540c98ca710fe4a4ac33e4b5f38c17aa36756"
MAX_BYTES = 2 * 1024 * 1024
CATEGORIES = frozenset({
    "subtle_wrong_answer", "partially_correct_patch", "hidden_regression",
    "flaky_test", "adversarial_stdout", "manipulated_receipt", "stale_evidence",
    "semantic_valid_syntax",
})
FAULTS = frozenset({
    "worker_timeout", "worker_crash", "malformed_response", "duplicate_receipt",
    "stale_receipt", "network_loss", "provider_429", "provider_500",
    "corrupted_git_object", "verifier_timeout", "scheduler_restart",
    "station_restart", "evidence_sink_interruption", "disk_full", "partial_write",
})


class ValidationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_hash(value: object) -> str:
    return digest_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                   ensure_ascii=True, allow_nan=False).encode())


def strict_json(data: bytes) -> object:
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def invalid(value):
        raise ValidationError(f"non-finite JSON value: {value}")

    try:
        return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError("invalid JSON") from exc


def read_bounded(path: Path) -> bytes:
    require(not path.is_symlink(), "symlink input rejected")
    # Nonblocking open prevents a FIFO from hanging before the fstat check.
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        require(stat.S_ISREG(info.st_mode), "input must be a regular file")
        require(info.st_nlink == 1, "hardlinked input rejected")
        require(info.st_size <= MAX_BYTES, "input exceeds byte limit")
        data = handle.read(MAX_BYTES + 1)
    require(len(data) <= MAX_BYTES, "input exceeds byte limit")
    return data


def corpus_path(root: Path, relative: str) -> Path:
    require(isinstance(relative, str) and bool(relative), "invalid relative path")
    p = PurePosixPath(relative)
    require(not p.is_absolute() and p.as_posix() == relative and
            all(part not in {"", ".", ".."} for part in p.parts) and
            "\\" not in relative, "noncanonical corpus path")
    current = root
    require(not current.is_symlink(), "symlink corpus root rejected")
    for part in p.parts:
        current = current / part
        require(not current.is_symlink(), "symlink corpus path rejected")
    return current


def validate_corpus(root: Path = DEFAULT_ROOT) -> dict:
    root = Path(root)
    raw = read_bounded(corpus_path(root, "manifest.json"))
    require(digest_bytes(raw) == FROZEN_MANIFEST_SHA256, "frozen manifest hash mismatch")
    manifest = strict_json(raw)
    require(manifest["schema"] == "residual.preflight.adversarial-manifest.v1",
            "unsupported manifest schema")
    locked = manifest["files"]
    actual_json = {p.relative_to(root).as_posix() for p in root.rglob("*.json")}
    require(actual_json == set(locked) | {"manifest.json"}, "unexpected or missing JSON files")
    documents = {}
    for relative, expected in locked.items():
        data = read_bounded(corpus_path(root, relative))
        require(digest_bytes(data) == expected, f"frozen file hash mismatch: {relative}")
        documents[relative] = strict_json(data)
    labels = documents[manifest["gold_path"]]
    require(labels["schema"] == "residual.preflight.gold.v1", "unsupported gold schema")
    gold = {}
    for label in labels["cases"]:
        case_id = label["case_id"]
        require(case_id not in gold, "duplicate gold case")
        require(type(label["acceptable"]) is bool, "gold label must be boolean")
        require(label["category"] in CATEGORIES, "unknown challenge category")
        require(label["label_source"] == "specification_counterexample", "inadmissible gold source")
        require(bool(label["witnesses"]) and bool(label["rationale"]), "missing ground truth evidence")
        unequal = [w["expected"] != w["candidate_actual"] for w in label["witnesses"]]
        require(not any(unequal) if label["acceptable"] else any(unequal),
                "ground truth witnesses contradict the label")
        gold[case_id] = label
    inputs = {}
    for case in manifest["cases"]:
        case_id = case["case_id"]
        require(case_id not in inputs, "duplicate manifest case")
        data = documents[case["input_path"]]
        require(set(data) == {"schema", "case_id", "task", "artifact"},
                "candidate envelope contains unexpected fields")
        require(data["case_id"] == case_id and data["schema"] == "residual.preflight.candidate.v1",
                "candidate identity/schema mismatch")
        inputs[case_id] = {"data": data, "sha256": locked[case["input_path"]]}
    require(set(gold) == set(inputs), "candidate/gold set mismatch")
    for category in CATEGORIES:
        require({x["acceptable"] for x in gold.values() if x["category"] == category} == {False, True},
                "each category needs a defect and a correct control")
    matrix = documents[manifest["fault_matrix_path"]]
    require(matrix["schema"] == "residual.preflight.fault-matrix.v1", "unsupported fault schema")
    require({f["name"] for f in matrix["faults"]} == FAULTS, "fault coverage mismatch")
    require(matrix["count"] == len(matrix["faults"]) == len(FAULTS), "fault count mismatch")
    for fault in matrix["faults"]:
        for field in ("boundary", "injection", "observed_injection_requirement",
                      "expected_fail_closed_result", "required_evidence", "blocked_prerequisites"):
            require(bool(fault[field]), f"fault missing {field}")
        require(fault["execution_status"] == "not_executed", "design must not claim executed faults")
    return {"manifest": manifest, "inputs": inputs, "gold": gold, "fault_matrix": matrix}


def _sha(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _ratio(numerator: int, denominator: int) -> dict:
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None}


def score_outcomes(corpus: dict, report: dict) -> dict:
    """Score one attempt per case, preserving all exclusions in the denominator.

    Evidence hashes establish consistency of the supplied report. They do not
    authenticate the reporting party or prove that a verifier ran in isolation.
    """
    require(isinstance(report, dict) and set(report) == {
        "schema", "corpus_manifest_sha256", "verifier_revision_sha256", "observations", "evidence"
    }, "invalid outcome report fields")
    require(report["schema"] == "residual.preflight.verifier-observations.v1", "unsupported outcomes schema")
    require(report["corpus_manifest_sha256"] == FROZEN_MANIFEST_SHA256, "outcomes belong to another corpus")
    revision = report["verifier_revision_sha256"]
    require(_sha(revision), "invalid verifier revision hash")
    require(isinstance(report["observations"], list) and isinstance(report["evidence"], dict),
            "invalid observations/evidence types")
    evidence = report["evidence"]
    seen = set()
    used = set()
    counts = Counter({k: 0 for k in (
        "true_accept", "false_accept", "true_reject", "false_reject", "unknown",
        "error", "skipped", "resource_limited", "signal", "missing"
    )})
    by_category = {category: Counter() for category in sorted(CATEGORIES)}
    by_class = {"acceptable": Counter(), "defective": Counter()}
    sources = Counter()
    classified = []
    for observation in report["observations"]:
        require(isinstance(observation, dict) and set(observation) == {"case_id", "evidence_sha256"},
                "invalid observation fields")
        case_id = observation["case_id"]
        require(case_id in corpus["inputs"] and case_id not in seen, "unknown or duplicate case_id")
        seen.add(case_id)
        reference = observation["evidence_sha256"]
        require(_sha(reference) and reference in evidence, "missing evidence blob")
        item = evidence[reference]
        require(isinstance(item, dict) and set(item) == {
            "schema", "case_id", "candidate_sha256", "verifier_revision_sha256",
            "status", "termination_reason", "returncode", "source"
        }, "invalid evidence fields")
        require(canonical_hash(item) == reference, "evidence hash mismatch")
        require(item["schema"] == "residual.preflight.verifier-evidence.v1", "unsupported evidence schema")
        require(item["case_id"] == case_id and item["candidate_sha256"] == corpus["inputs"][case_id]["sha256"]
                and item["verifier_revision_sha256"] == revision, "evidence identity mismatch")
        require(item["source"] in {"synthetic-accounting-test", "retained-run"}, "invalid evidence source")
        used.add(reference)
        sources[item["source"]] += 1
        status, reason, code = item["status"], item["termination_reason"], item["returncode"]
        require(status in {"pass", "fail", "unknown", "error", "skipped"}, "invalid verifier status")
        require(reason in {"exit", "timeout", "output_limit", "sandbox_error", "launch_failed",
                           "isolation_unavailable", "signal", "not_run", "verifier_error"},
                "invalid termination reason")
        require(code is None or type(code) is int, "returncode must be integer or null")
        if status == "pass":
            require(reason == "exit" and code == 0, "PASS requires normal zero exit")
        if status == "fail":
            require(reason in {"exit", "timeout", "output_limit", "signal"}, "invalid FAIL origin")
            if reason == "exit":
                require(type(code) is int and code != 0, "FAIL exit requires nonzero returncode")
        if status == "unknown":
            require(reason in {"exit", "launch_failed", "isolation_unavailable"}, "invalid UNKNOWN origin")
        if status == "error":
            require(reason in {"sandbox_error", "launch_failed", "verifier_error"}, "invalid ERROR origin")
        if status == "skipped":
            require(reason == "not_run" and code is None, "invalid SKIPPED origin")
        acceptable = corpus["gold"][case_id]["acceptable"]
        if status in {"unknown", "error", "skipped"}:
            bucket = status
        elif reason in {"timeout", "output_limit"}:
            bucket = "resource_limited"
        elif reason == "signal" or (type(code) is int and code < 0):
            bucket = "signal"
        else:
            bucket = ("true_accept" if acceptable else "false_accept") if status == "pass" else (
                "false_reject" if acceptable else "true_reject")
        counts[bucket] += 1
        by_category[corpus["gold"][case_id]["category"]][bucket] += 1
        by_class["acceptable" if acceptable else "defective"][bucket] += 1
        classified.append({"case_id": case_id, "bucket": bucket, "evidence_sha256": reference})
    require(used == set(evidence), "unreferenced evidence blobs")
    for case_id in sorted(set(corpus["inputs"]) - seen):
        counts["missing"] += 1
        by_category[corpus["gold"][case_id]["category"]]["missing"] += 1
        by_class["acceptable" if corpus["gold"][case_id]["acceptable"] else "defective"]["missing"] += 1
        classified.append({"case_id": case_id, "bucket": "missing", "evidence_sha256": None})
    ta, fa, tr, fr = (counts[k] for k in ("true_accept", "false_accept", "true_reject", "false_reject"))
    total = len(corpus["inputs"])
    require(sum(counts.values()) == total, "accounting does not reconcile")
    return {
        "schema": "residual.preflight.verifier-score.v1",
        "scope": "non_confirmatory_engineering_accounting",
        "corpus_manifest_sha256": FROZEN_MANIFEST_SHA256,
        "verifier_revision_sha256": revision,
        "evidence_authenticity": "not_assessed_by_this_tool",
        "contains_synthetic_evidence": bool(sources["synthetic-accounting-test"]),
        "source_counts": dict(sources),
        "total_frozen_cases": total,
        "counts": dict(counts),
        "metrics": {
            "acceptance_precision": _ratio(ta, ta + fa),
            "acceptance_recall": _ratio(ta, ta + fr),
            "defect_precision": _ratio(tr, tr + fr),
            "defect_recall": _ratio(tr, tr + fa),
            "false_accept_rate_on_decided_defects": _ratio(fa, fa + tr),
            "false_reject_rate_on_decided_controls": _ratio(fr, fr + ta),
            "decision_coverage": _ratio(ta + fa + tr + fr, total),
            "unsafe_accepts_per_frozen_defect": _ratio(fa, sum(not g["acceptable"] for g in corpus["gold"].values())),
        },
        "by_category": {k: dict(v) for k, v in by_category.items()},
        "by_gold_class": {k: dict(v) for k, v in by_class.items()},
        "classified": sorted(classified, key=lambda item: item["case_id"]),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "export", "score"))
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--outcomes", type=Path)
    args = parser.parse_args(argv)
    try:
        corpus = validate_corpus(args.root)
        if args.command == "export":
            for item in corpus["inputs"].values():
                print(json.dumps(item["data"], sort_keys=True, ensure_ascii=True, allow_nan=False))
            return 0
        if args.command == "score":
            require(args.outcomes is not None, "score requires --outcomes")
            result = score_outcomes(corpus, strict_json(read_bounded(args.outcomes)))
        else:
            result = {"status": "valid", "manifest_sha256": FROZEN_MANIFEST_SHA256,
                      "case_count": len(corpus["inputs"]), "categories": sorted(CATEGORIES),
                      "fault_designs": len(FAULTS), "candidate_execution": "none"}
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (ValidationError, OSError, TypeError, KeyError, ValueError) as exc:
        print(f"adversarial corpus validation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
