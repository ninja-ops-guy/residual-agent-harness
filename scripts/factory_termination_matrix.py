#!/usr/bin/env python3
"""Repeat the two Swarm-3 suspect runtime cases under controlled host contention."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import unittest

RAW_TEST = "test_raw_file_syscall_is_kernel_killed"
OLD_BLOCKED_TEST = "test_watchdog_kills_even_when_audit_callback_is_blocked"
NEW_BLOCKED_TEST = "test_watchdog_termination_is_independent_of_blocked_audit_callback"


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _load_execution_tests(repo: Path):
    """Child-interpreter only: never import a target into the caller process."""
    repo = repo.resolve()
    sys.path.insert(0, str(repo))
    path = repo / "tests" / "test_factory_runtime.py"
    spec = importlib.util.spec_from_file_location("swarm3_target_factory_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    cls = module.ExecutionTests
    blocked = NEW_BLOCKED_TEST if hasattr(cls, NEW_BLOCKED_TEST) else OLD_BLOCKED_TEST
    if not hasattr(cls, RAW_TEST) or not hasattr(cls, blocked):
        raise RuntimeError("required Swarm-3 tests are missing")
    return cls, blocked


class RecordingResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.stats: dict[str, dict[str, int]] = {}
        self.details: list[dict[str, str]] = []

    def _row(self, test) -> dict[str, int]:
        name = getattr(test, "_testMethodName", test.id())
        return self.stats.setdefault(name, {"runs": 0, "failures": 0, "errors": 0, "skips": 0})

    def startTest(self, test):
        self._row(test)["runs"] += 1
        super().startTest(test)

    def addFailure(self, test, err):
        self._row(test)["failures"] += 1
        self.details.append({"test": test.id(), "kind": "failure", "traceback": "".join(traceback.format_exception(*err))})
        super().addFailure(test, err)

    def addError(self, test, err):
        self._row(test)["errors"] += 1
        self.details.append({"test": test.id(), "kind": "error", "traceback": "".join(traceback.format_exception(*err))})
        super().addError(test, err)

    def addSkip(self, test, reason):
        self._row(test)["skips"] += 1
        self.details.append({"test": test.id(), "kind": "skip", "traceback": reason})
        super().addSkip(test, reason)


@contextmanager
def contention(kind: str):
    stop = threading.Event()
    burners: list[subprocess.Popen] = []
    io_thread = None
    temp = None
    try:
        if kind in {"cpu", "combined"}:
            count = max(1, min(4, os.cpu_count() or 1))
            for _ in range(count):
                burners.append(subprocess.Popen(
                    [sys.executable, "-c", "while True: pass"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                ))
        if kind in {"io", "combined"}:
            temp = tempfile.TemporaryDirectory()
            target = Path(temp.name) / "pressure.bin"
            block = b"x" * (1024 * 1024)

            def write_pressure():
                while not stop.is_set():
                    try:
                        with target.open("wb", buffering=0) as stream:
                            for _ in range(8):
                                stream.write(block)
                            os.fsync(stream.fileno())
                    except OSError:
                        return

            io_thread = threading.Thread(target=write_pressure, daemon=True)
            io_thread.start()
        yield {"cpu_processes": len(burners), "io_pressure": io_thread is not None}
    finally:
        stop.set()
        if io_thread is not None:
            io_thread.join(timeout=2)
        for process in burners:
            process.terminate()
        for process in burners:
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        if temp is not None:
            temp.cleanup()


def upper_95_zero_failures(n: int) -> float | None:
    if n <= 0:
        return None
    return 1.0 - math.pow(0.05, 1.0 / n)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--condition", choices=("normal", "cpu", "io", "combined"), required=True)
    parser.add_argument("--runs", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-failures", action="store_true")
    args = parser.parse_args(argv)
    if args.runs < 1:
        parser.error("--runs must be positive")

    return args


def main(argv: list[str] | None = None) -> int:
    """Run each repository in a fresh interpreter, including calls from pytest.

    Restoring sys.path alone is insufficient: sys.modules can retain a different
    baseline/candidate implementation. The parent never imports the target.
    """
    args = _parse_args(argv)
    command = [sys.executable, '-I', str(Path(__file__).resolve()), '--matrix-worker',
               '--repo-root', str(args.repo_root.resolve()), '--condition', args.condition,
               '--runs', str(args.runs), '--output', str(args.output.resolve())]
    if args.allow_failures:
        command.append('--allow-failures')
    return subprocess.run(command, check=False).returncode


def _run_matrix(argv: list[str]) -> int:
    args = _parse_args(argv)
    repo = args.repo_root.resolve()
    tests, blocked_test = _load_execution_tests(repo)
    suite = unittest.TestSuite()
    for _ in range(args.runs):
        suite.addTest(tests(RAW_TEST))
        suite.addTest(tests(blocked_test))

    started_ns = time.monotonic_ns()
    with contention(args.condition) as load:
        result = RecordingResult()
        suite.run(result)
    finished_ns = time.monotonic_ns()

    stats = result.stats
    for row in stats.values():
        unexplained = row["failures"] + row["errors"]
        row["unexplained_failures"] = unexplained
        row["zero_failure_upper_95"] = upper_95_zero_failures(row["runs"]) if unexplained == 0 and row["skips"] == 0 else None

    report = {
        "schema_version": "swarm3-termination-matrix-v1",
        "repo_root": str(repo),
        "commit": git(repo, "rev-parse", "HEAD"),
        "tree": git(repo, "rev-parse", "HEAD^{tree}"),
        "condition": args.condition,
        "runs_per_test": args.runs,
        "tests": {"raw_seccomp": RAW_TEST, "blocked_audit": blocked_test},
        "load": load,
        "started_monotonic_ns": started_ns,
        "finished_monotonic_ns": finished_ns,
        "duration_s": (finished_ns - started_ns) / 1_000_000_000,
        "stats": stats,
        "details": result.details,
        "claim_boundary": "Zero failures establish only the reported statistical upper bound; they do not prove determinism.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True, indent=2))

    failed = any(row["failures"] or row["errors"] for row in stats.values())
    skipped = any(row["skips"] for row in stats.values())
    if skipped:
        return 2
    return 0 if args.allow_failures or not failed else 1


if __name__ == "__main__":
    if sys.argv[1:2] == ['--matrix-worker']:
        raise SystemExit(_run_matrix(sys.argv[2:]))
    raise SystemExit(main())
