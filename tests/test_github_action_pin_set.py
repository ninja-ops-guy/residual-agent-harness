from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from scripts.validate_github_action_pins import PIN_RE, external_uses

ROOT = Path(__file__).resolve().parents[1]
PIN_SET = ROOT / "docs" / "v1" / "V1_GITHUB_ACTION_PIN_SET.json"
WORKFLOWS = ROOT / ".github" / "workflows"


class ActionPinSetTests(unittest.TestCase):
    def _allowed(self) -> dict[str, str]:
        data = json.loads(PIN_SET.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "residual.v1.github-action-pin-set/1")
        actions = data["actions"]
        self.assertTrue(actions, "pin set is empty")
        allowed: dict[str, str] = {}
        for entry in actions:
            action = entry["action"]
            sha = entry["sha"]
            self.assertNotIn(action, allowed, f"duplicate pin-set action: {action}")
            self.assertRegex(sha, re.compile(r"^[0-9a-f]{40}$"))
            allowed[action] = sha
        return allowed

    def test_every_external_workflow_ref_matches_reviewed_pin_set(self):
        allowed = self._allowed()
        seen: set[str] = set()
        for path in sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml"))):
            uses, structural_findings = external_uses(path)
            self.assertFalse(
                structural_findings,
                f"{path} has structurally invalid workflow syntax: {structural_findings}",
            )
            for lineno, target in uses:
                self.assertIn("@", target, f"{path}:{lineno} external use has no ref")
                action, ref = target.rsplit("@", 1)
                self.assertRegex(ref, PIN_RE, f"{path}:{lineno} ref is not immutable: {target}")
                self.assertIn(action, allowed, f"{path}:{lineno} action is not in reviewed pin set: {action}")
                self.assertEqual(ref.lower(), allowed[action].lower(), f"{path}:{lineno} pin differs from reviewed set")
                seen.add(action)

        self.assertTrue(seen, "no external workflow refs discovered")
        missing = set(allowed) - seen
        self.assertFalse(missing, f"reviewed pin-set entries are unused: {sorted(missing)}")


if __name__ == "__main__":
    unittest.main()
