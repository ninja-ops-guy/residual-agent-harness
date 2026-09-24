import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "r4_seal_manifest.py"
SPEC = importlib.util.spec_from_file_location("r4_seal_manifest", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class SealManifestCardinalityTests(unittest.TestCase):
    def write_file(self, root: Path, name: str, data: bytes) -> str:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return hashlib.sha256(data).hexdigest()

    def write_manifest(self, root: Path, names: list[str]) -> Path:
        manifest = root / "SHA256SUMS"
        manifest.write_text(
            "\n".join(f"{self.write_file(root, name, name.encode())}  {name}" for name in names)
            + "\n",
            encoding="utf-8",
        )
        return manifest

    def write_seal(self, root: Path, count: int) -> Path:
        seal = root / "SEAL.json"
        seal.write_text(
            json.dumps({"authoritative_manifest": {
                "entry_count": count,
                "entries_verified": count,
                "entries_failed": 0,
                "verification": "PASS",
            }}),
            encoding="utf-8",
        )
        return seal

    def test_cardinality_tracks_manifest_addition_and_removal_without_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.write_manifest(root, ["one", "two"])
            self.assertEqual(module.verify_authoritative_manifest(manifest)["entry_count"], 2)
            manifest = self.write_manifest(root, ["one", "two", "three"])
            self.assertEqual(module.verify_authoritative_manifest(manifest)["entry_count"], 3)
            manifest = self.write_manifest(root, ["one"])
            self.assertEqual(module.verify_authoritative_manifest(manifest)["entry_count"], 1)

    def test_verifier_rejects_recorded_cardinality_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.write_manifest(root, [f"entry-{index}" for index in range(50)])
            seal = self.write_seal(root, 44)
            with self.assertRaisesRegex(module.ManifestError, "recorded=44 authoritative=50"):
                module.verify_seal_cardinality(manifest, seal)

    def test_verifier_accepts_count_derived_from_same_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.write_manifest(root, ["a", "nested/b", "c"])
            derived = module.verify_authoritative_manifest(manifest)
            seal = self.write_seal(root, derived["entry_count"])
            self.assertEqual(module.verify_seal_cardinality(manifest, seal)["entry_count"], 3)

    def test_parser_rejects_invalid_duplicate_or_unsafe_entries(self):
        cases = [
            "not-a-hash  file\n",
            f"{'0' * 64}  duplicate\n{'1' * 64}  duplicate\n",
            f"{'0' * 64}  ../escape\n",
        ]
        for content in cases:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as temporary:
                manifest = Path(temporary) / "SHA256SUMS"
                manifest.write_text(content, encoding="utf-8")
                with self.assertRaises(module.ManifestError):
                    module.parse_authoritative_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
