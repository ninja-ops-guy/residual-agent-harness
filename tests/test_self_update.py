import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from residual import self_update
from residual.cli import main as cli_main


class SelfUpdateTests(unittest.TestCase):
    def test_cli_dispatches_update_before_normal_config_path(self):
        with mock.patch("residual.self_update.main", return_value=7) as update:
            self.assertEqual(cli_main(["update", "--dry-run"]), 7)
        update.assert_called_once_with(["--dry-run"])

    def test_detect_source_checkout_requires_git_and_pyproject(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module = root / "residual" / "self_update.py"
            module.parent.mkdir()
            module.write_text("# fixture\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
            self.assertIsNone(self_update.detect_source_checkout(module))
            (root / ".git").mkdir()
            self.assertEqual(self_update.detect_source_checkout(module), root.resolve())

    def test_source_update_is_clean_fast_forward_only(self):
        root = Path("/tmp/residual-source-fixture")
        with (
            mock.patch("residual.self_update.shutil.which", return_value="/usr/bin/git"),
            mock.patch(
                "residual.self_update._git_output",
                side_effect=["main", "", "origin/main", "a" * 40, "b" * 40],
            ) as output,
            mock.patch("residual.self_update._git_exec") as execute,
        ):
            result = self_update.update_source(root)

        self.assertEqual(result["status"], "updated")
        self.assertEqual(result["from_revision"], "a" * 40)
        self.assertEqual(result["to_revision"], "b" * 40)
        execute.assert_has_calls(
            [
                mock.call(root, ["fetch", "--quiet", "--prune"], "could not fetch the configured upstream"),
                mock.call(
                    root,
                    ["merge", "--ff-only", "@{upstream}"],
                    "source branch cannot fast-forward to its upstream; resolve the branch manually",
                ),
            ]
        )
        self.assertEqual(output.call_count, 5)

    def test_source_update_refuses_dirty_checkout_before_network(self):
        root = Path("/tmp/residual-source-fixture")
        with (
            mock.patch("residual.self_update.shutil.which", return_value="/usr/bin/git"),
            mock.patch(
                "residual.self_update._git_output",
                side_effect=["main", " M residual/cli.py"],
            ),
            mock.patch("residual.self_update._git_exec") as execute,
        ):
            with self.assertRaisesRegex(self_update.UpdateError, "uncommitted changes"):
                self_update.update_source(root)
        execute.assert_not_called()

    def test_source_dry_run_does_not_fetch_or_merge(self):
        root = Path("/tmp/residual-source-fixture")
        with (
            mock.patch("residual.self_update.shutil.which", return_value="/usr/bin/git"),
            mock.patch(
                "residual.self_update._git_output",
                side_effect=["main", "", "origin/main", "a" * 40],
            ),
            mock.patch("residual.self_update._git_exec") as execute,
        ):
            result = self_update.update_source(root, dry_run=True)
        self.assertEqual(result["status"], "ready")
        execute.assert_not_called()

    def test_package_update_uses_current_interpreter_and_upgrade(self):
        completed = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with (
            mock.patch("residual.self_update._package_version", side_effect=["0.5.0", "0.5.1"]),
            mock.patch("residual.self_update._run_process", return_value=completed) as run,
        ):
            result = self_update.update_package(pre=True)

        cmd = run.call_args.args[0]
        self.assertEqual(cmd[:3], [sys.executable, "-m", "pip"])
        self.assertIn("--upgrade", cmd)
        self.assertIn("--no-input", cmd)
        self.assertIn("--pre", cmd)
        self.assertEqual(cmd[-1], self_update.DISTRIBUTION)
        self.assertEqual(result["status"], "updated")
        self.assertEqual(result["to_version"], "0.5.1")

    def test_package_failure_does_not_echo_pip_stderr(self):
        completed = subprocess.CompletedProcess(
            [],
            1,
            stdout="",
            stderr="https://user:super-secret@example.invalid/simple",
        )
        with (
            mock.patch("residual.self_update._package_version", return_value="0.5.0"),
            mock.patch("residual.self_update._run_process", return_value=completed),
        ):
            with self.assertRaisesRegex(self_update.UpdateError, "pip could not upgrade") as ctx:
                self_update.update_package()
        self.assertNotIn("super-secret", str(ctx.exception))

    def test_package_dry_run_does_not_invoke_pip(self):
        with (
            mock.patch("residual.self_update._package_version", return_value="0.5.0"),
            mock.patch("residual.self_update._run_process") as run,
        ):
            result = self_update.update_package(dry_run=True)
        self.assertEqual(result["status"], "ready")
        run.assert_not_called()

    def test_main_reports_update_error_without_traceback(self):
        with (
            mock.patch("residual.self_update.detect_source_checkout", return_value=Path("/repo")),
            mock.patch(
                "residual.self_update.update_source",
                side_effect=self_update.UpdateError("source checkout has uncommitted changes"),
            ),
            contextlib.redirect_stderr(io.StringIO()) as err,
        ):
            self.assertEqual(self_update.main(["--method", "source"]), 1)
        self.assertIn("uncommitted changes", err.getvalue())


if __name__ == "__main__":
    unittest.main()
