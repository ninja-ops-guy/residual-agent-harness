#!/usr/bin/env python3
"""Research CI validator for the SLM data toolchain.

Validates, fail-closed (exit nonzero on any violation):
  * observation records (JSONL) against observation.schema.json
  * packed dataset manifests against research/slm/dataset/manifest.schema.json
  * tokenizer artifacts (.tiktoken files load and round-trip encode)
  * evaluation outputs against a caller-provided JSON schema

Usage:
    python research_ci.py \
        --observations observations.jsonl \
        --observation-schema docs/research/EXP-M6-SLM/observation.schema.json \
        --dataset-manifest out/dataset_manifest.json \
        --tokenizer-artifact residual_bpe.tiktoken \
        --eval-output eval.json --eval-schema eval.schema.json

All checks are independent; every failing check is reported before exit.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

EXIT_VIOLATION = 1


def report(ok: bool, label: str, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    line = f"[{status}] {label}"
    if detail:
        line += f": {detail}"
    print(line, file=sys.stderr if not ok else sys.stdout)
    return ok


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)


def make_validator(schema_path: Path):
    import jsonschema
    schema, err = load_json(schema_path)
    if err:
        return None, f"cannot load schema {schema_path}: {err}"
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError as exc:
        return None, f"invalid schema {schema_path}: {exc.message}"
    return jsonschema.Draft202012Validator(schema), None


def check_observations(jsonl_path: Path, schema_path: Path) -> bool:
    validator, err = make_validator(schema_path)
    if err:
        return report(False, "observations", err)
    failures = 0
    count = 0
    try:
        fh = jsonl_path.open("r", encoding="utf-8")
    except OSError as exc:
        return report(False, "observations", str(exc))
    with fh:
        for lineno, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            count += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                report(False, "observations",
                       f"line {lineno}: invalid JSON: {exc}")
                failures += 1
                continue
            for error in validator.iter_errors(rec):
                loc = "/".join(str(p) for p in error.path) or "<root>"
                report(False, "observations",
                       f"line {lineno} at {loc}: {error.message}")
                failures += 1
                break  # one report per record is enough
    return report(failures == 0, "observations",
                  f"{count} records, {failures} violations")


def check_dataset_manifest(manifest_path: Path, schema_path: Path) -> bool:
    validator, err = make_validator(schema_path)
    if err:
        return report(False, "dataset-manifest", err)
    manifest, err = load_json(manifest_path)
    if err:
        return report(False, "dataset-manifest", err)
    errors = sorted(validator.iter_errors(manifest), key=lambda e: e.path)
    if errors:
        for error in errors[:5]:
            loc = "/".join(str(p) for p in error.path) or "<root>"
            report(False, "dataset-manifest", f"at {loc}: {error.message}")
        return False
    # Cross-check referenced files + hashes when present on disk.
    base = manifest_path.parent
    import hashlib
    ok = True
    for split, info in manifest.get("splits", {}).items():
        bin_file = base / info.get("bin_file", "")
        if bin_file.exists():
            digest = hashlib.sha256(bin_file.read_bytes()).hexdigest()
            if digest != info.get("bin_sha256"):
                ok = report(False, "dataset-manifest",
                            f"{split}: bin sha256 mismatch for {bin_file}")
    return report(ok, "dataset-manifest", str(manifest_path))


def check_tokenizer_artifact(path: Path) -> bool:
    if not path.exists():
        return report(False, "tokenizer-artifact", f"not found: {path}")
    ranks: dict[bytes, int] = {}
    try:
        for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) != 2:
                raise ValueError(f"line {lineno}: expected 2 columns")
            token = base64.b64decode(parts[0], validate=True)
            rank = int(parts[1])
            if rank in ranks.values():
                raise ValueError(f"line {lineno}: duplicate rank {rank}")
            ranks[token] = rank
    except ValueError as exc:
        return report(False, "tokenizer-artifact", str(exc))
    missing_bytes = [b for b in range(256) if bytes([b]) not in ranks]
    if missing_bytes:
        return report(False, "tokenizer-artifact",
                      f"missing {len(missing_bytes)} base byte tokens")
    # Round-trip via tiktoken if available (advisory, not required).
    try:
        import tiktoken
        enc = tiktoken.Encoding(
            name=path.stem,
            pat_str=(r"'(?i:[sdmt]|ll|ve|re)|[^\r\n\p{L}\p{N}]?+\p{L}++"
                     r"|\p{N}{1,3}+| ?[^\s\p{L}\p{N}]++[\r\n]*+|\s++$"
                     r"|\s*[\r\n]|\s+(?!\S)|\s+"),
            mergeable_ranks=ranks,
            special_tokens={},
        )
        sample = "residual-agent-harness smoke test 123"
        assert enc.decode(enc.encode(sample)) == sample
    except ImportError:
        pass  # tiktoken optional for CI validation
    except Exception as exc:  # round-trip failure is a violation
        return report(False, "tokenizer-artifact",
                      f"round-trip failed: {exc}")
    return report(True, "tokenizer-artifact",
                  f"{path.name}: {len(ranks)} ranks")


def check_eval_output(output_path: Path, schema_path: Path) -> bool:
    validator, err = make_validator(schema_path)
    if err:
        return report(False, "eval-output", err)
    data, err = load_json(output_path)
    if err:
        return report(False, "eval-output", err)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        for error in errors[:5]:
            loc = "/".join(str(p) for p in error.path) or "<root>"
            report(False, "eval-output", f"at {loc}: {error.message}")
        return False
    return report(True, "eval-output", str(output_path))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--observations",
                   help="Observation JSONL file to validate.")
    p.add_argument("--observation-schema",
                   default="docs/research/EXP-M6-SLM/observation.schema.json",
                   help="Schema for --observations.")
    p.add_argument("--dataset-manifest",
                   help="Packed dataset manifest JSON to validate.")
    p.add_argument("--dataset-manifest-schema",
                   default="research/slm/dataset/manifest.schema.json",
                   help="Schema for --dataset-manifest.")
    p.add_argument("--tokenizer-artifact", action="append", default=[],
                   help=".tiktoken file to validate (repeatable).")
    p.add_argument("--eval-output",
                   help="Evaluation output JSON to validate.")
    p.add_argument("--eval-schema",
                   help="Schema for --eval-output (required with it).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    checks = []
    if args.observations:
        checks.append(check_observations(
            Path(args.observations), Path(args.observation_schema)))
    if args.dataset_manifest:
        checks.append(check_dataset_manifest(
            Path(args.dataset_manifest),
            Path(args.dataset_manifest_schema)))
    for artifact in args.tokenizer_artifact:
        checks.append(check_tokenizer_artifact(Path(artifact)))
    if args.eval_output:
        if not args.eval_schema:
            report(False, "eval-output",
                   "--eval-schema is required with --eval-output")
            checks.append(False)
        else:
            checks.append(check_eval_output(
                Path(args.eval_output), Path(args.eval_schema)))
    if not checks:
        report(False, "research-ci", "no checks requested; nothing to do")
        return EXIT_VIOLATION
    ok = all(checks)
    print(f"research-ci: {sum(checks)}/{len(checks)} checks passed")
    return 0 if ok else EXIT_VIOLATION


if __name__ == "__main__":
    raise SystemExit(main())
