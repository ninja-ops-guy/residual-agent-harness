"""Exercise the actual CLI walkthrough and preserve prior user evidence."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/first_run.py"


class FirstRunTests(unittest.TestCase):
    def test_real_walkthrough_from_outside_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "output with spaces"
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--output", str(out)],
                cwd=directory, capture_output=True, text=True, timeout=90,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            report = json.loads((out / "first-run.json").read_text())
            self.assertEqual(report["status"], "PASS")
            self.assertFalse(report["release_authority"])
            self.assertEqual(report["model_calls"], 0)
            checks = {entry["name"]: entry for entry in report["checks"]}
            self.assertEqual(checks["reject-altered"]["exit_code"], 1)
            original = json.loads((out / "accepted/result.json").read_text())
            altered = json.loads((out / "altered-result.json").read_text())
            self.assertEqual(original["values"]["total_fan_rpm"], 7230)
            self.assertEqual(altered["values"]["total_fan_rpm"], 0)
            self.assertEqual(checks["verify-original-again"]["exit_code"], 0)

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            sentinel = Path(directory) / "first-run.json"
            sentinel.write_text("prior evidence\n")
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--output", directory],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(proc.returncode, 1)
            self.assertIn("already exists", proc.stderr)
            self.assertEqual(sentinel.read_text(), "prior evidence\n")
            self.assertEqual(list(Path(directory).iterdir()), [sentinel])


if __name__ == "__main__":
    unittest.main()
