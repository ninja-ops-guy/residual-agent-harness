#!/usr/bin/env python3
"""Generate deterministic Swarm 5 development-fixture evidence."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from residual.core import canonical
from residual.eval_frozen.economics import build_swarm5_evidence


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=root, check=True, capture_output=True, text=True,
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("runs/swarm5"))
    parser.add_argument("--commit", help="tested implementation commit; defaults to HEAD")
    args = parser.parse_args()
    root = ROOT
    commit = args.commit or git(root, "rev-parse", "HEAD")
    tree = git(root, "rev-parse", f"{commit}^{{tree}}")
    evidence = build_swarm5_evidence(commit, tree)
    output = args.output if args.output.is_absolute() else root / args.output
    output.mkdir(parents=True, exist_ok=True)
    documents = {
        "raw-timing-observations.json": {
            "schema_version": evidence["schema_version"],
            "observations": evidence["raw_timing_observations"],
        },
        "topology-decisions.json": {
            "schema_version": "residual.topology-decision-log.v1",
            "decisions": evidence["topology_decision_log"],
        },
        "orchestration-tax.json": evidence["orchestration_tax_snapshot"],
        "aggregate-report.json": evidence["aggregate_report"],
        "pareto-inputs.json": evidence["pareto_inputs"],
        "evidence.json": evidence,
    }
    for name, document in documents.items():
        (output / name).write_text(canonical(document) + "\n", encoding="utf-8")
    (output / "report.sha256").write_text(str(evidence["report_sha256"]) + "\n",
                                          encoding="ascii")
    print(json.dumps({"output": str(output), "report_sha256": evidence["report_sha256"],
                      "evidence_sha256": evidence["evidence_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
