import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tests import test_r4_seal_manifest as base


module = base.module


class SealManifestAdversarialTests(unittest.TestCase):
    def manifest(self, root, entries):
        path = root / "SHA256SUMS"
        path.write_text("\n".join(entries) + "\n", encoding="utf-8")
        return path

    def entry(self, root, name, content=b"content"):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return f"{hashlib.sha256(content).hexdigest()}  {name}"

    def seal(self, root, count, extra=None):
        document = {"authoritative_manifest": {"entry_count": count,
            "entries_verified": count, "entries_failed": 0, "verification": "PASS"}}
        document.update(extra or {})
        path = root / "SEAL.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def test_added_and_removed_entries_change_authoritative_count(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            entries = [self.entry(root, "a"), self.entry(root, "b")]
            self.assertEqual(module.verify_authoritative_manifest(self.manifest(root, entries))["entry_count"], 2)
            entries.append(self.entry(root, "c"))
            self.assertEqual(module.verify_authoritative_manifest(self.manifest(root, entries))["entry_count"], 3)
            self.assertEqual(module.verify_authoritative_manifest(self.manifest(root, entries[:1]))["entry_count"], 1)

    def test_duplicate_malformed_absolute_and_traversal_paths_are_rejected(self):
        digest = "0" * 64
        cases = [
            [f"{digest}  same", f"{digest}  same"],
            ["malformed"],
            [f"{digest}  /absolute"],
            [f"{digest}  nested/../../escape"],
        ]
        for entries in cases:
            with self.subTest(entries=entries), tempfile.TemporaryDirectory() as td:
                with self.assertRaises(module.ManifestError):
                    module.parse_authoritative_manifest(self.manifest(Path(td), entries))

    def test_wrong_digest_and_missing_referenced_file_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wrong = self.manifest(root, [f"{'0' * 64}  present"])
            (root / "present").write_bytes(b"different")
            with self.assertRaisesRegex(module.ManifestError, "present"):
                module.verify_authoritative_manifest(wrong)
            missing = self.manifest(root, [f"{'0' * 64}  missing"])
            with self.assertRaisesRegex(module.ManifestError, "missing"):
                module.verify_authoritative_manifest(missing)

    def test_stale_derived_count_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = self.manifest(root, [self.entry(root, "a"), self.entry(root, "b")])
            with self.assertRaisesRegex(module.ManifestError, "recorded=1 authoritative=2"):
                module.verify_seal_cardinality(manifest, self.seal(root, 1))

    def test_extra_unmanifested_file_is_outside_current_cardinality_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = self.manifest(root, [self.entry(root, "authority")])
            (root / "unmanifested").write_text("extra", encoding="utf-8")
            self.assertEqual(module.verify_authoritative_manifest(manifest)["entry_count"], 1)

    def test_semantically_false_metadata_is_outside_current_cardinality_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = self.manifest(root, [self.entry(root, "authority")])
            seal = self.seal(root, 1, {"candidate": {"head": "semantically-false"}})
            self.assertEqual(module.verify_seal_cardinality(manifest, seal)["verification"], "PASS")

    def test_derived_artifact_can_be_hashed_but_provenance_is_outside_current_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            derived = json.dumps({"count": 999}).encode()
            manifest = self.manifest(root, [self.entry(root, "derived-summary.json", derived)])
            self.assertEqual(module.verify_authoritative_manifest(manifest)["entry_count"], 1)


if __name__ == "__main__":
    unittest.main()
