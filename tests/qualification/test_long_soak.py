from __future__ import annotations

import unittest

import scripts.qualification_long_soak as long_soak


class LongSoakSourceContinuityTests(unittest.TestCase):
    def test_same_clean_commit_and_tree_pass(self):
        identity = {"commit": "a" * 40, "tree": "b" * 40, "tracked_source_dirty": False}
        self.assertTrue(long_soak.source_continuity_ok(identity, dict(identity)))

    def test_dirty_source_fails(self):
        start = {"commit": "a" * 40, "tree": "b" * 40, "tracked_source_dirty": True}
        end = {"commit": "a" * 40, "tree": "b" * 40, "tracked_source_dirty": False}
        self.assertFalse(long_soak.source_continuity_ok(start, end))

    def test_commit_or_tree_change_fails(self):
        start = {"commit": "a" * 40, "tree": "b" * 40, "tracked_source_dirty": False}
        changed_commit = {"commit": "c" * 40, "tree": "b" * 40, "tracked_source_dirty": False}
        changed_tree = {"commit": "a" * 40, "tree": "d" * 40, "tracked_source_dirty": False}
        self.assertFalse(long_soak.source_continuity_ok(start, changed_commit))
        self.assertFalse(long_soak.source_continuity_ok(start, changed_tree))

    def test_unknown_git_identity_fails(self):
        unknown = {"commit": None, "tree": None, "tracked_source_dirty": None}
        self.assertFalse(long_soak.source_continuity_ok(unknown, unknown))


if __name__ == "__main__":
    unittest.main()
