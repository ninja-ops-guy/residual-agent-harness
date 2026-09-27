import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tests import test_r4_seal_manifest as base


module = base.module


class SealManifestMetadataSchemaTests(unittest.TestCase):
    def manifest(self, root: Path) -> Path:
        content = b"authority"
        (root / "authority").write_bytes(content)
        manifest = root / "SHA256SUMS"
        manifest.write_text(f"{hashlib.sha256(content).hexdigest()}  authority\n", encoding="utf-8")
        return manifest

    def seal(self, root: Path, metadata: dict) -> Path:
        seal = root / "SEAL.json"
        seal.write_text(json.dumps({"authoritative_manifest": metadata}), encoding="utf-8")
        return seal

    def test_exact_nonnegative_integer_counts_are_required(self):
        invalid_metadata = [
            {"entry_count": True, "entries_verified": True, "entries_failed": False, "verification": "PASS"},
            {"entry_count": 1.0, "entries_verified": 1.0, "entries_failed": 0, "verification": "PASS"},
            {"entry_count": "1", "entries_verified": 1, "entries_failed": 0, "verification": "PASS"},
            {"entry_count": 1, "entries_verified": "1", "entries_failed": 0, "verification": "PASS"},
            {"entry_count": 1, "entries_verified": 1, "entries_failed": "0", "verification": "PASS"},
            {"entry_count": -1, "entries_verified": 1, "entries_failed": 0, "verification": "PASS"},
            {"entry_count": 1, "entries_verified": -1, "entries_failed": 0, "verification": "PASS"},
            {"entry_count": 1, "entries_verified": 1, "entries_failed": -1, "verification": "PASS"},
        ]
        for metadata in invalid_metadata:
            with self.subTest(metadata=metadata), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                manifest = self.manifest(root)
                seal = self.seal(root, metadata)
                with self.assertRaisesRegex(module.ManifestError, "nonnegative integer"):
                    module.verify_seal_cardinality(manifest, seal)

    def test_legacy_authoritative_evidence_count_must_also_be_exact_integer(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = self.manifest(root)
            seal = root / "SEAL.json"
            seal.write_text(json.dumps({"authoritative_evidence": {"sha256sums_verification": {
                "entries_verified": True,
                "entries_failed": 0,
                "verification": "PASS",
            }}}), encoding="utf-8")
            with self.assertRaisesRegex(module.ManifestError, "nonnegative integer"):
                module.verify_seal_cardinality(manifest, seal)

    def test_valid_exact_integer_metadata_still_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = self.manifest(root)
            seal = self.seal(root, {
                "entry_count": 1,
                "entries_verified": 1,
                "entries_failed": 0,
                "verification": "PASS",
            })
            self.assertEqual(module.verify_seal_cardinality(manifest, seal)["entry_count"], 1)


if __name__ == "__main__":
    unittest.main()
