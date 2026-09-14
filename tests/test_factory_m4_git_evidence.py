"""Issue #63 M4-4: Git base evidence is typed ABSENT/UNKNOWN/ERROR/PRESENT.

A failed lookup must never be silently reclassified as absence.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from residual.factory.m4_git_evidence import (
    GitBlobEvidence, GitEvidenceState, read_base_blob,
)
from residual.factory.runtime_workspace import git


class GitEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        (self.repo / "present.txt").write_bytes(b"content\n")
        git(self.repo, "init")
        git(self.repo, "add", ".")
        git(self.repo, "-c", "user.name=t", "-c", "user.email=t@localhost", "commit", "-m", "base")
        self.base = git(self.repo, "rev-parse", "HEAD").decode().strip()

    def evidence(self, commit, path):
        return read_base_blob(self.repo, commit, path)

    def test_valid_base_and_present_path(self):
        ev = self.evidence(self.base, "present.txt")
        self.assertEqual(ev.state, GitEvidenceState.PRESENT)
        self.assertEqual(ev.data, b"content\n")

    def test_valid_base_and_absent_path(self):
        ev = self.evidence(self.base, "missing.txt")
        self.assertEqual(ev.state, GitEvidenceState.ABSENT)
        self.assertIsNone(ev.data)

    def test_absent_is_distinct_from_empty_file(self):
        (self.repo / "empty.txt").write_bytes(b"")
        git(self.repo, "add", ".")
        git(self.repo, "-c", "user.name=t", "-c", "user.email=t@localhost", "commit", "-m", "x")
        head = git(self.repo, "rev-parse", "HEAD").decode().strip()
        self.assertEqual(self.evidence(head, "empty.txt").data, b"")
        self.assertEqual(self.evidence(head, "nope.txt").state, GitEvidenceState.ABSENT)

    def test_malformed_commit_ref_is_error(self):
        for bad in ("not-a-sha", "z" * 40, "", "../etc"):
            with self.subTest(bad=bad):
                self.assertEqual(self.evidence(bad, "present.txt").state, GitEvidenceState.ERROR)

    def test_nonexistent_commit_is_unknown(self):
        missing = "0" * 40
        ev = self.evidence(missing, "present.txt")
        self.assertEqual(ev.state, GitEvidenceState.UNKNOWN)
        self.assertEqual(ev.detail, "base_commit_unresolvable")

    def test_corrupt_object_is_error_not_absence(self):
        oid = git(self.repo, "rev-parse", f"{self.base}:present.txt").decode().strip()
        (self.repo / ".git" / "objects" / oid[:2] / oid[2:]).unlink()
        ev = self.evidence(self.base, "present.txt")
        self.assertEqual(ev.state, GitEvidenceState.ERROR)

    def test_command_failure_is_error(self):
        import residual.factory.m4_git_evidence as mod
        real = mod._run

        def fail_ls_tree(repository, arguments, **kwargs):
            if arguments[0] == "ls-tree":
                return 128, b""
            return real(repository, arguments, **kwargs)

        with patch.object(mod, "_run", side_effect=fail_ls_tree):
            ev = self.evidence(self.base, "missing.txt")
        self.assertEqual(ev.state, GitEvidenceState.ERROR)
        self.assertEqual(ev.detail, "git_command_failed")

    def test_git_timeout_is_unknown(self):
        import residual.factory.m4_git_evidence as mod

        def timeout(repository, arguments, **kwargs):
            raise mod._GitTimeout("simulated")

        with patch.object(mod, "_run", side_effect=timeout):
            ev = self.evidence(self.base, "missing.txt")
        self.assertEqual(ev.state, GitEvidenceState.UNKNOWN)
        self.assertEqual(ev.detail, "git_timeout")

    def test_missing_repository_evidence(self):
        empty = Path(self.temp.name) / "not-a-repo"
        empty.mkdir()
        ev = read_base_blob(empty, self.base, "present.txt")
        self.assertEqual(ev.state, GitEvidenceState.UNKNOWN)

    def test_invalid_path_is_error(self):
        for bad in ("../escape", "/absolute", ".git/config", "a\\b"):
            with self.subTest(bad=bad):
                self.assertEqual(self.evidence(self.base, bad).state, GitEvidenceState.ERROR)

    def test_evidence_value_invariants(self):
        with self.assertRaises(ValueError):
            GitBlobEvidence(GitEvidenceState.PRESENT, None, "bad")
        with self.assertRaises(ValueError):
            GitBlobEvidence(GitEvidenceState.ABSENT, b"x", "bad")


if __name__ == "__main__":
    unittest.main()
