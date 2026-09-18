"""Bridge pytest-style Copilot suites into the repository unittest gate.

The authoritative CI matrix invokes scripts/qualification_unittest.py, so this
unittest-discovered test launches pytest only for the Copilot enterprise suite.
A pytest failure therefore fails the existing qualification job on every Python
matrix version instead of silently leaving function-style tests undiscovered.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENTERPRISE = ROOT / "tests" / "enterprise"


class CopilotPytestQualification(unittest.TestCase):
    def test_copilot_enterprise_pytest_suite(self):
        files = sorted(ENTERPRISE.glob("test_copilot*.py"))
        self.assertTrue(files, "no Copilot enterprise qualification files found")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "--maxfail=1",
                *[str(path.relative_to(ROOT)) for path in files],
            ],
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            "Copilot pytest qualification suite failed",
        )


if __name__ == "__main__":
    unittest.main()
