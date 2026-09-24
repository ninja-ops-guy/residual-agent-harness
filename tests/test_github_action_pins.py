import tempfile
import unittest
from pathlib import Path

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

    def test_missing_workflow_directory_fails_closed(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        result = audit(Path(td.name))
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
