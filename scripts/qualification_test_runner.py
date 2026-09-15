#!/usr/bin/env python3
"""Run unittest discovery once, retaining incremental diagnostic evidence.

This does not retry, relax assertions, classify missing evidence, or qualify
namespace isolation. Only the existing Factory fixture's run_source boundary
is observed; direct runtime calls and results that never return are not captured.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import functools
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Match `python -m unittest` import precedence when invoked as a script.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CI_FIELDS = (
    "GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_REF", "GITHUB_EVENT_NAME",
    "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_JOB", "GITHUB_WORKFLOW",
    "QUALIFICATION_HEAD_SHA", "QUALIFICATION_BASE_SHA",
)
RUNTIME_FIELDS = ("attempt_id", "returncode", "status", "process_reaped", "usage")
TERMINATION_FIELDS = (
    "correlation_id", "pid", "pid_start_time_ticks", "boot_id", "requested_by",
    "request_boundary", "request_field", "requested_monotonic_ns",
    "observed_monotonic_ns", "reaped_monotonic_ns", "returncode",
    "observed_signal", "waitid_code", "waitid_status", "classification",
    "cgroup_memory_events_before", "cgroup_memory_events_after",
    "cgroup_oom_kill_delta", "kernel_audit_evidence",
)
ACTION_FIELDS = ("reason", "elapsed_s", "resident_bytes", "read_error_type", "sqlite_errorcode")


def metadata(root: Path) -> dict:
    def git(*args):
        return subprocess.check_output(
            ["git", "--no-replace-objects", "-C", str(root), *args],
            text=True, stderr=subprocess.PIPE, timeout=30,
        ).strip()
    return {
        "commit": git("rev-parse", "HEAD"),
        "tree": git("rev-parse", "HEAD^{tree}"),
        "dirty": bool(git("status", "--porcelain", "--untracked-files=normal")),
        "python": platform.python_version(), "platform": platform.platform(),
        "ci": {key: os.environ[key] for key in CI_FIELDS if key in os.environ},
    }


def runtime_record(result) -> dict:
    record = {key: getattr(result, key, None) for key in RUNTIME_FIELDS}
    termination = getattr(result, "termination", None)
    record["termination"] = None
    if isinstance(termination, dict):
        record["termination"] = {key: termination.get(key) for key in TERMINATION_FIELDS}
        action = termination.get("request_action")
        record["termination"]["request_action"] = (
            {key: action[key] for key in ACTION_FIELDS if key in action}
            if isinstance(action, dict) else None
        )
    return record


class EventWriter:
    def __init__(self, stream):
        self.stream = stream
        self.errors: list[str] = []
        self.lock = threading.Lock()

    def emit(self, event: str, **fields) -> None:
        # A diagnostic failure must fail the run, but must not replace the
        # original test outcome or prevent the remaining tests from executing.
        with self.lock:
            try:
                self.stream.write(json.dumps({
                    "event": event, "at": datetime.now(timezone.utc).isoformat(), **fields,
                }, sort_keys=True, allow_nan=False) + "\n")
                self.stream.flush()
            except (OSError, TypeError, ValueError) as exc:
                self.errors.append(type(exc).__name__)


class DiagnosticResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity, *, events: EventWriter):
        super().__init__(stream, descriptions, verbosity)
        self.events = events
        self._restore = {}

    def startTest(self, test):
        super().startTest(test)
        self.events.emit("test-start", test=test.id())
        original = getattr(test, "run_source", None)
        if (callable(original) and getattr(original, "__module__", "").split(".")[-1]
                == "test_factory_runtime"):
            self._restore[id(test)] = ("run_source" in vars(test), vars(test).get("run_source"))

            @functools.wraps(original)
            def observed(*args, **kwargs):
                returned = original(*args, **kwargs)
                try:
                    record = runtime_record(returned[1])
                    self.events.emit("runtime-result", test=test.id(), runtime=record)
                except Exception as exc:
                    self.events.errors.append(type(exc).__name__)
                return returned

            test.run_source = observed

    def stopTest(self, test):
        saved = self._restore.pop(id(test), None)
        if saved is not None:
            had_attribute, original = saved
            if had_attribute:
                test.run_source = original
            else:
                del test.run_source
        self.events.emit("test-stop", test=test.id())
        super().stopTest(test)

    def _outcome(self, test, outcome, **extra):
        self.events.emit("test-outcome", test=test.id(), outcome=outcome, **extra)

    def addSuccess(self, test):
        super().addSuccess(test)
        self._outcome(test, "pass")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._outcome(test, "failure", traceback=self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self._outcome(test, "error", traceback=self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._outcome(test, "skip", reason=reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._outcome(test, "expected-failure")

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._outcome(test, "unexpected-success")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        self.events.emit("subtest-outcome", test=test.id(), subtest=subtest.id(),
                         outcome="pass" if err is None else "failure" if
                         issubclass(err[0], test.failureException) else "error",
                         traceback=self._exc_info_to_string(err, test) if err else None)


def run_suite(suite, events: EventWriter, *, stream=None) -> int:
    runner = unittest.TextTestRunner(
        stream=stream, verbosity=2,
        resultclass=functools.partial(DiagnosticResult, events=events),
    )
    result = runner.run(suite)
    successful = result.wasSuccessful() and result.testsRun > 0 and not events.errors
    events.emit("run-finish", tests_run=result.testsRun, failures=len(result.failures),
                errors=len(result.errors), skipped=len(result.skipped),
                expected_failures=len(result.expectedFailures),
                unexpected_successes=len(result.unexpectedSuccesses),
                successful=successful, diagnostic_errors=list(events.errors))
    return int(not successful or bool(events.errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-directory", default="tests")
    parser.add_argument("--pattern", default="test*.py")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    # Refuse evidence overwrite, including a rerun into the same output path.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        events = EventWriter(stream)
        try:
            events.emit("run-start", schema="residual.unittest-diagnostics.v1",
                        metadata=metadata(ROOT), start_directory=args.start_directory,
                        pattern=args.pattern, capture_scope="Factory Fixture.run_source only")
            suite = unittest.defaultTestLoader.discover(args.start_directory, pattern=args.pattern)
            return run_suite(suite, events)
        except BaseException as exc:
            events.emit("run-aborted", exception_type=type(exc).__name__)
            raise


if __name__ == "__main__":
    raise SystemExit(main())
