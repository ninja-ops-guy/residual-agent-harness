import copy
import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_release_receipt.py"
SPEC = importlib.util.spec_from_file_location("validate_release_receipt", MODULE_PATH)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class ReleaseReceiptBindingTests(unittest.TestCase):
    def setUp(self):
        release_commit = "1" * 40
        self.doc = {
            "schema_version": "residual.release-receipt.v1",
            "release": "v1.0.0",
            "canary_provenance": {
                "candidate": {
                    "commit": mod.CANARY_COMMIT,
                    "tree": mod.CANARY_TREE,
                    "parent": mod.CANARY_PARENT,
                },
                "post_canary_report_sha256": "a" * 64,
            },
            "candidate": {
                "commit": release_commit,
                "tree": "2" * 40,
                "parent": "3" * 40,
            },
            "rc_tag": {
                "name": "v1.0.0-rc.1",
                "commit": release_commit,
                "signature_verified": True,
            },
            "final_tag": None,
            "binding_verification": {
                "candidate_rc_equal": True,
                "candidate_final_equal": None,
                "validator": "scripts/validate_release_receipt.py@reviewed",
                "verified_at": "2026-09-24T00:00:00Z",
                "report_sha256": "b" * 64,
            },
        }

    def test_rc_binding_passes_without_final_tag(self):
        mod.validate_binding(self.doc)

    def test_rejects_rc_tag_on_different_commit(self):
        doc = copy.deepcopy(self.doc)
        doc["rc_tag"]["commit"] = "4" * 40
        with self.assertRaisesRegex(mod.ReceiptBindingError, "rc_tag.commit"):
            mod.validate_binding(doc)

    def test_rejects_unverified_rc_tag_signature(self):
        doc = copy.deepcopy(self.doc)
        doc["rc_tag"]["signature_verified"] = False
        with self.assertRaisesRegex(mod.ReceiptBindingError, "rc_tag signature"):
            mod.validate_binding(doc)

    def test_rejects_wrong_canary_provenance(self):
        doc = copy.deepcopy(self.doc)
        doc["canary_provenance"]["candidate"]["commit"] = "5" * 40
        with self.assertRaisesRegex(mod.ReceiptBindingError, "canary provenance"):
            mod.validate_binding(doc)

    def test_final_tag_must_match_release_candidate(self):
        doc = copy.deepcopy(self.doc)
        doc["final_tag"] = {
            "name": "v1.0.0",
            "commit": doc["candidate"]["commit"],
            "signature_verified": True,
        }
        doc["binding_verification"]["candidate_final_equal"] = True
        mod.validate_binding(doc)

        doc["final_tag"]["commit"] = "6" * 40
        with self.assertRaisesRegex(mod.ReceiptBindingError, "final_tag.commit"):
            mod.validate_binding(doc)

    def test_rejects_unverified_final_tag_signature(self):
        doc = copy.deepcopy(self.doc)
        doc["final_tag"] = {
            "name": "v1.0.0",
            "commit": doc["candidate"]["commit"],
            "signature_verified": False,
        }
        doc["binding_verification"]["candidate_final_equal"] = True
        with self.assertRaisesRegex(mod.ReceiptBindingError, "final_tag signature"):
            mod.validate_binding(doc)

    def test_binding_flags_fail_closed(self):
        doc = copy.deepcopy(self.doc)
        doc["binding_verification"]["candidate_rc_equal"] = False
        with self.assertRaisesRegex(mod.ReceiptBindingError, "candidate_rc_equal"):
            mod.validate_binding(doc)

        doc = copy.deepcopy(self.doc)
        doc["binding_verification"]["candidate_final_equal"] = True
        with self.assertRaisesRegex(mod.ReceiptBindingError, "must be null"):
            mod.validate_binding(doc)


if __name__ == "__main__":
    unittest.main()
