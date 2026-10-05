#!/usr/bin/env python3
"""Append-only, digest-chained research results store for EXP-M6-SLM.

Each run record binds: stable run id, model hash, benchmark hash,
harness condition (SLM-05 A-F), seed (from the frozen seed list), seed
index, hardware, metrics (using the frozen metric names: VMSR, VSMS/$,
VSMS/W, FNER, AVR, frontier calls avoided, UER, operator-active minutes,
latency, schema-invalid output rate, ECE, Brier, throughput), and raw
outputs. Records are appended to a JSONL chain where each record carries
the SHA-256 digest of the previous record, making tampering evident.

This store is SEPARATE from production logs. It never writes to
production paths and never reads holdout labels; it stores metrics and
outputs that were computed elsewhere.

CLI:
  python results_store.py --help
  python results_store.py init --store runs.jsonl
  python results_store.py append --store runs.jsonl --record record.json
  python results_store.py verify --store runs.jsonl
  python results_store.py list --store runs.jsonl [--condition F]
  python results_store.py schema  (prints results-store.schema.json)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Dict, Iterator, List, Optional, Sequence

SCHEMA_VERSION = "slm-results-store-v0"
GENESIS_DIGEST = "0" * 64

CONDITIONS = ("A", "B", "C", "D", "E", "F")
FROZEN_SEEDS = (20260920, 4117, 89123, 777001, 5551212)

# Frozen metric names (EVALUATION-PROTOCOL.md sections 2-4).
KNOWN_METRICS = {
    "vmsr",
    "vsms_per_dollar",
    "vsms_per_watt",
    "fner",
    "avr",
    "frontier_calls_avoided",
    "uer",
    "operator_active_minutes",
    "latency_ms_median",
    "latency_ms_p95",
    "latency_ms_p99",
    "schema_invalid_rate",
    "ece",
    "brier",
    "throughput_decisions_per_sec",
}

REQUIRED_FIELDS = (
    "model_hash",
    "benchmark_hash",
    "harness_condition",
    "seed",
    "seed_index",
    "hardware",
    "metrics",
)

_SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "results-store.schema.json"
)


def canonical_json(obj: object) -> bytes:
    """Deterministic serialization used for digest chaining."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def record_digest(record: Dict[str, object]) -> str:
    """SHA-256 over the record with its own digest field excluded."""
    body = {k: v for k, v in record.items() if k != "digest"}
    return hashlib.sha256(canonical_json(body)).hexdigest()


def validate_record(record: Dict[str, object]) -> List[str]:
    """Validate a record against the store contract; returns problems."""
    problems = []
    for name in REQUIRED_FIELDS:
        if name not in record:
            problems.append("missing required field: %s" % name)
    cond = record.get("harness_condition")
    if cond is not None and cond not in CONDITIONS:
        problems.append(
            "harness_condition must be one of %s, got %r" % (CONDITIONS, cond)
        )
    seed = record.get("seed")
    if seed is not None and seed not in FROZEN_SEEDS:
        problems.append(
            "seed %r not in frozen seed list %s" % (seed, FROZEN_SEEDS)
        )
    metrics = record.get("metrics")
    if metrics is not None:
        if not isinstance(metrics, dict):
            problems.append("metrics must be an object")
        else:
            unknown = set(metrics) - KNOWN_METRICS
            if unknown:
                problems.append(
                    "unknown metric names (not in frozen protocol): %s"
                    % sorted(unknown)
                )
    return problems


def _read_all(path: str) -> List[Dict[str, object]]:
    records = []
    if not os.path.exists(path):
        return records
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError("%s:%d: corrupt record: %s" % (path, lineno, exc))
    return records


def init_store(path: str) -> None:
    """Create a new empty store; refuses to overwrite (append-only)."""
    if os.path.exists(path):
        raise FileExistsError("store already exists (append-only): %s" % path)
    with open(path, "x", encoding="utf-8") as fh:
        fh.write("")


def append_record(path: str, record: Dict[str, object]) -> Dict[str, object]:
    """Validate, chain, and append a record; returns the stored record."""
    problems = validate_record(record)
    if problems:
        raise ValueError("invalid record: %s" % "; ".join(problems))
    records = _read_all(path)
    seq = len(records)
    prev = records[-1]["digest"] if records else GENESIS_DIGEST
    run_id = "slm-run-%s-%06d" % (
        hashlib.sha256(canonical_json(record)).hexdigest()[:12],
        seq,
    )
    stored = dict(record)
    stored.update(
        {"schema_version": SCHEMA_VERSION, "seq": seq, "run_id": run_id,
         "prev_digest": prev}
    )
    stored["digest"] = record_digest(stored)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(stored, sort_keys=True) + "\n")
    return stored


def verify_chain(path: str) -> List[str]:
    """Verify digest chain integrity; returns a list of violations."""
    violations = []
    prev = GENESIS_DIGEST
    for i, rec in enumerate(_read_all(path)):
        if rec.get("schema_version") != SCHEMA_VERSION:
            violations.append("seq %d: bad schema_version" % i)
        if rec.get("seq") != i:
            violations.append("seq %d: sequence gap/rewrite" % i)
        if rec.get("prev_digest") != prev:
            violations.append("seq %d: prev_digest mismatch" % i)
        if rec.get("digest") != record_digest(rec):
            violations.append("seq %d: digest mismatch (tampered?)" % i)
        prev = rec.get("digest", prev)
    return violations


def iter_records(
    path: str, condition: Optional[str] = None
) -> Iterator[Dict[str, object]]:
    for rec in _read_all(path):
        if condition and rec.get("harness_condition") != condition:
            continue
        yield rec


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--store", help="path to the JSONL results store")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="create a new empty append-only store")
    app = sub.add_parser("append", help="append a run record")
    app.add_argument("--record", required=True, help="record JSON path")
    sub.add_parser("verify", help="verify digest-chain integrity")
    lst = sub.add_parser("list", help="list records (JSON)")
    lst.add_argument("--condition", choices=CONDITIONS)
    sub.add_parser("schema", help="print the JSON schema")
    args = parser.parse_args(argv)

    if args.command == "schema":
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as fh:
            sys.stdout.write(fh.read())
        return 0
    if not args.store:
        parser.error("--store is required for this command")

    try:
        if args.command == "init":
            init_store(args.store)
        elif args.command == "append":
            with open(args.record, "r", encoding="utf-8") as fh:
                record = json.load(fh)
            stored = append_record(args.store, record)
            print(json.dumps({"run_id": stored["run_id"],
                              "digest": stored["digest"]}, indent=2))
        elif args.command == "verify":
            violations = verify_chain(args.store)
            if violations:
                for v in violations:
                    print("VIOLATION: %s" % v)
                return 1
            print("chain OK: %s" % args.store)
        elif args.command == "list":
            print(json.dumps(list(iter_records(args.store, args.condition)),
                             indent=2, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
