"""Structural regression for issue #305 CI queue saturation."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TriggerHygieneTests(unittest.TestCase):
    def _workflow(self, name):
        return (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")

    def test_heavy_general_workflows_push_only_on_main(self):
        for name in ("ci.yml", "station.yml"):
            with self.subTest(workflow=name):
                text = self._workflow(name)
                push = text.split("  push:\n", 1)[1].split("  pull_request:", 1)[0]
                self.assertIn("branches: [main]", push)
                self.assertNotRegex(push, re.compile(r"^\s+paths(-ignore)?:", re.MULTILINE))
                self.assertIn("  pull_request:", text)

    def test_superseded_pr_runs_cancel_but_main_runs_do_not(self):
        for name in ("ci.yml", "station.yml"):
            with self.subTest(workflow=name):
                text = self._workflow(name)
                self.assertIn("github.event.pull_request.number || github.ref", text)
                self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", text)

    def test_production_pages_keeps_non_cancelling_main_semantics(self):
        pages = self._workflow("pages.yml")
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", pages)
        self.assertIn("|| 'production' }}", pages)


if __name__ == "__main__":
    unittest.main()
