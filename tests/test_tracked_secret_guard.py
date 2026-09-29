from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_tracked_secrets import scan


class TrackedSecretGuardTests(unittest.TestCase):
    def test_rejects_realistic_secret_patterns(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.txt"
            path.write_text("token=github_pat_" + "A" * 30, encoding="utf-8")
            findings = scan([path])
        self.assertTrue(any("github_pat" in item for item in findings))

    def test_short_synthetic_test_secret_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "fixture.py"
            path.write_text("key='sk-cp-upstream-secret'", encoding="utf-8")
            self.assertEqual(scan([path]), [])

    def test_rejects_private_key_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "fixture.txt"
            path.write_text("-----BEGIN PRIVATE KEY-----\nnot-real\n", encoding="utf-8")
            findings = scan([path])
        self.assertTrue(any("private_key" in item for item in findings))

    def test_rejects_tracked_env_file_by_name(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / ".env"
            path.write_text("EMPTY=", encoding="utf-8")
            findings = scan([path])
        self.assertTrue(any("forbidden credential-bearing" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
