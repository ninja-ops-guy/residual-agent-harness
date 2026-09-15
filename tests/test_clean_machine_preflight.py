"""Product onboarding boundary checks; all providers remain scripted."""
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("clean_machine_preflight", ROOT / "scripts/clean_machine_preflight.py")
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


class CleanMachinePreflightTests(unittest.TestCase):
    def test_default_environment_drops_credentials_and_python_injection(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "canary-private", "PYTHONPATH": "/malicious",
                                    "LD_PRELOAD": "/malicious.so", "HTTPS_PROXY": "secret-url"}):
            clean = preflight.clean_environment()
        for key in ("OPENAI_API_KEY", "PYTHONPATH", "LD_PRELOAD", "HTTPS_PROXY"):
            self.assertNotIn(key, clean)

    def test_provider_requires_both_opt_in_flags_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            for config, allowed in ((Path("config.toml"), False), (None, True)):
                target = Path(temporary) / "must-not-exist"
                with self.assertRaises(ValueError):
                    preflight.run_preflight(ROOT, target, provider_config=config, allow_model_call=allowed)
                self.assertFalse(target.exists())

    def test_nonfinite_and_out_of_range_timeouts_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "evidence"
            for timeout in (float("nan"), float("inf"), float("-inf"), 0, -1, 601):
                with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                    preflight.run_preflight(ROOT, output, timeout=timeout)
                self.assertFalse(output.exists())

    def test_archive_rejects_traversal_and_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            for name, kind in (("../escape", tarfile.REGTYPE), ("link", tarfile.SYMTYPE)):
                data = io.BytesIO()
                with tarfile.open(fileobj=data, mode="w") as archive:
                    item = tarfile.TarInfo(name)
                    item.type = kind
                    archive.addfile(item)
                with self.assertRaises(ValueError):
                    preflight.unpack_source(data.getvalue(), Path(temporary))

    def test_default_result_must_be_scripted_and_successful(self):
        with self.assertRaises(ValueError):
            preflight.verify_demo_result({"success": True, "calls": [{"usage": {"source": "provider"}}]})
        with self.assertRaises(ValueError):
            preflight.verify_demo_result({"success": False, "calls": [{"usage": {"source": "simulation"}}]})

    def test_failing_command_retains_hashes_and_phase(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recorder = preflight.Recorder(root, 10)
            with self.assertRaises(preflight.PhaseFailure):
                recorder.run("failure", [sys.executable, "-c", "import sys; print('diagnostic', file=sys.stderr); sys.exit(7)"],
                             cwd=root, env=preflight.clean_environment())
            phase = recorder.phases[0]
            self.assertEqual(phase["exit_code"], 7)
            self.assertEqual(phase["stderr_sha256"], preflight.sha256((root / "failure.stderr.log").read_bytes()))

    def test_provider_stdout_and_stderr_are_withheld(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recorder = preflight.Recorder(root, 10)
            recorder.run("private", [sys.executable, "-c", "print('secret-canary')"], cwd=root,
                         env=preflight.clean_environment(), private_output=True)
            self.assertNotIn("secret-canary", (root / "private.stdout.log").read_text())
            self.assertNotEqual(recorder.phases[0]["stdout_sha256"], recorder.phases[0]["stdout_log_sha256"])

    def test_bad_source_still_writes_failure_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = preflight.run_preflight(root, root / "failure")
            self.assertEqual(result["status"], "fail")
            self.assertEqual(result["failure"]["phase"], "git-sha")
            self.assertTrue((root / "failure/manifest.sha256").is_file())

    def test_fresh_venv_documented_flow_and_bound_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "evidence"
            with patch.dict(os.environ, {"OPENAI_API_KEY": "must-not-leak"}):
                report = preflight.run_preflight(ROOT, output)
            self.assertEqual(report["status"], "pass", report.get("failure"))
            self.assertTrue(report["diagnostics"]["fresh_venv"])
            self.assertFalse(report["blank_vm_tested"])
            self.assertFalse(report["installed_distribution_tested"])
            self.assertEqual(report["provider_smoke"]["model_calls"], 0)
            self.assertTrue(all(phase["status"] == "pass" for phase in report["phases"]))
            self.assertNotIn("must-not-leak", (output / "manifest.json").read_text())
            result = json.loads((output / "result.json").read_text())
            self.assertEqual(report["trace_root"], result["trace_root"])
            for filename, expected in report["scripted_artifacts"].items():
                self.assertEqual(preflight.sha256((output / filename).read_bytes()), expected)
            with self.assertRaises(FileExistsError):
                preflight.run_preflight(ROOT, output)


if __name__ == "__main__":
    unittest.main()
