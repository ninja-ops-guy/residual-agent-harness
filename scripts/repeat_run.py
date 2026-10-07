#!/usr/bin/env python3
"""Run a test module N times and report machine-readable determinism evidence.

For each repetition the per-test outcome map (test id -> outcome) is captured
and compared against the first run. Any divergence in the outcome map, or any
failing run, makes the script exit 1.

Usage:
    python scripts/repeat_run.py tests.test_factory_runtime --times 20
    python scripts/repeat_run.py tests.test_sandbox_containment --runner pytest

Output: one JSON document on stdout with the run count, per-run outcome
hashes, and the divergence list (empty when fully deterministic).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path


def _run_unittest(module: str, cwd: Path) -> tuple[int, dict[str, str], str]:
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", module, "-v"],
        cwd=cwd, capture_output=True, text=True, timeout=3600)
    outcomes: dict[str, str] = {}
    for line in proc.stderr.splitlines():
        for marker in (" ... ok", " ... FAIL", " ... ERROR", " ... skipped"):
            if marker in line:
                test_id, _, tail = line.partition(" ... ")
                outcomes[test_id.strip()] = tail.split()[0] if tail else "unknown"
                break
    return proc.returncode, outcomes, proc.stderr


def _run_pytest(module: str, cwd: Path) -> tuple[int, dict[str, str], str]:
    path = module.replace(".", "/") + ".py"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", path, "-v", "--tb=no", "-p", "no:cacheprovider"],
        cwd=cwd, capture_output=True, text=True, timeout=3600)
    outcomes: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "::" in line:
            test_id, _, status = line.partition(" ")
            outcomes[test_id.strip()] = status.strip().split()[0] if status.strip() else "unknown"
    return proc.returncode, outcomes, proc.stdout


def _detect_runner(module: str, cwd: Path) -> str:
    path = cwd / (module.replace(".", "/") + ".py")
    try:
        text = path.read_text()
    except OSError:
        return "unittest"
    if "import pytest" in text or "from pytest" in text:
        return "pytest"
    return "unittest"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", help="dotted test module, e.g. tests.test_factory_runtime")
    parser.add_argument("--times", type=int, default=20)
    parser.add_argument("--runner", choices=("auto", "unittest", "pytest"), default="auto")
    parser.add_argument("--output", help="optional path for the JSON report")
    args = parser.parse_args(argv)
    if args.times < 1:
        parser.error("--times must be >= 1")

    cwd = Path(__file__).resolve().parents[1]
    runner = _detect_runner(args.module, cwd) if args.runner == "auto" else args.runner
    execute = _run_pytest if runner == "pytest" else _run_unittest

    runs = []
    baseline: dict[str, str] | None = None
    divergences = []
    failed_runs = []
    for index in range(args.times):
        returncode, outcomes, _raw = execute(args.module, cwd)
        digest = hashlib.sha256(
            json.dumps(outcomes, sort_keys=True).encode()).hexdigest()
        runs.append({"run": index, "returncode": returncode,
                     "tests": len(outcomes), "outcome_sha256": digest})
        if returncode != 0:
            failed_runs.append(index)
        if baseline is None:
            baseline = outcomes
        elif outcomes != baseline:
            diff = {t: (baseline.get(t), outcomes.get(t))
                    for t in set(baseline) | set(outcomes)
                    if baseline.get(t) != outcomes.get(t)}
            divergences.append({"run": index, "diff": diff})
        print(f"run {index + 1}/{args.times}: rc={returncode} "
              f"tests={len(outcomes)} sha={digest[:12]}", file=sys.stderr)

    deterministic = not divergences and not failed_runs
    report = {
        "module": args.module,
        "runner": runner,
        "times": args.times,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "runs": runs,
        "failed_runs": failed_runs,
        "divergences": divergences,
        "deterministic": deterministic,
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n")
    print(text)
    return 0 if deterministic else 1


if __name__ == "__main__":
    raise SystemExit(main())
