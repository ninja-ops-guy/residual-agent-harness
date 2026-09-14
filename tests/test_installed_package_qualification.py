"""Regression tests for wheel-origin validation and negative reporting."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/qualify_installed_package.py"
spec = importlib.util.spec_from_file_location("installed_package_qualification", SCRIPT)
assert spec is not None and spec.loader is not None
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class InstalledPackageQualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "checkout"
        self.site = self.root / "venv/lib/site-packages"
        self.origin = self.site / "residual/__init__.py"
        self.origin.parent.mkdir(parents=True)
        self.origin.write_text("# installed\n")
        self.source.mkdir()
        self.files = {self.origin.resolve()}

    def validate(self, origin=None):
        return smoke.validate_origin(origin or self.origin, self.files, self.site, self.source)

    def test_distribution_owned_venv_origin_passes(self):
        self.assertEqual(self.validate(), self.origin.resolve())

    def test_checkout_shadow_is_rejected(self):
        origin = self.source / "residual.py"
        origin.write_text("# source\n")
        with self.assertRaisesRegex(RuntimeError, "checkout shadowing"):
            self.validate(origin)

    def test_global_package_is_rejected(self):
        origin = self.root / "global.py"
        origin.write_text("# global\n")
        self.files.add(origin.resolve())
        with self.assertRaisesRegex(RuntimeError, "outside this venv"):
            self.validate(origin)

    def test_unrecorded_venv_file_is_rejected(self):
        self.files.clear()
        with self.assertRaisesRegex(RuntimeError, "distribution file"):
            self.validate()

    def test_missing_recorded_file_is_rejected(self):
        self.origin.unlink()
        with self.assertRaisesRegex(RuntimeError, "distribution file"):
            self.validate()

    def test_symlink_back_into_checkout_is_rejected(self):
        target = self.source / "source.py"
        target.write_text("# source\n")
        self.origin.unlink()
        try:
            self.origin.symlink_to(target)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        with self.assertRaisesRegex(RuntimeError, "checkout shadowing"):
            self.validate()

    def test_environment_removes_import_path_overrides_without_mutating_input(self):
        original = {"PYTHONPATH": "/checkout", "PYTHONHOME": "/global", "PATH": "/bin"}
        cleaned = smoke.clean_environment(original)
        self.assertNotIn("PYTHONPATH", cleaned)
        self.assertNotIn("PYTHONHOME", cleaned)
        self.assertEqual(cleaned["PYTHONNOUSERSITE"], "1")
        self.assertEqual(cleaned["PATH"], "/bin")
        self.assertIn("PYTHONPATH", original)

    def test_failure_is_retained_and_returns_nonzero(self):
        output = self.root / "evidence/smoke.json"
        with patch.object(smoke, "qualify", side_effect=RuntimeError("missing packaged resource")):
            with redirect_stdout(io.StringIO()):
                code = smoke.main(["--source-root", str(self.source), "--output", str(output)])
        self.assertEqual(code, 1)
        report = json.loads(output.read_text())
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("missing packaged resource", report["error"])

    def test_success_is_retained(self):
        output = self.root / "evidence/smoke.json"
        with patch.object(smoke, "qualify", return_value={"status": "PASS"}):
            with redirect_stdout(io.StringIO()):
                code = smoke.main(["--source-root", str(self.source), "--output", str(output)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.read_text())["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
