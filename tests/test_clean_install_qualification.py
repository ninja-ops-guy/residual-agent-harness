"""Regression tests for the clean-install qualification tooling itself."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = (Path(__file__).resolve().parents[1]
          / "verifier/v3/qualify_clean_install.py")
spec = importlib.util.spec_from_file_location("clean_install_qualification", SCRIPT)
assert spec is not None and spec.loader is not None
qualify_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qualify_tool)


class _Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _happy_runner(state):
    """Fake subprocess runner for a fully passing qualification."""
    def runner(cmd, *, cwd=None, env=None, timeout=600):
        cmd = [str(c) for c in cmd]
        if cmd[:2] == ["git", "--no-replace-objects"] or cmd[0] == "git":
            ref = cmd[-1]
            if ref == "HEAD":
                return _Result(stdout="a" * 40 + "\n")
            if ref == "HEAD^{tree}":
                return _Result(stdout="b" * 40 + "\n")
            return _Result(1, stderr="unknown ref")
        if cmd[1:3] == ["-m", "venv"]:
            python = Path(cmd[-1]) / "bin" / "python"
            python.parent.mkdir(parents=True, exist_ok=True)
            python.write_text("# fake\n")
            return _Result()
        if cmd[1:4] == ["-m", "pip", "wheel"]:
            wheel_dir = Path(cmd[cmd.index("--wheel-dir") + 1])
            wheel_dir.mkdir(parents=True, exist_ok=True)
            (wheel_dir / "residual_agent_harness-0.5.0-py3-none-any.whl").write_bytes(
                b"fake wheel bytes")
            return _Result()
        if cmd[1:4] == ["-m", "pip", "install"]:
            return _Result()
        if cmd[1:4] == ["-m", "pip", "check"]:
            return _Result()
        if cmd[1:4] == ["-m", "pip", "freeze"]:
            return _Result(stdout="residual-agent-harness==0.5.0\n")
        if cmd[1] == "-I":  # isolated smoke
            return _Result(stdout=json.dumps({"cli": {"residual": "PASS"}}))
        if "check_factory_ownership.py" in cmd[1]:
            return _Result(stdout=json.dumps({"passed": True, "checked": 32})
                           + "\nPASS: gate green\n")
        raise AssertionError(f"unexpected command: {cmd}")
    return runner


class HelpersTests(unittest.TestCase):
    def test_sha256_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "blob"
            path.write_bytes(b"qualification-evidence")
            self.assertEqual(
                qualify_tool.sha256_file(path),
                hashlib.sha256(b"qualification-evidence").hexdigest())

    def test_git_sha_rejects_invalid_output(self):
        def runner(cmd, **kwargs):
            return _Result(stdout="not-a-sha\n")
        original = qualify_tool._run
        qualify_tool._run = runner
        try:
            with self.assertRaisesRegex(qualify_tool.QualificationError, "invalid git SHA"):
                qualify_tool.git_sha(Path("."), "HEAD")
        finally:
            qualify_tool._run = original

    def test_git_sha_fails_closed_on_git_error(self):
        def runner(cmd, **kwargs):
            return _Result(128, stderr="not a git repository")
        original = qualify_tool._run
        qualify_tool._run = runner
        try:
            with self.assertRaises(qualify_tool.QualificationError):
                qualify_tool.git_sha(Path("."), "HEAD")
        finally:
            qualify_tool._run = original

    def test_smoke_surfaces_are_nonempty(self):
        self.assertTrue(qualify_tool.SMOKE_MODULES)
        self.assertTrue(qualify_tool.SMOKE_RESOURCES)
        self.assertTrue(qualify_tool.SMOKE_COMMANDS)
        self.assertIn("residual", qualify_tool.SMOKE_MODULES)


class QualifyFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "checkout"
        self.source.mkdir()
        (self.source / "verifier/v3").mkdir(parents=True)
        (self.source / "verifier/v3/check_factory_ownership.py").write_text("# x\n")
        self.work = self.root / "work"

    def test_happy_path_binds_commit_tree_wheel_and_results(self):
        report = qualify_tool.qualify(
            self.source, self.work, runner=_happy_runner({}))
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["commit"], "a" * 40)
        self.assertEqual(report["tree"], "b" * 40)
        self.assertEqual(
            report["wheel"]["sha256"],
            hashlib.sha256(b"fake wheel bytes").hexdigest())
        self.assertTrue(report["ownership"]["passed"])
        self.assertEqual(report["smoke"]["cli"]["residual"], "PASS")

    def test_work_dir_inside_checkout_is_rejected(self):
        with self.assertRaisesRegex(qualify_tool.QualificationError, "outside the checkout"):
            qualify_tool.qualify(
                self.source, self.source / "work", runner=_happy_runner({}))

    def test_any_step_failure_raises(self):
        def failing_runner(cmd, **kwargs):
            return _Result(1, stderr="boom")
        with self.assertRaises(qualify_tool.QualificationError):
            qualify_tool.qualify(self.source, self.work, runner=failing_runner)

    def test_multiple_wheels_fail_closed(self):
        def runner(cmd, *, cwd=None, env=None, timeout=600):
            cmd = [str(c) for c in cmd]
            if cmd[0] == "git":
                return _Result(stdout="a" * 40 + "\n")
            if cmd[1:4] == ["-m", "pip", "wheel"]:
                wheel_dir = Path(cmd[cmd.index("--wheel-dir") + 1])
                wheel_dir.mkdir(parents=True, exist_ok=True)
                (wheel_dir / "a-1.whl").write_bytes(b"a")
                (wheel_dir / "b-1.whl").write_bytes(b"b")
                return _Result()
            return _Result()
        with self.assertRaisesRegex(qualify_tool.QualificationError, "exactly one wheel"):
            qualify_tool.qualify(self.source, self.work, runner=runner)


class MainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "evidence/report.json"

    def test_failure_report_is_retained_and_exit_nonzero(self):
        with patch.object(qualify_tool, "qualify",
                          side_effect=qualify_tool.QualificationError("venv broken")):
            with redirect_stdout(io.StringIO()):
                code = qualify_tool.main([
                    "--source-root", str(self.root),
                    "--work-dir", str(self.root / "wd"),
                    "--output", str(self.output)])
        self.assertEqual(code, 1)
        report = json.loads(self.output.read_text())
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("venv broken", report["error"])

    def test_success_report_exit_zero(self):
        with patch.object(qualify_tool, "qualify", return_value={"status": "PASS"}):
            with redirect_stdout(io.StringIO()):
                code = qualify_tool.main([
                    "--source-root", str(self.root),
                    "--work-dir", str(self.root / "wd"),
                    "--output", str(self.output)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(self.output.read_text())["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
