#!/usr/bin/env python3
"""Compare tokenizers on a corpus: tokens per trajectory, truncation rate
at a given context length, encoding throughput, and peak memory.

Supports r50k_base, any tiktoken encoding ("generic", e.g. o200k_base),
and a custom residual-bpe `.tiktoken` file. This tool NEVER calls any
benchmark; it only reads an explicitly provided corpus file.

Usage:
    python measure.py --corpus observations.jsonl --context 2048 \
        --tokenizer r50k_base --tokenizer o200k_base \
        --tokenizer residual_bpe.tiktoken
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import tracemalloc
from pathlib import Path

# Reuse the tokenizer loading + canonical rendering from the dataset
# compiler to keep semantics identical across the toolchain.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dataset"))
import compile as dataset_compile  # noqa: E402  pylint: disable=wrong-import-position


def fail(msg: str) -> "SystemExit":
    print(f"error: {msg}", file=sys.stderr)
    return SystemExit(2)


def measure_one(spec: str, records: list[str], context: int) -> dict:
    enc = dataset_compile.get_tokenizer(spec)
    tracemalloc.start()
    started = time.monotonic()
    token_counts: list[int] = []
    for text in records:
        token_counts.append(len(enc.encode(text)))
    elapsed = time.monotonic() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    total = sum(token_counts)
    n = len(token_counts)
    truncated = sum(1 for c in token_counts if context and c > context)
    return {
        "tokenizer": spec,
        "records": n,
        "total_tokens": total,
        "tokens_per_trajectory_mean": round(total / n, 2) if n else 0.0,
        "tokens_per_trajectory_max": max(token_counts) if n else 0,
        "context_length": context,
        "truncated_records": truncated,
        "truncation_rate": round(truncated / n, 6) if n else 0.0,
        "encode_seconds": round(elapsed, 3),
        "records_per_second": round(n / elapsed, 1) if elapsed else None,
        "tokens_per_second": round(total / elapsed, 1) if elapsed else None,
        "peak_memory_bytes": peak,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--corpus", required=True,
                   help="Observation JSONL corpus (canonical records).")
    p.add_argument("--context", type=int, default=2048,
                   help="Context length for truncation-rate measurement "
                        "(default: 2048; 0 disables).")
    p.add_argument("--tokenizer", action="append", required=True,
                   help="tiktoken encoding name or .tiktoken file; "
                        "repeatable for ablation (SLM-04).")
    p.add_argument("--output", default="",
                   help="Optional path to write JSON results.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    corpus = Path(args.corpus)
    if not corpus.exists():
        raise fail(f"corpus not found: {corpus}")
    records = [
        dataset_compile.canonical_text(rec)
        for _, rec in dataset_compile.stream_jsonl(corpus)
    ]
    if not records:
        raise fail(f"corpus {corpus} contained no records")
    results = [measure_one(spec, records, args.context)
               for spec in args.tokenizer]
    payload = json.dumps({"corpus": str(corpus), "results": results},
                         indent=2)
    print(payload)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
