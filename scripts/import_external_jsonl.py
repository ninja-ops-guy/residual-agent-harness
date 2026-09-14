"""Convert independently authored JSONL benchmark data into Residual external-suite v1.

This is a deterministic format adapter, not a benchmark author. The output suite
preserves evaluator-supplied authorship/source metadata and hashes the converted
cases through the normal external-suite loader.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def stable_bucket(case_id: str, salt: str) -> int:
    raw = hashlib.sha256(f"{salt}\0{case_id}".encode("utf-8")).digest()
    return int.from_bytes(raw[:8], "big") % 10000


def read_jsonl(path: Path):
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {number}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"line {number} must be an object")
        rows.append(item)
    if len(rows) < 2:
        raise ValueError("source requires at least two cases")
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description="Import an external JSONL benchmark deterministically")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--source-uri", required=True)
    parser.add_argument("--authored-at", required=True)
    parser.add_argument("--id-key", default="id")
    parser.add_argument("--prompt-key", default="prompt")
    parser.add_argument("--answer-key", default="answer")
    parser.add_argument("--capability", default="text")
    parser.add_argument("--assurance", default="routine", choices=("routine", "sensitive", "critical"))
    parser.add_argument("--required-pass-rate", type=float, default=0.5)
    parser.add_argument("--train-percent", type=int, default=20)
    parser.add_argument("--split-salt", required=True)
    args = parser.parse_args(argv)

    if not 1 <= args.train_percent <= 99:
        raise SystemExit("--train-percent must be in [1,99]")
    if not 0 <= args.required_pass_rate <= 1:
        raise SystemExit("--required-pass-rate must be in [0,1]")

    source = Path(args.input)
    rows = read_jsonl(source)
    cases = []
    seen = set()
    threshold = args.train_percent * 100
    for index, item in enumerate(rows):
        case_id = str(item.get(args.id_key, index))
        if not case_id or case_id in seen:
            raise ValueError("case ids must be non-empty and unique")
        seen.add(case_id)
        prompt = item.get(args.prompt_key)
        answer = item.get(args.answer_key)
        if not isinstance(prompt, str) or not isinstance(answer, (str, int, float, bool)):
            raise ValueError(f"case {case_id} requires a text prompt and scalar answer")
        split = "train" if stable_bucket(case_id, args.split_salt) < threshold else "evaluation"
        cases.append({
            "id": case_id,
            "split": split,
            "capability": args.capability,
            "assurance": args.assurance,
            "required_pass_rate": args.required_pass_rate,
            "prompt": prompt,
            "grader": {"kind": "exact_text", "expected": str(answer)},
        })

    if not any(c["split"] == "train" for c in cases) or not any(c["split"] == "evaluation" for c in cases):
        raise ValueError("deterministic split produced an empty partition; change train percent or salt")

    source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    payload = {
        "schema_version": "residual.external-suite.v1",
        "name": args.name,
        "provenance": {
            "evidence_level": "externally_authored",
            "author": args.author,
            "source_uri": f"{args.source_uri}#source-sha256={source_sha256}",
            "authored_at": args.authored_at,
        },
        "cases": cases,
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "cases": len(cases),
        "train": sum(c["split"] == "train" for c in cases),
        "evaluation": sum(c["split"] == "evaluation" for c in cases),
        "source_sha256": source_sha256,
        "output": str(target),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
