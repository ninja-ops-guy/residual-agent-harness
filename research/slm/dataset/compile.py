#!/usr/bin/env python3
"""Compile a canonical observation JSONL corpus into a packed binary dataset.

Pipeline: streaming JSONL reader -> schema validation (fail-closed) ->
deterministic seeded shuffle -> train/holdout assignment via a pre-provided
split manifest ONLY (this tool never invents splits) -> tokenization ->
packed uint32 token stream + manifest + per-record index.

Usage:
    python compile.py --input observations.jsonl --split-manifest splits.json \
        --output-dir out/ --seed 1234 --tokenizer r50k_base

Split manifest format (JSON):
    {"observation_id": "train" | "holdout", ...}
Every observation_id in the input MUST appear in the manifest; the tool
refuses to proceed otherwise.

Determinism: identical inputs, seed, and tokenizer produce byte-identical
outputs (hashes recorded in dataset_manifest.json).
"""
from __future__ import annotations

import argparse
import array
import base64
import datetime as dt
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any, Iterator

REQUIRED_SPLIT_VALUES = {"train", "holdout"}

# Fields that are allowed to be null per observation.schema.json; we count
# nulls for observability but never substitute invented values.
NULLABLE_FIELDS = (
    "proposed_decision",
    "contamination_group",
    "notes",
)


def fail(msg: str) -> "SystemExit":
    print(f"error: {msg}", file=sys.stderr)
    return SystemExit(2)


