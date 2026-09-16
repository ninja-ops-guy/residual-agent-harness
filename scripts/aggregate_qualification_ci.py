#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from residual.dsm.evidence import generate_evidence
from residual.qualification.evidence import (
    GateResult,
    load_envelope,
    new_envelope,
    write_envelope,
)
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
    "dsm-fault-matrix",
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


def _record(ledger: Path, gate: str, classification: FailureClass,
            summary: str, evidence: dict) -> None:
    append_failure(ledger, FailureObservation(
        gate_id=gate,
        classification=classification,
        summary=summary,
        evidence=evidence,
    ))


def _dsm_gate(output_root: Path) -> Path:
    """Run the repository's real DSM duplicate/delay/reorder/loss + recovery matrix."""
    dsm_dir = output_root / "dsm"
    artifact, _sha = generate_evidence(dsm_dir, ROOT)
    raw = json.loads(artifact.read_text(encoding="utf-8"))
    results = raw.get("results") or {}
    fault = raw.get("fault_matrix") or {}
    recovery = raw.get("recovery_suite") or {}
    passed = bool(
        results.get("ok")
        and results.get("fault_matrix_ok")
        and results.get("no_duplicate_accepted_transition")
        and fault.get("all_converged")
        and fault.get("all_idempotent")
        and recovery.get("ok")
    )
    envelope = new_envelope(
        "dsm-fault-matrix",
        GateResult.PASS if passed else GateResult.FAIL,
        root=ROOT,
        command=["residual.dsm.evidence.generate_evidence"],
        evidence_paths=[artifact],
        notes=[
            "real DSM fault matrix: duplicate, delayed, reordered, lost and combined delivery",
            "recovery suite includes crash/restart/replay and duplicate accepted-transition checks",
        ],
        non_claims=[
            "DSM qualification applies to the documented single-writer crash-stop boundary; it is not a split-brain consensus claim."
        ],
    )
    path = dsm_dir / "dsm-fault-matrix.evidence.json"
    write_envelope(envelope, path)
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate Qualification v1 CI artifacts")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--failure-ledger", type=Path)
    args = parser.parse_args(argv)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    ledger = args.failure_ledger or args.output.with_name("failure-ledger.jsonl")
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("", encoding="utf-8")

    dsm_evidence = _dsm_gate(args.output.parent)
    evidence = sorted(args.root.rglob("*.evidence.json")) + [dsm_evidence]
    wheels = sorted(args.root.rglob("*.whl"))
    if len(wheels) != 1:
        _record(
            ledger,
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
                ledger,
                "evidence-envelope",
                FailureClass.PROVENANCE_UNKNOWN,
                f"unreadable evidence envelope: {path}",
                {"path": str(path), "error": f"{type(exc).__name__}: {exc}"},
            )
            continue
        if envelope.gate_id in loaded:
            _record(
                ledger,
                envelope.gate_id,
                FailureClass.PROVENANCE_UNKNOWN,
                "duplicate qualification gate evidence observed",
                {"path": str(path)},
            )
        loaded[envelope.gate_id] = envelope

    for gate in REQUIRED_GATES:
        envelope = loaded.get(gate)
        if envelope is None:
            _record(
                ledger,
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
                ledger,
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
            ledger,
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
