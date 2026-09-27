import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_release_lock.py"
SPEC = importlib.util.spec_from_file_location("validate_release_lock", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

H1 = "1" * 64
H2 = "2" * 64


class ReleaseLockContractTests(unittest.TestCase):
    def lock(self, text: str) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "requirements-release.lock"
        path.write_text(text, encoding="utf-8")
        return path

    def test_accepts_exact_pins_with_sha256_hashes(self):
        path = self.lock(
            f"defusedxml==0.7.1 --hash=sha256:{H1}\n"
            f"setuptools==80.9.0 --hash=sha256:{H2}\n"
        )
        result = module.validate_lock(path)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["entries"], 2)

    def test_accepts_multiple_hashes_for_one_exact_distribution(self):
        path = self.lock(
            f"example==1.2.3 --hash=sha256:{H1} --hash=sha256:{H2}\n"
        )
        self.assertEqual(module.validate_lock(path)["unique_sha256_hashes"], 2)

    def test_rejects_range_or_unhashed_dependency(self):
        for content in ("defusedxml>=0.7.1\n", "defusedxml==0.7.1\n"):
            with self.subTest(content=content):
                with self.assertRaises(module.LockContractError):
                    module.validate_lock(self.lock(content))

    def test_rejects_mutable_or_direct_sources(self):
        cases = [
            "git+https://example.invalid/repo.git\n",
            "https://example.invalid/pkg.whl\n",
            "-e ../local\n",
        ]
        for content in cases:
            with self.subTest(content=content):
                with self.assertRaises(module.LockContractError):
                    module.validate_lock(self.lock(content))

    def test_rejects_duplicate_projects(self):
        path = self.lock(
            f"Example==1.0 --hash=sha256:{H1}\n"
            f"example==1.0 --hash=sha256:{H2}\n"
        )
        with self.assertRaisesRegex(module.LockContractError, "duplicate"):
            module.validate_lock(path)

    def test_rejects_missing_or_empty_lock(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(module.LockContractError, "missing"):
                module.validate_lock(Path(td) / "missing.lock")
        with self.assertRaisesRegex(module.LockContractError, "no dependency"):
            module.validate_lock(self.lock("# comments only\n"))


if __name__ == "__main__":
    unittest.main()
