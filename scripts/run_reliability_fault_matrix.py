#!/usr/bin/env python3
"""Run the development fault matrix and emit explicit experiment receipts.

This script is for development evidence. It does not relabel bundled fixtures as
confirmatory or independent external validation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from residual.config import build_harness, load_config
from residual.core import canonical
from residual.reliability_experiment_report import build_experiment_report
from residual.reliability_experiments import FAULT_KINDS, FaultSpec, run_fault_trial
from residual.study import load_suite
from residual.study_tasks import grade


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run controlled RESIDUAL fault-injection fixture trials")
    parser.add_argument("--suite", default="examples/study/suite.json")
    parser.add_argument("--config", default="examples/study-fixture.toml")
    parser.add_argument("--output", required=True, help="output directory")
    parser.add_argument("--split", choices=["development", "evaluation"], default="evaluation")
    parser.add_argument("--mode", default="full_cloud")
    parser.add_argument("--role", choices=["local", "expert"], default="expert")
    args = parser.parse_args(argv)

    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    config = load_config(args.config)
    suite, cases = load_suite(args.suite)
    selected = [(entry, task, grader) for entry, task, grader in cases if entry["split"] == args.split]
    receipts = []

    for entry, task, grader_spec in selected:
        for kind in sorted(FAULT_KINDS):
            harness = build_harness(config, mode=args.mode, disable_cache=True)
            spec = FaultSpec(f"{entry['id']}:{kind}", kind, args.role)
            receipt = run_fault_trial(
                harness,
                task,
                spec,
                lambda values, g=grader_spec: bool(grade(values, g)["pass"]),
            )
            receipt["case_id"] = entry["id"]
            receipt["family"] = entry["family"]
            receipt["split"] = entry["split"]
            receipts.append(receipt)

    (output / "fault-trials.jsonl").write_text("".join(canonical(r) + "\n" for r in receipts), encoding="utf-8")
    report = build_experiment_report(receipts)
    report["suite_name"] = suite["name"]
    report["evidence_level"] = suite["evidence_level"]
    report["split"] = args.split
    report["development_only"] = suite["evidence_level"] != "independently_authored"
    (output / "fault-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Recorded {len(receipts)} controlled fault trials across {len(selected)} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
