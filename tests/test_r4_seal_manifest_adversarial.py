import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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


class SealManifestContainmentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.package = self.root / "package"
        self.outside = self.root / "outside"
        self.package.mkdir()
        self.outside.mkdir()
        self.data = b"disposable evidence"
        (self.outside / "data").write_bytes(self.data)
        self.manifest = self.package / "SHA256SUMS"

    def write_manifest(self, name="data"):
        self.manifest.write_text(
            f"{hashlib.sha256(self.data).hexdigest()}  {name}\n", encoding="utf-8")
        return self.manifest

    def reject(self):
        with self.assertRaises(module.ManifestError):
            module.verify_authoritative_manifest(self.manifest)

    def test_external_file_symlink_is_rejected_even_when_digest_matches(self):
        (self.package / "data").symlink_to(self.outside / "data")
        self.write_manifest()
        self.reject()

    def test_external_parent_symlink_is_rejected_even_when_digest_matches(self):
        (self.package / "nested").symlink_to(self.outside, target_is_directory=True)
        self.write_manifest("nested/data")
        self.reject()

    def test_internal_file_symlink_is_also_rejected(self):
        (self.package / "real").write_bytes(self.data)
        (self.package / "data").symlink_to("real")
        self.write_manifest()
        self.reject()

    def test_internal_parent_symlink_is_also_rejected(self):
        (self.package / "real").mkdir()
        (self.package / "real/data").write_bytes(self.data)
        (self.package / "nested").symlink_to("real", target_is_directory=True)
        self.write_manifest("nested/data")
        self.reject()

    def test_broken_and_looping_symlinks_fail_closed(self):
        for target in ("missing", "data"):
            with self.subTest(target=target):
                link = self.package / "data"
                link.symlink_to(target)
                self.write_manifest()
                self.reject()
                link.unlink()

    def test_manifest_itself_cannot_be_a_symlink(self):
        (self.package / "data").write_bytes(self.data)
        self.write_manifest()
        original = self.outside / "SHA256SUMS"
        self.manifest.rename(original)
        self.manifest.symlink_to(original)
        self.reject()
        with self.assertRaises(module.ManifestError):
            module.parse_authoritative_manifest(self.manifest)

    def test_nested_regular_file_is_accepted_and_manifest_digest_matches(self):
        (self.package / "nested").mkdir()
        (self.package / "nested/data").write_bytes(self.data)
        self.write_manifest("nested/data")
        result = module.verify_authoritative_manifest(self.manifest)
        self.assertEqual(result["verification"], "PASS")
        self.assertEqual(result["entry_count"], 1)
        self.assertEqual(result["sha256sums_sha256"],
                         hashlib.sha256(self.manifest.read_bytes()).hexdigest())

    def test_path_aliases_and_non_posix_paths_are_rejected(self):
        for name in ("./data", "nested//data", "nested/./data", "data/", "a\\b", "a\x00b"):
            with self.subTest(name=name):
                self.write_manifest(name)
                with self.assertRaises(module.ManifestError):
                    module.parse_authoritative_manifest(self.manifest)

    def test_directory_and_fifo_are_rejected_without_blocking(self):
        for kind in ("directory", "fifo"):
            with self.subTest(kind=kind):
                target = self.package / "data"
                if kind == "directory":
                    target.mkdir()
                else:
                    os.mkfifo(target)
                self.write_manifest()
                self.reject()
                if kind == "directory":
                    target.rmdir()
                else:
                    target.unlink()

    def test_unsupported_secure_open_fails_closed(self):
        (self.package / "data").write_bytes(self.data)
        self.write_manifest()
        with patch.object(module, "_SECURE_OPEN", False):
            with self.assertRaisesRegex(module.ManifestError, "unavailable"):
                module.verify_authoritative_manifest(self.manifest)

    def test_leaf_swapped_to_symlink_immediately_before_open_is_rejected(self):
        target = self.package / "data"
        target.write_bytes(self.data)
        self.write_manifest()
        real_open = os.open
        injected = []

        def swap(path, flags, *args, **kwargs):
            if path == "data" and kwargs.get("dir_fd") is not None:
                target.unlink()
                target.symlink_to(self.outside / "data")
                injected.append(True)
            return real_open(path, flags, *args, **kwargs)

        with patch.object(module.os, "open", side_effect=swap):
            self.reject()
        self.assertEqual(injected, [True])

    def test_parent_swapped_to_symlink_immediately_before_open_is_rejected(self):
        nested = self.package / "nested"
        nested.mkdir()
        (nested / "data").write_bytes(self.data)
        self.write_manifest("nested/data")
        real_open = os.open
        injected = []

        def swap(path, flags, *args, **kwargs):
            if path == "nested" and kwargs.get("dir_fd") is not None:
                nested.rename(self.package / "retained")
                nested.symlink_to(self.outside, target_is_directory=True)
                injected.append(True)
            return real_open(path, flags, *args, **kwargs)

        with patch.object(module.os, "open", side_effect=swap):
            self.reject()
        self.assertEqual(injected, [True])

    def test_opened_parent_descriptor_is_not_replaced_by_later_path_swap(self):
        nested = self.package / "nested"
        nested.mkdir()
        (nested / "data").write_bytes(self.data)
        (self.outside / "data").write_bytes(b"must not be read")
        self.write_manifest("nested/data")
        real_open = os.open
        injected = []

        def swap(path, flags, *args, **kwargs):
            if path == "data" and kwargs.get("dir_fd") is not None:
                nested.rename(self.package / "retained")
                nested.symlink_to(self.outside, target_is_directory=True)
                injected.append(True)
            return real_open(path, flags, *args, **kwargs)

        with patch.object(module.os, "open", side_effect=swap):
            result = module.verify_authoritative_manifest(self.manifest)
        self.assertEqual(injected, [True])
        self.assertEqual(result["verification"], "PASS")

    def test_manifest_digest_binds_parsed_bytes_not_a_later_path_read(self):
        (self.package / "data").write_bytes(self.data)
        self.write_manifest()
        expected = hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        parse = module._parse_manifest

        def replace_after_read(raw):
            self.manifest.write_text("replacement is not authoritative", encoding="utf-8")
            return parse(raw)

        with patch.object(module, "_parse_manifest", side_effect=replace_after_read):
            result = module.verify_authoritative_manifest(self.manifest)
        self.assertEqual(result["sha256sums_sha256"], expected)

    def test_repeated_rejections_do_not_leak_descriptors(self):
        (self.package / "data").symlink_to(self.outside / "data")
        self.write_manifest()
        # Linux qualification target; no timing-dependent assertion.
        descriptors = Path("/proc/self/fd")
        before = len(list(descriptors.iterdir()))
        for _ in range(50):
            self.reject()
        self.assertEqual(len(list(descriptors.iterdir())), before)


if __name__ == "__main__":
    unittest.main()
