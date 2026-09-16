#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from residual.qualification.evidence import GateResult, new_envelope, write_envelope


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Bind an existing machine report into a Qualification v1 evidence envelope")
    parser.add_argument("--gate-id", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--non-claim", action="append", default=[])
    args = parser.parse_args(argv)

    raw = json.loads(args.report.read_text(encoding="utf-8"))
    try:
        result = GateResult(str(raw["result"]).upper())
    except (KeyError, ValueError) as exc:
        raise SystemExit(f"report has no valid result: {exc}")
    envelope = new_envelope(
        args.gate_id,
        result,
        root=ROOT,
        command=["report", str(args.report)],
        evidence_paths=[args.report],
        unknown_count=1 if result == GateResult.UNKNOWN else 0,
        notes=[str(reason) for reason in raw.get("reasons", [])],
        non_claims=args.non_claim,
    )
    write_envelope(envelope, args.output)
    print(json.dumps(envelope.to_dict(), indent=2, sort_keys=True))
    if result == GateResult.PASS:
        return 0
    if result == GateResult.UNKNOWN:
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
