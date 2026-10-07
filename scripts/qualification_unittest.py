#!/usr/bin/env python3
"""Ordinary unittest CLI with a narrow diagnostic for the lifecycle JSON failure.

Preserves unittest discovery, warnings, assertions and exit status. Only the
known missing-input fixture's failed JSON document is emitted; arbitrary test
locals, environment variables and other JSON payloads are never collected.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TARGET = ("test_factory_runtime_lifecycle.LifecycleGuards."
          "test_missing_cli_input_returns_sanitized_blocked_json_for_both_run_aliases")


class DiagnosticResult(unittest.TextTestResult):
    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if (err is not None and isinstance(err[1], json.JSONDecodeError)
                and test.id() in (TARGET, "tests." + TARGET)):
            document = err[1].doc
            self.stream.writeln("LIFECYCLE_JSON_DIAGNOSTIC " + json.dumps({
                "test": subtest.id(), "document": document[:16384],
                "length": len(document), "truncated": len(document) > 16384,
                "position": err[1].pos,
            }, sort_keys=True))


class DiagnosticRunner(unittest.TextTestRunner):
    resultclass = DiagnosticResult


if __name__ == "__main__":
    unittest.main(module=None, testRunner=DiagnosticRunner)
