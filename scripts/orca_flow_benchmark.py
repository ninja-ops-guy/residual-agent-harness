#!/usr/bin/env python3
"""Run the Orca-derived flow development benchmark and optionally retain JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from residual.orchestrator.flow_benchmark import run_flow_benchmark


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=250)
    parser.add_argument("--output")
    args = parser.parse_args()

    report = run_flow_benchmark(iterations=args.iterations)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload + "\n", encoding="utf-8")

    summary = report["summary"]
    print(payload)
    print(
        "ORCA_FLOW_BENCHMARK "
        f"material_architecture_efficiency_signal={summary['material_architecture_efficiency_signal']} "
        f"live_execution_improvement_proven={summary['live_execution_improvement_proven']}"
    )
    return 0 if summary["material_architecture_efficiency_signal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
