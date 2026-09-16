#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from residual.qualification.evidence import GateResult
from residual.qualification.manifest import aggregate_manifest, write_manifest

REQUIRED_GATES = (
    "deterministic-regression",
    "stateful-runtime-journal",
    "distributed-history",
    "mutation-canary",
    "coverage-strength",
    "m4-capability",
    "m4-zero-skip",
    "exact-wheel",
    "container-smoke",
    "browser-chromium",
    "browser-firefox",
    "browser-webkit",
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate Qualification v1 CI artifacts")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    evidence = sorted(args.root.rglob("*.evidence.json"))
    wheels = sorted(args.root.rglob("*.whl"))
    if len(wheels) != 1:
        print(f"expected exactly one promoted wheel, found {len(wheels)}", file=sys.stderr)
        return 1
    try:
        manifest = aggregate_manifest(evidence, required_gates=REQUIRED_GATES, artifact_paths=wheels)
    except Exception as exc:
        print(f"qualification aggregation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    write_manifest(manifest, args.output)
    print(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
    return 0 if manifest.result == GateResult.PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
