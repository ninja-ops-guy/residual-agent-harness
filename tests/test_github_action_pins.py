import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.validate_github_action_pins import audit

PIN = "1" * 40


class ActionPinAuditTests(unittest.TestCase):
    def _root(self, body: str) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        workflows = root / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text(body, encoding="utf-8")
        return root

    def test_commit_pinned_action_passes(self):
        result = audit(self._root(f"steps:\n  - uses: actions/checkout@{PIN}\n"))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["external_uses"], 1)

    def test_semver_tag_is_blocked(self):
        result = audit(self._root("steps:\n  - uses: actions/checkout@v4\n"))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(len(result["violations"]), 1)

    def test_branch_ref_is_blocked(self):
        result = audit(self._root("steps:\n  - uses: owner/action@main\n"))
        self.assertEqual(result["status"], "BLOCKED")

    def test_external_reusable_workflow_requires_pin(self):
        result = audit(
            self._root(
                "jobs:\n"
                "  call:\n"
                "    uses: owner/repo/.github/workflows/reuse.yml@release\n"
            )
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_local_action_is_ignored(self):
        result = audit(self._root("steps:\n  - uses: ./.github/actions/local\n"))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["external_uses"], 0)

    def test_docker_reference_is_outside_action_pin_gate(self):
        result = audit(self._root("steps:\n  - uses: docker://alpine:3.20\n"))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["external_uses"], 0)

    def test_quoted_target_and_comment_are_parsed(self):
        result = audit(
            self._root(
                f'jobs:\n  build:\n    uses: "owner/repo/.github/workflows/reuse.yml@{PIN}" # v1\n'
            )
        )
        self.assertEqual(result["status"], "PASS")

    def test_inline_mapping_uses_is_detected(self):
        result = audit(self._root("steps: [{uses: actions/checkout@v4}]\n"))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["external_uses"], 1)

    def test_quoted_uses_key_is_detected(self):
        result = audit(self._root('"steps":\n  - "uses": actions/checkout@v4\n'))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["external_uses"], 1)

    def test_uses_text_inside_run_block_is_not_an_action(self):
        result = audit(
            self._root(
                "steps:\n"
                "  - run: |\n"
                "      echo 'uses: actions/checkout@v4'\n"
            )
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["external_uses"], 0)

    def test_uses_text_inside_environment_value_is_not_an_action(self):
        result = audit(
            self._root(
                "env:\n"
                "  SAMPLE: 'uses: actions/checkout@v4'\n"
                "steps:\n"
                f"  - uses: actions/checkout@{PIN}\n"
            )
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["external_uses"], 1)

    def test_duplicate_uses_key_is_blocked(self):
        result = audit(
            self._root(
                "steps:\n"
                f"  - uses: actions/checkout@{PIN}\n"
                "    uses: actions/setup-python@v5\n"
            )
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("duplicate YAML mapping key" in x["reason"] for x in result["violations"]))

    def test_alias_is_blocked(self):
        result = audit(
            self._root(
                "steps:\n"
                f"  - &base {{uses: actions/checkout@{PIN}}}\n"
                "  - *base\n"
            )
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("aliases/anchors", result["reason"])

    def test_merge_key_is_blocked(self):
        result = audit(
            self._root(
                f"base: &base\n  uses: actions/checkout@{PIN}\n"
                "steps:\n"
                "  - <<: *base\n"
            )
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_custom_tag_is_blocked(self):
        result = audit(self._root("steps: !custom []\n"))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("unsupported YAML tag" in x["reason"] for x in result["violations"]))

    def test_malformed_yaml_is_blocked(self):
        result = audit(self._root("steps: [\n"))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("structurally parse", result["reason"])

    def test_non_scalar_uses_value_is_blocked(self):
        result = audit(self._root("steps:\n  - uses: [actions/checkout@v4]\n"))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("uses value must be a scalar string" in x["reason"] for x in result["violations"]))

    def test_missing_workflow_directory_fails_closed(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        result = audit(Path(td.name))
        self.assertEqual(result["status"], "BLOCKED")

    def test_unreadable_workflow_fails_closed(self):
        root = self._root(f"steps:\n  - uses: actions/checkout@{PIN}\n")
        with mock.patch.object(Path, "read_text", side_effect=PermissionError("denied")):
            result = audit(root)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("unable to structurally parse workflow", result["reason"])


if __name__ == "__main__":
    unittest.main()
