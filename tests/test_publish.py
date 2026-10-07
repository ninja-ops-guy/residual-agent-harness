import tempfile
import unittest
from pathlib import Path

from scripts.publish import publish_commands


class PublishTests(unittest.TestCase):
    def test_private_visibility_and_explicit_repository_are_fixed(self):
        commands = publish_commands(Path("/tmp/repo"), "ninja-ops-guy", "residual-agent-harness", False)
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][3], "ninja-ops-guy/residual-agent-harness")
        self.assertIn("--private", commands[0])
        self.assertNotIn("--public", commands[0])

    def test_bundle_restore_preserves_working_tree(self):
        commands = publish_commands(Path("/tmp/repo"), "owner", "repo", True)
        self.assertEqual(commands[2][-2:], ["--mixed", "FETCH_HEAD"])
        self.assertNotIn("--hard", sum(commands, []))

    def test_unsupported_identifiers_cannot_inject_options(self):
        for owner in ("--public", "owner/other", "owner;command", "owner name"):
            with self.assertRaises(ValueError):
                publish_commands(Path("/tmp/repo"), owner, "repo", False)


if __name__ == "__main__":
    unittest.main()
