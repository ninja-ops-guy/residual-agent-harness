"""Local Git fixtures: no credentials, network, model calls, or source execution."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("open_core_export", Path(__file__).resolve().parents[1] / "tools/export_open_core.py")
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)


class OpenCoreExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        for path in EXPORT.ALWAYS:
            self.write(path, "test fixture only\n")
        self.write("open/module.py", "VALUE = 'committed'\n")
        self.write("reserved/enterprise.py", "PRIVATE = True\n")
        self.manifest = {"schema_version": 1, "license": "Apache-2.0",
                         "license_file": EXPORT.ALWAYS[0], "notice_file": "NOTICE",
                         "include": ["open"], "exclude": ["reserved"]}
        self.commit_manifest()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Test Fixture",
                               "-c", "user.email=fixture@example.invalid", *args],
                              check=True, capture_output=True).stdout

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "fixture")

    def commit_manifest(self):
        self.write(EXPORT.MANIFEST_PATH, json.dumps(self.manifest))
        self.commit()

    def test_basic_selection_excludes_reserved(self):
        _, selected = EXPORT.snapshot(self.root)
        self.assertIn("open/module.py", selected)
        self.assertNotIn("reserved/enterprise.py", selected)

    def test_untracked_and_ignored_files_never_export(self):
        self.write("open/.env", "NOT-A-REAL-SECRET")
        self.write("open/__pycache__/cache.pyc", "cache")
        self.write(".gitignore", "open/.env\nopen/__pycache__/\n")
        _, selected = EXPORT.snapshot(self.root)
        self.assertNotIn("open/.env", selected)
        self.assertNotIn("open/__pycache__/cache.pyc", selected)

    def test_dirty_and_staged_files_are_not_exported(self):
        self.write("open/module.py", "VALUE = 'local'\n")
        self.git("add", "open/module.py")
        self.write(EXPORT.MANIFEST_PATH, "not json")
        EXPORT.export(self.root, Path("dist/source.tar.gz"))
        with tarfile.open(self.root / "dist/source.tar.gz") as archive:
            self.assertEqual(archive.extractfile("residual-open-core/open/module.py").read(), b"VALUE = 'committed'\n")

    def test_committed_symlink_rejected(self):
        (self.root / "open/link").symlink_to("../reserved/enterprise.py")
        self.commit()
        with self.assertRaises(EXPORT.ExportError):
            EXPORT.snapshot(self.root)

    def test_committed_submodule_rejected(self):
        head = self.git("rev-parse", "HEAD").decode().strip()
        self.git("update-index", "--add", "--cacheinfo", f"160000,{head},open/submodule")
        self.git("commit", "-qm", "submodule fixture")
        with self.assertRaises(EXPORT.ExportError):
            EXPORT.snapshot(self.root)

    def test_malformed_paths_rejected(self):
        for value in ("../reserved", "/tmp", "open/../reserved", "open//x", "open/", "open\\x", "C:/x", ".", "open/*", " open", 3):
            with self.subTest(value=value), self.assertRaises(EXPORT.ExportError):
                EXPORT.safe_path(value)

    def test_overlapping_roots_rejected(self):
        self.manifest["include"] = ["reserved/enterprise.py"]
        self.commit_manifest()
        with self.assertRaises(EXPORT.ExportError):
            EXPORT.snapshot(self.root)

    def test_duplicate_roots_rejected(self):
        self.manifest["include"] = ["open", "open"]
        self.commit_manifest()
        with self.assertRaises(EXPORT.ExportError):
            EXPORT.snapshot(self.root)

    def test_malformed_manifest_rejected(self):
        self.write(EXPORT.MANIFEST_PATH, "not-json")
        self.commit()
        with self.assertRaises(json.JSONDecodeError):
            EXPORT.snapshot(self.root)

    def test_duplicate_json_key_rejected(self):
        self.write(EXPORT.MANIFEST_PATH, '{"include": [], "include": ["reserved"]}')
        self.commit()
        with self.assertRaises(EXPORT.ExportError):
            EXPORT.snapshot(self.root)

    def test_missing_included_path_rejected(self):
        self.manifest["include"] = ["missing"]
        self.commit_manifest()
        with self.assertRaises(EXPORT.ExportError):
            EXPORT.snapshot(self.root)

    def test_deterministic_archives(self):
        first = EXPORT.export(self.root, Path("dist/one.tar.gz"))
        second = EXPORT.export(self.root, Path("dist/two.tar.gz"))
        self.assertEqual(first, second)
        self.assertEqual((self.root / "dist/one.tar.gz").read_bytes(), (self.root / "dist/two.tar.gz").read_bytes())

    def test_existing_output_not_overwritten(self):
        self.write("dist/out.tar.gz", "keep")
        with self.assertRaises(EXPORT.ExportError):
            EXPORT.export(self.root, Path("dist/out.tar.gz"))
        self.assertEqual((self.root / "dist/out.tar.gz").read_text(), "keep")

    def test_output_cannot_escape_repository(self):
        with self.assertRaises(EXPORT.ExportError):
            EXPORT.export(self.root, self.root.parent / "escape.tar.gz")

    def test_symlink_output_not_overwritten(self):
        (self.root / "out").symlink_to(self.root / "missing")
        with self.assertRaises(EXPORT.ExportError):
            EXPORT.export(self.root, Path("out"))

    def test_auxiliary_metadata_cannot_bypass_reservation(self):
        self.manifest["exclude"].append("SECURITY.md")
        self.commit_manifest()
        with self.assertRaises(EXPORT.ExportError):
            EXPORT.snapshot(self.root)


if __name__ == "__main__":
    unittest.main()
