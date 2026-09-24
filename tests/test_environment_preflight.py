import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "environment_preflight.py"
SPEC = importlib.util.spec_from_file_location("environment_preflight", MODULE_PATH)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class EnvironmentPreflightTests(unittest.TestCase):
    def test_overall_pass_requires_every_required_check(self):
        checks = [
            {"name": "a", "required": True, "status": "PASS"},
            {"name": "b", "required": True, "status": "PASS"},
        ]
        self.assertEqual(mod.overall_status(checks), "PASS")

        checks[1]["status"] = "BLOCKED"
        self.assertEqual(mod.overall_status(checks), "BLOCKED")
        self.assertEqual(mod.overall_status([]), "BLOCKED")

    def test_optional_failure_does_not_block_required_passes(self):
        checks = [
            {"name": "required", "required": True, "status": "PASS"},
            {"name": "optional", "required": False, "status": "BLOCKED"},
        ]
        self.assertEqual(mod.overall_status(checks), "PASS")

    def test_safe_environment_is_allowlisted(self):
        env = {
            "CI": "true",
            "GITHUB_ACTIONS": "true",
            "RUNNER_OS": "Linux",
            "RUNNER_ARCH": "X64",
            "SUPER_SECRET_TOKEN": "must-not-leak",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(
                mod.safe_environment(),
                {
                    "CI": "true",
                    "GITHUB_ACTIONS": "true",
                    "RUNNER_OS": "Linux",
                    "RUNNER_ARCH": "X64",
                },
            )

    def test_report_is_machine_readable_and_fail_closed(self):
        checks = [
            {"name": "identity", "required": True, "status": "PASS", "detail": "ok"},
            {"name": "namespace", "required": True, "status": "BLOCKED", "detail": "denied"},
        ]
        report = mod.build_report(checks)
        self.assertEqual(report["schema_version"], mod.SCHEMA)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["checks"], checks)
        self.assertIn("python", report["runtime"])
        self.assertIn("sqlite", report["runtime"])
        self.assertIn("openssl", report["runtime"])

    def test_required_distribution_contract_matches_factory_qualification_needs(self):
        self.assertEqual(
            mod.REQUIRED_DISTRIBUTIONS,
            ("cryptography", "PyYAML", "hypothesis", "coverage", "pytest"),
        )

    def test_signal_probe_cleans_up_child_when_signal_delivery_raises(self):
        class FakeProcess:
            def __init__(self):
                self.killed = False
                self.wait_calls = 0

            def send_signal(self, _sig):
                raise OSError("synthetic signal failure")

            def poll(self):
                return None if not self.killed else -9

            def kill(self):
                self.killed = True

            def wait(self, timeout=None):
                self.wait_calls += 1
                return -9

        fake = FakeProcess()
        completed = SimpleNamespace(stdout="ENV_G01_SUBPROCESS_OK\n", returncode=0)
        with mock.patch.object(mod.subprocess, "run", return_value=completed), mock.patch.object(
            mod.subprocess, "Popen", return_value=fake
        ):
            result = mod._subprocess_and_signal()

        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(fake.killed)
        self.assertEqual(fake.wait_calls, 1)

    def test_signal_probe_contains_cleanup_kill_failure(self):
        class FakeProcess:
            def __init__(self):
                self.kill_calls = 0
                self.wait_calls = 0

            def send_signal(self, _sig):
                raise OSError("synthetic signal failure")

            def poll(self):
                return None

            def kill(self):
                self.kill_calls += 1
                raise OSError("synthetic kill failure")

            def wait(self, timeout=None):
                self.wait_calls += 1
                return -9

        fake = FakeProcess()
        completed = SimpleNamespace(stdout="ENV_G01_SUBPROCESS_OK\n", returncode=0)
        with mock.patch.object(mod.subprocess, "run", return_value=completed), mock.patch.object(
            mod.subprocess, "Popen", return_value=fake
        ):
            result = mod._subprocess_and_signal()

        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("synthetic signal failure", result["detail"])
        self.assertEqual(fake.kill_calls, 1)
        self.assertEqual(fake.wait_calls, 1)


if __name__ == "__main__":
    unittest.main()