def stream_jsonl(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    """Yield (line_number, record) for each non-blank line."""
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                raise fail(f"{path}:{lineno}: invalid JSON: {exc}")
            if not isinstance(rec, dict):
                raise fail(f"{path}:{lineno}: record is not a JSON object")
            yield lineno, rec


def load_validator(schema_path: Path):
    try:
        import jsonschema
    except ImportError:
        raise fail("jsonschema is required: pip install jsonschema==4.23.0")
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise fail(f"cannot load schema {schema_path}: {exc}")
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def load_split_manifest(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise fail(f"cannot load split manifest {path}: {exc}")
    if not isinstance(data, dict):
        raise fail("split manifest must be a JSON object {id: split}")
    for key, value in data.items():
        if value not in REQUIRED_SPLIT_VALUES:
            raise fail(
                f"split manifest entry {key!r} has invalid split {value!r}; "
                f"expected one of {sorted(REQUIRED_SPLIT_VALUES)}"
            )
    return data


def canonical_text(record: dict[str, Any]) -> str:
    """Deterministic text rendering of an observation for tokenization."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def get_tokenizer(spec: str):
    """Load a tiktoken encoding by name or a .tiktoken BPE file path."""
    try:
        import tiktoken
    except ImportError:
        raise fail("tiktoken is required: pip install tiktoken==0.8.0")
    candidate = Path(spec)
    if candidate.suffix == ".tiktoken" or candidate.exists():
        if not candidate.exists():
            raise fail(f"tokenizer file not found: {spec}")
        mergeable_ranks: dict[bytes, int] = {}
        with candidate.open("r", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) != 2:
                    continue
                token = base64.b64decode(parts[0])
                mergeable_ranks[token] = int(parts[1])
        pat_str = (
            r"'(?i:[sdmt]|ll|ve|re)|[^\r\n\p{L}\p{N}]?+\p{L}++"
            r"|\p{N}{1,3}+| ?[^\s\p{L}\p{N}]++[\r\n]*+|\s++$|\s*[\r\n]"
            r"|\s+(?!\S)|\s+"
        )
        return tiktoken.Encoding(
            name=candidate.stem,
            pat_str=pat_str,
            mergeable_ranks=mergeable_ranks,
            special_tokens={},
        )
    try:
        return tiktoken.get_encoding(spec)
    except ValueError as exc:
        raise fail(f"unknown tiktoken encoding {spec!r}: {exc}")


def compile_dataset(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    out_dir = Path(args.output_dir)
    if not input_path.exists():
        raise fail(f"input not found: {input_path}")
    splits = load_split_manifest(Path(args.split_manifest))
    validator = load_validator(Path(args.schema))
    enc = get_tokenizer(args.tokenizer)

    # Pass 1: stream, validate, bucket by split.
    records: dict[str, list[dict[str, Any]]] = {"train": [], "holdout": []}
    null_counts: dict[str, int] = {f: 0 for f in NULLABLE_FIELDS}
    unknown_field_counts: dict[str, int] = {}
    known_fields = set(
        validator.schema.get("properties", {}).keys())
    n_in = 0
    seen_ids: set[str] = set()
    for lineno, rec in stream_jsonl(input_path):
        n_in += 1
        errors = sorted(validator.iter_errors(rec), key=lambda e: e.path)
        if errors:
            first = errors[0]
            loc = "/".join(str(p) for p in first.path) or "<root>"
            raise fail(
                f"{input_path}:{lineno}: schema validation failed at "
                f"{loc}: {first.message} (fail-closed; record rejected)")
        oid = rec["observation_id"]
        if oid in seen_ids:
            raise fail(f"duplicate observation_id {oid!r} at line {lineno}")
        seen_ids.add(oid)
        if oid not in splits:
            raise fail(
                f"observation_id {oid!r} (line {lineno}) has no entry in the "
                f"split manifest; refusing to invent a split assignment")
        for f in NULLABLE_FIELDS:
            if rec.get(f) is None:
                null_counts[f] += 1
        for key in rec:
            if key not in known_fields:
                unknown_field_counts[key] = (
                    unknown_field_counts.get(key, 0) + 1)
        records[splits[oid]].append(rec)

    unused = set(splits) - seen_ids
    if unused:
        print(f"warning: {len(unused)} split-manifest ids absent from input "
              f"(e.g. {sorted(unused)[:3]})", file=sys.stderr)

    # Deterministic shuffle per split with the explicit seed.
    rng = random.Random(args.seed)
    for split in records:
        rng.shuffle(records[split])

    # Pass 2: tokenize + pack.
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "manifest_version": "slm-dataset-manifest-v0",
        "created_utc": dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "seed": args.seed,
        "tokenizer": args.tokenizer,
        "input_sha256": hashlib.sha256(
            input_path.read_bytes()).hexdigest(),
        "null_field_counts": null_counts,
        "unknown_field_counts": unknown_field_counts,
        "splits": {},
    }
    index_path = out_dir / "index.jsonl"
    index_hasher = hashlib.sha256()
    with index_path.open("wb") as index_fh:
        for split in ("train", "holdout"):
            token_buf = array.array("I")
            rec_count = 0
            for rec in records[split]:
                ids = enc.encode(canonical_text(rec))
                if args.max_tokens and len(ids) > args.max_tokens:
                    ids = ids[: args.max_tokens]
                offset = len(token_buf)
                token_buf.extend(ids)
                rec_count += 1
                idx_line = json.dumps({
                    "observation_id": rec["observation_id"],
                    "contamination_group": rec.get("contamination_group"),
                    "split": split,
                    "token_offset": offset,
                    "token_count": len(ids),
                }, sort_keys=True).encode("utf-8") + b"\n"
                index_fh.write(idx_line)
                index_hasher.update(idx_line)
            bin_path = out_dir / f"{split}.bin"
            bin_path.write_bytes(token_buf.tobytes())
            manifest["splits"][split] = {
                "record_count": rec_count,
                "token_count": len(token_buf),
                "bin_file": bin_path.name,
                "bin_sha256": hashlib.sha256(
                    bin_path.read_bytes()).hexdigest(),
                "dtype": "uint32-le",
            }
    manifest["index_file"] = index_path.name
    manifest["index_sha256"] = index_hasher.hexdigest()
    manifest["total_records"] = n_in

    manifest_path = out_dir / "dataset_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps({
        "records": n_in,
        "train_tokens": manifest["splits"]["train"]["token_count"],
        "holdout_tokens": manifest["splits"]["holdout"]["token_count"],
        "manifest": str(manifest_path),
    }))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True,
                   help="Path to canonical observation JSONL corpus.")
    p.add_argument("--split-manifest", required=True,
                   help="JSON object mapping observation_id -> "
                        "'train'|'holdout'. Splits are NEVER invented.")
    p.add_argument("--output-dir", required=True,
                   help="Directory for packed outputs.")
    p.add_argument("--seed", type=int, required=True,
                   help="Explicit shuffle seed (required for determinism).")
    p.add_argument("--tokenizer", default="r50k_base",
                   help="tiktoken encoding name or path to a .tiktoken BPE "
                        "file (default: r50k_base).")
    p.add_argument("--schema",
                   default="docs/research/EXP-M6-SLM/observation.schema.json",
                   help="Path to observation JSON schema.")
    p.add_argument("--max-tokens", type=int, default=0,
                   help="Optional per-record token cap (0 = no cap).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return compile_dataset(args)


if __name__ == "__main__":
    raise SystemExit(main())
