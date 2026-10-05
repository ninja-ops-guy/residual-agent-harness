"""Governance self-integrity (Lane D, D2): the gate checkers, their tests,
and the gate workflows must not change silently.

verifier/v3/governance_integrity.json pins the git blob SHA of every
governance-critical file. Any modification, rename, or deletion fails this
test unless the manifest is advanced in the same change with a non-empty
justification (mirroring verifier/v3/factory_ownership_baseline.json).
The manifest cannot pin itself; its schema and non-empty justification are
asserted here instead.
"""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "verifier" / "v3" / "governance_integrity.json"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class GovernanceIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_schema(self):
        self.assertIsInstance(self.manifest.get("pinned_at"), str)
        self.assertEqual(len(self.manifest["pinned_at"]), 40)
        int(self.manifest["pinned_at"], 16)
        justification = self.manifest.get("justification")
        self.assertIsInstance(justification, str)
        self.assertTrue(justification.strip(), "manifest must carry a non-empty justification")
        files = self.manifest.get("files")
        self.assertIsInstance(files, dict)
        self.assertTrue(files, "manifest pins no files")

    def test_gate_checkers_are_pinned(self):
        files = self.manifest["files"]
        for required in (
            "verifier/v3/check_factory_ownership.py",
            "verifier/v3/qualify_clean_install.py",
            "scripts/check_maintainer_approval.py",
            "tests/test_factory_ownership_gate.py",
            "tests/test_maintainer_approval_gate.py",
            "tests/test_clean_install_qualification.py",
            "tests/test_governance_gate_index.py",
            "tests/test_governance_integrity.py",
            ".github/workflows/maintainer-approval.yml",
            ".github/workflows/pr-agent.yml",
            ".github/workflows/pages.yml",
        ):
            self.assertIn(required, files, f"governance-critical file {required} is not pinned")

    def test_every_pinned_blob_matches_the_checkout(self):
        for rel, pinned in self.manifest["files"].items():
            with self.subTest(file=rel):
                path = ROOT / rel
                self.assertTrue(
                    path.is_file(),
                    f"pinned file {rel} was deleted or renamed; advance "
                    "verifier/v3/governance_integrity.json in the same change "
                    "with a non-empty justification",
                )
                self.assertEqual(
                    git_blob_sha(path), pinned,
                    f"{rel} no longer matches its governance integrity pin; "
                    "if this change is authorized, advance "
                    "verifier/v3/governance_integrity.json in the same change "
                    "with a non-empty justification",
                )


if __name__ == "__main__":
    unittest.main()
