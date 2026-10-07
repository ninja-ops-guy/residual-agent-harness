import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from residual.cli import main
from residual.config import load_config
from residual.evaluation import benchmark


class CLITests(unittest.TestCase):
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
