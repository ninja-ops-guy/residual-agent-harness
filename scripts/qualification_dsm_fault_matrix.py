#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from residual.dsm.evidence import generate_evidence

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate and validate DSM duplicate/delay/reorder/loss qualification evidence")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    path, sha256 = generate_evidence(args.output_dir, ROOT)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    results = artifact.get("results") or {}
    fault = artifact.get("fault_matrix") or {}
    recovery = artifact.get("recovery_suite") or {}
    passed = bool(
        results.get("ok")
        and results.get("fault_matrix_ok")
        and results.get("no_duplicate_accepted_transition")
        and fault.get("all_converged")
        and fault.get("all_idempotent")
        and recovery.get("ok")
    )
    summary = {
        "schema": "residual.qualification.dsm-fault-matrix.v1",
        "result": "PASS" if passed else "FAIL",
        "artifact": str(path),
        "sha256": sha256,
        "source_identity": artifact.get("source_identity"),
        "fault_matrix_ok": fault.get("ok"),
        "fault_cases": [
            {
                "schedule": case.get("schedule"),
                "converged": case.get("converged"),
                "idempotent": case.get("idempotent"),
                "duplicate_deliveries": case.get("duplicate_deliveries"),
                "retransmitted": case.get("retransmitted"),
            }
            for case in fault.get("matrix", [])
        ],
        "recovery_ok": recovery.get("ok"),
        "no_duplicate_accepted_transition": results.get("no_duplicate_accepted_transition"),
        "non_claim": "DSM evidence covers the documented single-writer crash-stop boundary; it does not claim split-brain-safe consensus.",
    }
    summary_path = args.output_dir / "qualification-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
