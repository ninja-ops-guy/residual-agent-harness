"""Fail-closed ownership regressions using real, temporary Git repositories."""
from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "verifier/v3/check_swarm.py"
spec = importlib.util.spec_from_file_location("swarm_ownership_gate", MODULE)
assert spec is not None and spec.loader is not None
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class OwnershipGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Ownership gate test")
        self.git("config", "user.email", "ownership-test@example.invalid")
        self.write("README.md", "baseline\n")
        self.write("residual/factory/runtime.py", "# owned\n")
        self.write("residual/swarm/worker.py", "# legacy owned\n")
        self.base = self.commit()

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args], check=True,
            capture_output=True, text=True,
        ).stdout.strip()

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD")

    def evaluate(self, **kwargs):
        return gate.evaluate_ownership(
            self.root, kwargs.get("baseline", self.base),
            kwargs.get("ownership_baseline", self.base),
        )

    def test_unchanged_baseline_is_zero_not_unknown(self):
        report, failures = self.evaluate()
        self.assertEqual(failures, [])
        self.assertEqual(report["changed_files"], 0)
        self.assertEqual(report["ownership_changed_files"], 0)
        self.assertEqual(report["head"], self.base)

    def test_unrelated_edit_allowed_and_counted(self):
        self.write("README.md", "allowed\n")
        self.commit()
        report, failures = self.evaluate()
        self.assertEqual(failures, [])
        self.assertEqual(report["changed_files"], 1)

    def test_canonical_edit_rejected(self):
        self.write("residual/factory/runtime.py", "# changed\n")
        self.commit()
        _, failures = self.evaluate()
        self.assertIn("residual/factory/runtime.py", " ".join(failures))

    def test_canonical_deletion_rejected(self):
        (self.root / "residual/factory/runtime.py").unlink()
        self.commit()
        _, failures = self.evaluate()
        self.assertIn("residual/factory/runtime.py", " ".join(failures))

    def test_protected_rename_outside_boundary_rejected(self):
        self.git("mv", "residual/factory/runtime.py", "moved.py")
        self.commit()
        _, failures = self.evaluate()
        self.assertIn("residual/factory/runtime.py", " ".join(failures))

    def test_each_reserved_canonical_file_is_protected(self):
        for path in sorted(gate.PROTECTED_FILES):
            with self.subTest(path=path):
                self.git("reset", "--hard", self.base)
                self.write(path, "# unauthorized addition or edit\n")
                self.commit()
                _, failures = self.evaluate()
                self.assertIn(path, " ".join(failures))

    def test_legacy_directory_remains_protected(self):
        self.write("residual/swarm/worker.py", "# changed\n")
        self.commit()
        _, failures = self.evaluate()
        self.assertIn("residual/swarm/worker.py", " ".join(failures))

    def test_whitespace_filenames_preserved(self):
        filename = "residual/swarm/name with\nnewline.py"
        self.write(filename, "# owned\n")
        self.commit()
        report, failures = self.evaluate()
        self.assertEqual(report["changed_files"], 1)
        self.assertIn(filename, " ".join(failures))

    def test_similar_prefix_is_not_owned(self):
        self.write("residual/swarm_extra/worker.py", "# allowed\n")
        self.write("residual/factory/runtime.py.backup", "# allowed\n")
        self.commit()
        self.assertEqual(self.evaluate()[1], [])

    def test_missing_reporting_baseline_fails_closed(self):
        report, failures = self.evaluate(baseline="0" * 40)
        self.assertIsNone(report["changed_files"])
        self.assertTrue(any("reporting evidence unavailable" in f for f in failures))

    def test_missing_ownership_baseline_fails_closed(self):
        report, failures = self.evaluate(ownership_baseline="0" * 40)
        self.assertIsNone(report["ownership_changed_files"])
        self.assertTrue(any("Factory ownership evidence unavailable" in f for f in failures))

    def test_blob_cannot_be_used_as_commit_baseline(self):
        blob = self.git("rev-parse", "HEAD:README.md")
        report, failures = self.evaluate(ownership_baseline=blob)
        self.assertIsNone(report["ownership_changed_files"])
        self.assertTrue(failures)

    def test_non_ancestor_baseline_rejected(self):
        self.git("checkout", "--orphan", "unrelated")
        self.write("README.md", "unrelated\n")
        unrelated = self.commit()
        self.git("checkout", "--detach", self.base)
        report, failures = self.evaluate(ownership_baseline=unrelated)
        self.assertIsNone(report["ownership_changed_files"])
        self.assertTrue(failures)

    def test_shallow_checkout_does_not_report_false_zero(self):
        self.write("README.md", "second\n")
        self.commit()
        shallow = Path(self.temp.name) / "shallow"
        subprocess.run(
            ["git", "clone", "-q", "--depth=1", self.root.as_uri(), str(shallow)],
            check=True, capture_output=True,
        )
        report, failures = gate.evaluate_ownership(shallow, self.base, self.base)
        self.assertIsNone(report["changed_files"])
        self.assertIsNone(report["ownership_changed_files"])
        self.assertEqual(len(failures), 2)

    def test_failed_diff_preserves_stderr(self):
        original = gate.subprocess.run

        def fail_diff(command, **kwargs):
            if "diff" in command:
                return subprocess.CompletedProcess(command, 128, "", "fixture diff error")
            return original(command, **kwargs)

        with patch.object(gate.subprocess, "run", side_effect=fail_diff):
            report, failures = self.evaluate()
        self.assertIsNone(report["changed_files"])
        self.assertIsNone(report["ownership_changed_files"])
        self.assertIn("fixture diff error", " ".join(failures))

    def test_git_missing_or_timeout_fails_closed(self):
        for error in (FileNotFoundError("git missing"), subprocess.TimeoutExpired("git", 30)):
            with self.subTest(error=error):
                with patch.object(gate.subprocess, "run", side_effect=error):
                    report, failures = self.evaluate()
                self.assertIsNone(report["changed_files"])
                self.assertTrue(failures)

    def test_failed_test_command_preserves_stderr(self):
        result = subprocess.CompletedProcess([], 1, "", "No module named pytest")
        with patch.object(gate.subprocess, "run", return_value=result):
            _, error = gate._run_check(self.root, "pytest", ["python", "-m", "pytest"])
        self.assertIn("No module named pytest", error)

    def test_preflight_does_not_claim_full_qualification(self):
        out = io.StringIO()
        with patch.object(gate, "evaluate_ownership", return_value=({}, [])):
            with patch.object(gate, "_run_check") as run_check, redirect_stdout(out):
                self.assertEqual(gate.main(["--ownership-only"]), 0)
        run_check.assert_not_called()
        self.assertIn("full qualification NOT RUN", out.getvalue())

    def test_ownership_failure_never_runs_or_claims_full_tests(self):
        with patch.object(gate, "evaluate_ownership", return_value=({}, ["missing baseline"])):
            with patch.object(gate, "_run_check") as run_check, redirect_stdout(io.StringIO()):
                self.assertEqual(gate.main([]), 1)
        run_check.assert_not_called()


if __name__ == "__main__":
    unittest.main()
