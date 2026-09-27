from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from scripts.validate_github_action_pins import PIN_RE, external_uses

ROOT = Path(__file__).resolve().parents[1]
PIN_SET = ROOT / "docs" / "v1" / "V1_GITHUB_ACTION_PIN_SET.json"
WORKFLOWS = ROOT / ".github" / "workflows"
ACTIONS = ROOT / ".github" / "actions"
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class ActionPinSetTests(unittest.TestCase):
    def _pin_data(self) -> tuple[dict[str, str], dict[str, str]]:
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
            allowed[action] = sha.lower()

        containers: dict[str, str] = {}
        for entry in data.get("container_images", []):
            image = entry["image"]
            digest = entry["digest"]
            self.assertNotIn(image, containers, f"duplicate container image: {image}")
            self.assertTrue(digest.startswith("sha256:"), f"container digest lacks sha256 prefix: {digest}")
            value = digest.removeprefix("sha256:")
            self.assertRegex(value, DIGEST_RE)
            containers[image] = value.lower()

        return allowed, containers

    def test_every_external_workflow_ref_matches_reviewed_pin_set(self):
        allowed, containers = self._pin_data()
        seen: set[str] = set()
        seen_containers: set[str] = set()
        paths = [*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")]
        if ACTIONS.is_dir():
            paths.extend(ACTIONS.glob("**/action.yml"))
            paths.extend(ACTIONS.glob("**/action.yaml"))

        for path in sorted(set(paths)):
            uses, structural_findings = external_uses(path)
            self.assertFalse(
                structural_findings,
                f"{path} has structurally invalid workflow syntax: {structural_findings}",
            )
            for lineno, target in uses:
                if target.startswith("docker://"):
                    image_ref = target.removeprefix("docker://")
                    self.assertIn(
                        "@sha256:",
                        image_ref,
                        f"{path}:{lineno} docker image is not digest pinned: {target}",
                    )
                    image, digest = image_ref.rsplit("@sha256:", 1)
                    self.assertRegex(
                        digest,
                        DIGEST_RE,
                        f"{path}:{lineno} docker digest is not SHA-256: {target}",
                    )
                    self.assertIn(
                        image,
                        containers,
                        f"{path}:{lineno} container image is not in reviewed pin set: {image}",
                    )
                    self.assertEqual(
                        digest.lower(),
                        containers[image],
                        f"{path}:{lineno} container digest differs from reviewed set",
                    )
                    seen_containers.add(image)
                    continue

                self.assertIn("@", target, f"{path}:{lineno} external use has no ref")
                action, ref = target.rsplit("@", 1)
                self.assertRegex(ref, PIN_RE, f"{path}:{lineno} ref is not immutable: {target}")
                self.assertIn(action, allowed, f"{path}:{lineno} action is not in reviewed pin set: {action}")
                self.assertEqual(ref.lower(), allowed[action], f"{path}:{lineno} pin differs from reviewed set")
                seen.add(action)

        self.assertTrue(seen, "no external workflow refs discovered")
        missing = set(allowed) - seen
        self.assertFalse(missing, f"reviewed pin-set entries are unused: {sorted(missing)}")

        missing_containers = set(containers) - seen_containers
        self.assertFalse(
            missing_containers,
            f"reviewed container-image entries are unused: {sorted(missing_containers)}",
        )


if __name__ == "__main__":
    unittest.main()
