"""Unit tests for output publication; these do not emulate a VM."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from demo.vm.guest_result_check import check
from residual.cli import main


class PublishedSummaryTests(unittest.TestCase):
    def invoke(self, cleanup):
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            result = {"task_id": "unit", "status": "passed", "success": True,
                      "values": {"value": 3}, "unresolved": {}, "calls": [],
                      "metrics": {"elapsed_ms": 123.25}, "trace_root": "unit-root"}
            harness = SimpleNamespace(
                run=lambda task: result,
                cache=SimpleNamespace(close=lambda: cleanup(result, destination)),
                ledger=SimpleNamespace(write=lambda path: Path(path).write_text("unit-test-only\n")))
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch("residual.cli.build_harness", return_value=harness), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(["demo", "--output", directory])
            return code, stdout.getvalue(), stderr.getvalue(), destination.joinpath("result.json").read_text()

    def test_summary_equals_persisted_result(self):
        code, stdout, _, saved = self.invoke(lambda result, path: None)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["metrics"], json.loads(saved)["metrics"])

    def test_cleanup_cannot_change_published_result_via_memory_alias(self):
        def cleanup(result, destination):
            result["metrics"]["elapsed_ms"] = float("-inf")
        code, stdout, _, saved = self.invoke(cleanup)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["metrics"]["elapsed_ms"], 123.25)
        self.assertNotIn("Infinity", stdout)
        check(saved, stdout)

    def test_changed_persisted_result_fails_closed(self):
        def cleanup(result, destination):
            result["values"]["value"] = 999
            destination.joinpath("result.json").write_text(json.dumps(result))
        code, stdout, stderr, _ = self.invoke(cleanup)
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("could not be validated", stderr)

    def test_nonfinite_persisted_result_fails_closed(self):
        def cleanup(result, destination):
            result["metrics"]["elapsed_ms"] = float("-inf")
            destination.joinpath("result.json").write_text(json.dumps(result))
        code, stdout, _, _ = self.invoke(cleanup)
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")


class GuestMetricAcceptanceTests(unittest.TestCase):
    def texts(self, elapsed=123.25):
        result = {"success": True, "status": "passed", "values": {}, "metrics": {"elapsed_ms": elapsed}}
        return json.dumps(result), json.dumps(result)

    def test_finite_agreement_passes(self):
        self.assertTrue(check(*self.texts())["timings_finite"])

    def test_nonfinite_constants_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                check(*self.texts(value))

    def test_json_numeric_overflow_rejected(self):
        with self.assertRaises(AssertionError):
            check(*[text.replace("123.25", "1e9999") for text in self.texts()])

    def test_negative_elapsed_rejected(self):
        with self.assertRaises(AssertionError):
            check(*self.texts(-1))

    def test_saved_and_displayed_metrics_must_agree(self):
        saved, cli = self.texts()
        with self.assertRaisesRegex(AssertionError, "differ"):
            check(saved, cli.replace("123.25", "124.25"))


if __name__ == "__main__":
    unittest.main()
