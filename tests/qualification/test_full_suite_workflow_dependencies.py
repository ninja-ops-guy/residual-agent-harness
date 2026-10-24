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

    def test_node_contract_jobs_pin_supported_node(self) -> None:
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        station = (ROOT / ".github/workflows/station.yml").read_text(encoding="utf-8")
        ci_tests = ci[ci.index("  tests:"):]
        station_python = station[station.index("  python:"):station.index("\n  browser:")]
        for workflow_section in (ci_tests, station_python):
            self.assertIn("uses: actions/setup-node@v4", workflow_section)
            self.assertIn("node-version: '22'", workflow_section)

    def test_playwright_jobs_pin_supported_ubuntu_runner(self) -> None:
        station = (ROOT / ".github/workflows/station.yml").read_text(encoding="utf-8")
        qualification = (ROOT / ".github/workflows/qualification-v1.yml").read_text(encoding="utf-8")
        station_browser = station[station.index("  browser:"):station.index("\n  docker:")]
        qualification_browser = qualification[
            qualification.index("  browser:"):qualification.index("\n\n  concurrency:")
        ]
        qualification_adversarial = qualification[
            qualification.index("  browser-adversarial:"):qualification.index("\n  redteam:")
        ]
        for workflow_section in (
            station_browser,
            qualification_browser,
            qualification_adversarial,
        ):
            self.assertIn("runs-on: ubuntu-24.04", workflow_section)
            self.assertNotIn("runs-on: ubuntu-latest", workflow_section)

    def test_deterministic_qualification_provisions_real_bubblewrap(self) -> None:
        text = (ROOT / ".github/workflows/qualification-v1.yml").read_text(encoding="utf-8")
        start = text.index("  deterministic:")
        end = text.index("\n  discovery:", start)
        deterministic = text[start:end]
        self.assertIn("runs-on: ubuntu-22.04", deterministic)
        self.assertNotIn("runs-on: ubuntu-latest", deterministic)
        self.assertIn("sudo apt-get install -y bubblewrap", deterministic)
        self.assertIn("command -v bwrap", deterministic)
        self.assertIn("bwrap --version", deterministic)
        self.assertIn("--unshare-pid --unshare-net", deterministic)
        self.assertIn("--ro-bind / / -- /bin/true", deterministic)
        self.assertNotIn("continue-on-error: true", deterministic)


if __name__ == "__main__":
    unittest.main()
