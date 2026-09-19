"""Regression: GitHub checkout credentials must never persist in workflow worktrees."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
CHECKOUT = "uses: actions/checkout@v4"


class CheckoutCredentialPersistenceTests(unittest.TestCase):
    def test_every_checkout_disables_persisted_credentials(self):
        seen = 0
        for path in sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml"))):
            lines = path.read_text(encoding="utf-8").splitlines()
            for index, line in enumerate(lines):
                if CHECKOUT not in line:
                    continue
                seen += 1
                indent = len(line) - len(line.lstrip())
                step_indent = indent if line.lstrip().startswith("- ") else max(0, indent - 2)
                block = [line]
                for candidate in lines[index + 1 :]:
                    candidate_indent = len(candidate) - len(candidate.lstrip())
                    if candidate.lstrip().startswith("- ") and candidate_indent <= step_indent:
                        break
                    block.append(candidate)
                self.assertTrue(
                    any(item.strip() == "persist-credentials: false" for item in block),
                    f"{path.relative_to(ROOT)} checkout at line {index + 1} persists credentials",
                )
        self.assertGreater(seen, 0, "no actions/checkout@v4 steps discovered")


if __name__ == "__main__":
    unittest.main()
