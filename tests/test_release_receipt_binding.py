import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_release_receipt.py"
SPEC = importlib.util.spec_from_file_location("validate_release_receipt", MODULE_PATH)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class ReleaseReceiptBindingTests(unittest.TestCase):
    def setUp(self):
        release_commit = "1" * 40
        artifact = "c" * 64
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
            "artifact": [{
                "name":"residual.whl",
                "media_type":"application/zip",
                "size":1,
                "sha256":artifact,
                "registry_digest":"sha256:" + artifact,
                "signature_verified":True,
                "sbom_sha256":"d"*64,
                "provenance_sha256":"e"*64,
            }],
            "artifact_binding":{
                "rc_artifact_sha256":artifact,
                "qualified_artifact_sha256":artifact,
                "artifact_equal":True,
            },
            "closure":{
                "state":"PRE_CLOSURE",
                "closed_at":"2026-09-24T00:00:00Z",
                "release_manager":"owner",
                "receipt_sha256":"f"*64,
                "no_rebuild":True,
            },
        }

    def close(self, doc):
        doc["closure"]["state"]="V1_CLOSED"
        doc["final_tag"]={
            "name":"v1.0.0",
            "commit":doc["candidate"]["commit"],
            "signature_verified":True,
        }
        doc["binding_verification"]["candidate_final_equal"]=True

    def test_rc_binding_passes_before_final_tag(self):
        mod.validate_binding(self.doc)

    def test_rejects_rc_tag_on_different_commit(self):
        doc=copy.deepcopy(self.doc); doc["rc_tag"]["commit"]="4"*40
        with self.assertRaisesRegex(mod.ReceiptBindingError,"RC source"):
            mod.validate_binding(doc)

    def test_rejects_canary_identity_substituted_for_rc(self):
        doc=copy.deepcopy(self.doc)
        doc["candidate"]["commit"]=mod.CANARY_COMMIT
        doc["rc_tag"]["commit"]=mod.CANARY_COMMIT
        with self.assertRaisesRegex(mod.ReceiptBindingError,"cannot populate RC"):
            mod.validate_binding(doc)

    def test_rejects_unverified_rc_tag_signature(self):
        doc=copy.deepcopy(self.doc); doc["rc_tag"]["signature_verified"]=False
        with self.assertRaisesRegex(mod.ReceiptBindingError,"rc_tag signature"):
            mod.validate_binding(doc)

    def test_v1_closed_requires_final_tag(self):
        doc=copy.deepcopy(self.doc); doc["closure"]["state"]="V1_CLOSED"
        with self.assertRaisesRegex(mod.ReceiptBindingError,"requires an exact signed final tag"):
            mod.validate_binding(doc)

    def test_valid_signature_wrong_commit_is_rejected(self):
        doc=copy.deepcopy(self.doc); self.close(doc)
        doc["final_tag"]["commit"]="6"*40
        with self.assertRaisesRegex(mod.ReceiptBindingError,"RC source"):
            mod.validate_binding(doc)

    def test_rejects_unverified_final_tag_signature(self):
        doc=copy.deepcopy(self.doc); self.close(doc)
        doc["final_tag"]["signature_verified"]=False
        with self.assertRaisesRegex(mod.ReceiptBindingError,"final_tag signature"):
            mod.validate_binding(doc)

    def test_rejects_correct_source_wrong_artifact(self):
        doc=copy.deepcopy(self.doc)
        doc["artifact_binding"]["qualified_artifact_sha256"]="9"*64
        with self.assertRaisesRegex(mod.ReceiptBindingError,"qualified artifact"):
            mod.validate_binding(doc)

    def test_rejects_post_qualification_rebuild(self):
        doc=copy.deepcopy(self.doc)
        rebuilt="8"*64
        doc["artifact"][0]["sha256"]=rebuilt
        doc["artifact"][0]["registry_digest"]="sha256:"+rebuilt
        doc["artifact_binding"]["rc_artifact_sha256"]=rebuilt
        with self.assertRaisesRegex(mod.ReceiptBindingError,"qualified artifact"):
            mod.validate_binding(doc)

    def test_rejects_artifact_binding_not_present_in_artifacts(self):
        doc=copy.deepcopy(self.doc)
        missing="7"*64
        doc["artifact_binding"]["rc_artifact_sha256"]=missing
        doc["artifact_binding"]["qualified_artifact_sha256"]=missing
        with self.assertRaisesRegex(mod.ReceiptBindingError,"not present"):
            mod.validate_binding(doc)

    def test_final_tag_requires_closed_or_rollback_state(self):
        doc=copy.deepcopy(self.doc)
        doc["final_tag"]={"name":"v1.0.0","commit":doc["candidate"]["commit"],"signature_verified":True}
        doc["binding_verification"]["candidate_final_equal"]=True
        with self.assertRaisesRegex(mod.ReceiptBindingError,"PRE_CLOSURE"):
            mod.validate_binding(doc)

    def test_binding_flags_fail_closed(self):
        doc=copy.deepcopy(self.doc); doc["binding_verification"]["candidate_rc_equal"]=False
        with self.assertRaisesRegex(mod.ReceiptBindingError,"candidate_rc_equal"):
            mod.validate_binding(doc)

    def test_release_gates_have_distinct_identity_roles(self):
        gates=json.loads((ROOT/"V1_RELEASE_GATES.json").read_text(encoding="utf-8"))
        self.assertNotIn("candidate_commit",gates)
        self.assertNotIn("candidate_tree",gates)
        self.assertEqual(gates["r4_canary_provenance_sha"],mod.CANARY_COMMIT)
        self.assertEqual(gates["r4_canary_provenance_tree"],mod.CANARY_TREE)
        for key in ("convergence_source_sha","rc_source_sha","rc_tree_sha","rc_artifact_digest","qualified_artifact_digest","final_tag_target_sha"):
            self.assertIn(key,gates)


if __name__ == "__main__":
    unittest.main()
