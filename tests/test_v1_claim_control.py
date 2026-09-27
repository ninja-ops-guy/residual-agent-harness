import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "validate_v1_claim_control.py"
SPEC = importlib.util.spec_from_file_location("validate_v1_claim_control", MODULE_PATH)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

class V1ClaimControlTests(unittest.TestCase):
    def claim(self):
        return {
            "claim_id":"X",
            "capability":"x",
            "documented_state":"DOCUMENTED",
            "implemented":True,
            "admission_state":"NOT_ADMITTED",
            "qualification_state":"NOT_QUALIFIED",
            "qualification_evidence":[],
            "release_state":"NOT_RELEASED",
            "support_state":"NOT_SUPPORTED",
            "public_claim":"experimental"
        }

    def test_checked_in_registries_validate(self):
        claims=json.loads((ROOT/"docs/v1/CLAIM_REGISTRY.json").read_text(encoding="utf-8"))
        docs=json.loads((ROOT/"docs/v1/DOCUMENT_AUTHORITY.json").read_text(encoding="utf-8"))
        mod.validate_claim_registry(claims)
        mod.validate_document_authority(docs)

    def test_missing_or_empty_claim_inventory_fails_closed(self):
        with self.assertRaisesRegex(mod.ClaimControlError,"claims must be a non-empty list"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1"})
        with self.assertRaisesRegex(mod.ClaimControlError,"claims must be a non-empty list"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[]})

    def test_missing_document_inventory_fails_closed(self):
        with self.assertRaisesRegex(mod.ClaimControlError,"documents must be a non-empty list"):
            mod.validate_document_authority({"schema_version":"residual.v1-document-authority.v1"})

    def test_experimental_evidence_requires_binding(self):
        c=self.claim(); c["qualification_state"]="EXPERIMENTAL_EVIDENCE"
        with self.assertRaisesRegex(mod.ClaimControlError,"qualification_evidence"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})
        c["qualification_evidence"]=["receipt:synthetic"]
        mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

    def test_d3_qualification_requires_admission_and_evidence(self):
        c=self.claim(); c["qualification_state"]="D3_QUALIFIED"; c["qualification_evidence"]=["receipt:synthetic"]
        with self.assertRaisesRegex(mod.ClaimControlError,"cannot confer admission"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

    def test_support_requires_authorized_release(self):
        c=self.claim(); c.update(admission_state="ADMITTED_D3", qualification_state="D3_QUALIFIED",
                                 qualification_evidence=["receipt:synthetic"], release_state="RELEASE_CANDIDATE",
                                 support_state="SUPPORTED")
        with self.assertRaisesRegex(mod.ClaimControlError,"before authorized release"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

    def test_released_state_requires_authorization_evidence(self):
        c=self.claim(); c.update(admission_state="ADMITTED_D3", qualification_state="RC_QUALIFIED",
                                 qualification_evidence=["receipt:synthetic"], release_state="RELEASED",
                                 support_state="SUPPORTED")
        with self.assertRaisesRegex(mod.ClaimControlError,"release_authorization"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

    def test_template_cannot_be_current_release_evidence(self):
        doc={"schema_version":"residual.v1-document-authority.v1","documents":[{"path":"x.md","authority_class":"REFERENCE_TEMPLATE","release_evidence_eligible":True}]}
        with self.assertRaisesRegex(mod.ClaimControlError,"CURRENT_NORMATIVE"):
            mod.validate_document_authority(doc)

if __name__ == "__main__":
    unittest.main()
