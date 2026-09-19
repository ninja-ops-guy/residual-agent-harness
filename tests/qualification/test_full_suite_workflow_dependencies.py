from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FULL_SUITE_WORKFLOWS = (
    ".github/workflows/ci.yml",
    ".github/workflows/station.yml",
    ".github/workflows/factory.yml",
    ".github/workflows/factory-execution.yml",
)


class FullSuiteWorkflowDependencyTests(unittest.TestCase):
    def test_full_suite_workflows_install_qualification_extra(self) -> None:
        extra_pattern = re.compile(r"\.\[(?:factory,qualification|qualification,factory)\]")
        for relative_path in FULL_SUITE_WORKFLOWS:
            with self.subTest(workflow=relative_path):
                text = (ROOT / relative_path).read_text(encoding="utf-8")
                self.assertIn("discover -s tests", text)
                self.assertRegex(text, extra_pattern)


if __name__ == "__main__":
    unittest.main()
