#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from residual.soak import SoakConfig, SoakHarness


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic RESIDUAL virtual-day soak")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--tasks-per-day", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260916)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.days < 1 or args.tasks_per_day < 1:
        parser.error("days and tasks-per-day must be positive")

    config = SoakConfig(seed=args.seed, total_days=args.days, tasks_per_day=args.tasks_per_day)
    harness = SoakHarness(config, b"qualification-v1", state_path=str(args.state),
                          enforce_load_minimum=args.tasks_per_day >= 1000)
    state = harness.run(resume=True, redteam=True)
    report = harness.report(signed=False)
    report["qualification"] = {
        "kind": "deterministic_virtual_day_soak",
        "seed": args.seed,
        "configured_days": args.days,
        "tasks_per_day": args.tasks_per_day,
        "completed_days": state.days_completed,
        "non_claim": "Virtual-day fixture evidence is not wall-clock production soak evidence.",
    }
    passed = bool(report.get("all_targets_passed")) and state.days_completed == args.days
    report["qualification"]["result"] = "PASS" if passed else "FAIL"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
