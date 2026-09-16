#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from residual.qualification.evidence import GateResult, load_envelope
from residual.qualification.failures import (
    FailureClass,
    FailureObservation,
    append_failure,
)
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


def _record(ledger: Path | None, gate: str, classification: FailureClass,
            summary: str, evidence: dict) -> None:
    if ledger is None:
        return
    append_failure(ledger, FailureObservation(
        gate_id=gate,
        classification=classification,
        summary=summary,
        evidence=evidence,
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate Qualification v1 CI artifacts")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--failure-ledger", type=Path)
    args = parser.parse_args(argv)

    evidence = sorted(args.root.rglob("*.evidence.json"))
    wheels = sorted(args.root.rglob("*.whl"))
    if args.failure_ledger:
        args.failure_ledger.parent.mkdir(parents=True, exist_ok=True)
        args.failure_ledger.unlink(missing_ok=True)

    if len(wheels) != 1:
        _record(
            args.failure_ledger,
            "artifact-set",
            FailureClass.PROVENANCE_UNKNOWN,
            f"expected exactly one promoted wheel, found {len(wheels)}",
            {"wheels": [str(path) for path in wheels]},
        )
        print(f"expected exactly one promoted wheel, found {len(wheels)}", file=sys.stderr)
        return 1

    loaded = {}
    for path in evidence:
        try:
            envelope = load_envelope(path)
        except Exception as exc:
            _record(
                args.failure_ledger,
                "evidence-envelope",
                FailureClass.PROVENANCE_UNKNOWN,
                f"unreadable evidence envelope: {path}",
                {"path": str(path), "error": f"{type(exc).__name__}: {exc}"},
            )
            continue
        loaded[envelope.gate_id] = envelope

    for gate in REQUIRED_GATES:
        envelope = loaded.get(gate)
        if envelope is None:
            _record(
                args.failure_ledger,
                gate,
                FailureClass.PROVENANCE_UNKNOWN,
                "required qualification evidence is missing",
                {},
            )
            continue
        if envelope.result != GateResult.PASS or envelope.unknown_count:
            classification = (
                FailureClass.PROVENANCE_UNKNOWN
                if envelope.result == GateResult.UNKNOWN or envelope.unknown_count
                else FailureClass.UNCLASSIFIED
            )
            _record(
                args.failure_ledger,
                gate,
                classification,
                "required qualification gate did not establish PASS",
                {
                    "result": envelope.result.value,
                    "unknown_count": envelope.unknown_count,
                    "skip_count": envelope.skip_count,
                    "source": envelope.source,
                    "notes": envelope.notes,
                },
            )

    try:
        manifest = aggregate_manifest(evidence, required_gates=REQUIRED_GATES, artifact_paths=wheels)
    except Exception as exc:
        _record(
            args.failure_ledger,
            "qualification-aggregate",
            FailureClass.PROVENANCE_UNKNOWN,
            "qualification evidence could not be aggregated",
            {"error": f"{type(exc).__name__}: {exc}"},
        )
        print(f"qualification aggregation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    write_manifest(manifest, args.output)
    print(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
    return 0 if manifest.result == GateResult.PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
