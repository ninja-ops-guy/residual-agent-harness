import contextlib
import io
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from residual.cli import main
from residual.config import load_config
from residual.evaluation import benchmark


class CLITests(unittest.TestCase):
    def test_doctor_command_is_first_class_and_read_only_surface(self):
        report = {"residual_version": "0.5.0", "update_blockers": []}
        with patch("residual.cli.doctor_report", return_value=report), \
             patch("residual.cli.format_doctor", return_value="RESIDUAL Doctor") as formatter, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["doctor"]), 0)
        formatter.assert_called_once_with(report)
        self.assertIn("RESIDUAL Doctor", output.getvalue())

    def test_update_check_uses_check_path_not_mutating_update(self):
        result = {"target_revision": "a" * 40, "update_available": True}
        with patch("residual.cli.update_status", return_value=result) as check, \
             patch("residual.cli.perform_update") as mutate, \
             patch("residual.cli.format_update", return_value="RESIDUAL Update Check"), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["update", "--check"]), 0)
        check.assert_called_once_with(version=None)
        mutate.assert_not_called()

    def test_demo_and_trace_result_binding(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["demo", "--output", tmp]), 0)
            result = Path(tmp) / "result.json"
            trace = Path(tmp) / "trace.jsonl"
            self.assertEqual(main(["verify-trace", str(trace), "--result", str(result)]), 0)
            value = json.loads(result.read_text())
            value["values"]["cause"] = "forged"
            result.write_text(json.dumps(value))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["verify-trace", str(trace), "--result", str(result)]), 1)

    def test_incomplete_run_has_nonzero_exit_status(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["demo", "--mode", "local_only", "--output", tmp]), 2)

    def test_ablation_summary_has_real_denominators_and_no_fake_bill(self):
        report = benchmark(load_config(), cases=4, noise_lines=64)
        self.assertTrue(report["simulation"])
        rows = {r["mode"]: r for r in report["summary"]}
        self.assertEqual(rows["residual"]["successful"], 4)
        self.assertEqual(rows["cascade"]["successful"], 4)
        self.assertEqual(rows["local_only"]["successful"], 1)
        self.assertEqual(rows["no_pull"]["successful"], 1)
        self.assertFalse(rows["residual"]["usage_complete"])
        self.assertIsNone(rows["residual"]["remote_cost_usd"])
        self.assertLess(rows["residual"]["remote_request_bytes"], rows["cascade"]["remote_request_bytes"])

    def test_benchmark_invalid_counts_are_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["benchmark", "--cases", "0"]), 1)


if __name__ == "__main__":
    unittest.main()
