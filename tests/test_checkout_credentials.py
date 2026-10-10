"""Regressions for GitHub checkout credential hardening."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
CHECKOUT = "uses: actions/checkout@v4"


class CheckoutCredentialPersistenceTests(unittest.TestCase):
    def test_every_checkout_disables_persisted_credentials_with_valid_step_indentation(self):
        seen = 0
        for path in sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml"))):
            lines = path.read_text(encoding="utf-8").splitlines()
            for index, line in enumerate(lines):
                if CHECKOUT not in line:
                    continue
                seen += 1
                uses_indent = len(line) - len(line.lstrip())
                inline_step = line.lstrip().startswith("- uses:")
                step_indent = uses_indent if inline_step else max(0, uses_indent - 2)
                expected_with_indent = uses_indent + 2 if inline_step else uses_indent
                block: list[tuple[int, str]] = []
                for candidate in lines[index + 1 :]:
                    candidate_indent = len(candidate) - len(candidate.lstrip())
                    if candidate.lstrip().startswith("- ") and candidate_indent <= step_indent:
                        break
                    block.append((candidate_indent, candidate.strip()))
                with_positions = [i for i, (indent, text) in enumerate(block) if text == "with:" and indent == expected_with_indent]
                self.assertTrue(
                    with_positions,
                    f"{path.relative_to(ROOT)} checkout at line {index + 1} lacks a correctly indented with: block",
                )
                with_pos = with_positions[0]
                self.assertIn(
                    (expected_with_indent + 2, "persist-credentials: false"),
                    block[with_pos + 1 :],
                    f"{path.relative_to(ROOT)} checkout at line {index + 1} persists credentials",
                )
        self.assertGreater(seen, 0, "no actions/checkout@v4 steps discovered")


if __name__ == "__main__":
    unittest.main()
