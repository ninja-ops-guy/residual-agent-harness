import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.qualification_test_runner import (
    EventWriter, ROOT, main, metadata, run_suite, runtime_record,
)


class DiagnosticsTests(unittest.TestCase):
    def execute(self, case):
        output = io.StringIO()
        events = EventWriter(output)
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(case)
        code = run_suite(suite, events, stream=io.StringIO())
        return code, [json.loads(line) for line in output.getvalue().splitlines()]

    def test_standard_outcomes_preserved_without_retries(self):
        calls = []

        class Cases(unittest.TestCase):
            def test_pass(self):
                calls.append("pass")

            def test_failure(self):
                calls.append("failure")
                self.assertEqual(-9, -31)

            def test_error(self):
                calls.append("error")
                raise ValueError("fixture error")

            @unittest.skip("namespace unavailable")
            def test_skip(self):
                raise AssertionError("must not run")

            @unittest.expectedFailure
            def test_expected(self):
                self.fail("expected")

            @unittest.expectedFailure
            def test_unexpected(self):
                pass

        code, records = self.execute(Cases)
        self.assertEqual(code, 1)
        self.assertEqual(sorted(calls), ["error", "failure", "pass"])
        outcomes = {record["outcome"] for record in records if record["event"] == "test-outcome"}
        self.assertEqual(outcomes, {"pass", "failure", "error", "skip", "expected-failure", "unexpected-success"})
        self.assertEqual(records[-1]["tests_run"], 6)
        self.assertEqual(records[-1]["skipped"], 1)
        failure = next(record for record in records if record.get("outcome") == "failure")
        self.assertIn("-9 != -31", failure["traceback"])

    def test_subtest_failures_and_errors_are_not_pass(self):
        class Cases(unittest.TestCase):
            def test_subtests(self):
                for value in range(3):
                    with self.subTest(value=value):
                        if value == 1:
                            self.fail("subtest failed")
                        if value == 2:
                            raise ValueError("subtest error")

        code, records = self.execute(Cases)
        self.assertEqual(code, 1)
        self.assertEqual([r["outcome"] for r in records if r["event"] == "subtest-outcome"],
                         ["pass", "failure", "error"])

    def test_fixture_result_saved_before_cleanup_and_method_restored(self):
        result = SimpleNamespace(returncode=-9, status="killed", process_reaped=True,
                                 termination={"classification": "unknown", "observed_signal": 9})
        returned = (object(), result)
        instances = []

        class Cases(unittest.TestCase):
            def run_source(self, source):
                return returned

            def test_capture(self):
                instances.append(self)
                self.assertIs(self.run_source("source-not-recorded"), returned)
                self.assertIs(self.run_source("second-call"), returned)
                self.addCleanup(lambda: setattr(result, "termination", None))
                self.assertEqual(result.returncode, -31)

        Cases.run_source.__module__ = "tests.test_factory_runtime"
        code, records = self.execute(Cases)
        self.assertEqual(code, 1)
        captured = [r for r in records if r["event"] == "runtime-result"]
        self.assertEqual(len(captured), 2)
        self.assertEqual(captured[0]["runtime"]["termination"]["observed_signal"], 9)
        self.assertIsNone(result.termination)
        self.assertNotIn("run_source", vars(instances[0]))
        self.assertNotIn("source-not-recorded", json.dumps(records))

    def test_uncaptured_result_is_not_invented(self):
        class Cases(unittest.TestCase):
            def test_no_fixture(self):
                pass

        code, records = self.execute(Cases)
        self.assertEqual(code, 0)
        self.assertFalse(any(r["event"] == "runtime-result" for r in records))
        self.assertTrue(records[-1]["successful"])

    def test_fixture_exception_remains_original_error_with_no_invented_result(self):
        class Cases(unittest.TestCase):
            def run_source(self, source):
                raise ValueError("original runtime failure")

            def test_capture(self):
                self.run_source("source")

        Cases.run_source.__module__ = "test_factory_runtime"
        code, records = self.execute(Cases)
        self.assertEqual(code, 1)
        errors = [r for r in records if r.get("outcome") == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIn("ValueError: original runtime failure", errors[0]["traceback"])
        self.assertFalse(any(r["event"] == "runtime-result" for r in records))

    def test_threaded_fixture_results_stay_bound_to_their_test(self):
        class Cases(unittest.TestCase):
            def run_source(self, source):
                return None, SimpleNamespace(attempt_id=source, returncode=0)

            def test_capture(self):
                with ThreadPoolExecutor(max_workers=4) as pool:
                    list(pool.map(self.run_source, map(str, range(12))))

        Cases.run_source.__module__ = "test_factory_runtime"
        code, records = self.execute(Cases)
        self.assertEqual(code, 0)
        captured = [r for r in records if r["event"] == "runtime-result"]
        self.assertEqual({r["runtime"]["attempt_id"] for r in captured}, set(map(str, range(12))))
        self.assertEqual(len({r["test"] for r in captured}), 1)

    def test_class_setup_error_is_retained(self):
        class Cases(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                raise ValueError("setup failure")

            def test_unreached(self):
                self.fail("must not execute")

        code, records = self.execute(Cases)
        self.assertEqual(code, 1)
        self.assertTrue(any("setup failure" in r.get("traceback", "") for r in records))

    def test_runtime_payload_is_allowlisted_without_candidate_or_contract(self):
        result = SimpleNamespace(
            returncode=-9, candidate="candidate-secret", contract="contract-secret",
            reason="arbitrary-secret", termination={
                "classification": "unknown", "unknown": "secret",
                "request_action": {"reason": "rss_meter_unavailable", "source": "secret"},
            })
        record = runtime_record(result)
        self.assertNotIn("secret", json.dumps(record))
        self.assertEqual(record["termination"]["request_action"], {"reason": "rss_meter_unavailable"})

    def test_diagnostic_write_failure_fails_run_without_suppressing_tests(self):
        class BrokenStream(io.StringIO):
            def write(self, text):
                raise OSError("disk full")

        calls = []
        events = EventWriter(BrokenStream())
        suite = unittest.TestSuite([unittest.FunctionTestCase(lambda: calls.append(1))])
        self.assertEqual(run_suite(suite, events, stream=io.StringIO()), 1)
        self.assertEqual(calls, [1])
        self.assertTrue(events.errors)

    def test_empty_discovery_cannot_pass(self):
        self.assertEqual(run_suite(unittest.TestSuite(), EventWriter(io.StringIO()), stream=io.StringIO()), 1)

    def test_serialization_failure_is_a_diagnostic_failure(self):
        events = EventWriter(io.StringIO())
        events.emit("invalid", non_json=object())
        suite = unittest.TestSuite([unittest.FunctionTestCase(lambda: None)])
        self.assertEqual(run_suite(suite, events, stream=io.StringIO()), 1)
        self.assertEqual(events.errors, ["TypeError"])

    def test_incremental_records_exist_before_finish(self):
        output = io.StringIO()
        events = EventWriter(output)

        def inspect():
            records = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual(records[-1]["event"], "test-start")
            self.assertFalse(any(r["event"] == "run-finish" for r in records))

        self.assertEqual(run_suite(unittest.TestSuite([unittest.FunctionTestCase(inspect)]),
                                   events, stream=io.StringIO()), 0)

    def test_metadata_binds_git_and_only_allowlisted_ci_values(self):
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "2",
                                    "PRIVATE_SECRET": "do-not-copy"}):
            result = metadata(ROOT)
        self.assertEqual(len(result["commit"]), 40)
        self.assertEqual(len(result["tree"]), 40)
        self.assertEqual(result["ci"]["GITHUB_RUN_ATTEMPT"], "2")
        self.assertIs(type(result["dirty"]), bool)
        self.assertNotIn("do-not-copy", json.dumps(result))

    def test_git_failure_is_not_fabricated_metadata(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(subprocess.CalledProcessError):
            metadata(Path(directory))

    def test_existing_evidence_refused_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text("retained evidence\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                main(["--output", str(path)])
            self.assertEqual(path.read_text(), "retained evidence\n")

    def test_cli_reports_empty_selection_and_aborted_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            for start, pattern, final in (("tests", "no_matching_tests_qualification.py", "run-finish"),
                                          ("missing-qualification-tests", "test*.py", "run-aborted")):
                with self.subTest(start=start):
                    path = Path(directory) / (final + ".jsonl")
                    proc = subprocess.run(
                        [sys.executable, "scripts/qualification_test_runner.py", "--start-directory", start,
                         "--pattern", pattern, "--output", str(path)],
                        cwd=ROOT, capture_output=True, text=True, timeout=30,
                    )
                    self.assertNotEqual(proc.returncode, 0)
                    records = [json.loads(line) for line in path.read_text().splitlines()]
                    self.assertEqual(records[0]["event"], "run-start")
                    self.assertEqual(records[-1]["event"], final)

    def test_workflows_use_diagnostics_and_binding_is_active(self):
        import yaml
        for name in ("ci", "station"):
            workflow = yaml.safe_load((ROOT / ".github/workflows" / f"{name}.yml").read_text())
            job = workflow["jobs"]["tests" if name == "ci" else "python"]
            self.assertIs(job["strategy"]["fail-fast"], False)
            self.assertEqual(sum("qualification_test_runner.py" in step.get("run", "") for step in job["steps"]), 1)
            uploads = [s for s in job["steps"] if s.get("name") == "Preserve ordinary-suite diagnostics"]
            self.assertEqual(len(uploads), 1)
            self.assertEqual(uploads[0]["if"], "always()")
            self.assertIn("github.run_attempt", uploads[0]["with"]["name"])
        self.assertTrue((ROOT / ".github/workflows/measured-eval-binding.yml").is_file())
        self.assertFalse((ROOT / "ci/measured-eval-binding.yml").exists())
