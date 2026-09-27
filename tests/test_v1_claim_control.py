import copy
import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "validate_v1_claim_control.py"
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
            "qualification_state":"EXPERIMENTAL_EVIDENCE",
            "release_state":"NOT_RELEASED",
            "support_state":"NOT_SUPPORTED",
            "public_claim":"experimental"
        }

    def test_experimental_evidence_does_not_confer_admission(self):
        mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[self.claim()]})

    def test_d3_qualification_requires_admission(self):
        c=self.claim(); c["qualification_state"]="D3_QUALIFIED"
        with self.assertRaisesRegex(mod.ClaimControlError,"cannot confer admission"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

    def test_support_requires_authorized_release(self):
        c=self.claim(); c.update(admission_state="ADMITTED_D3", qualification_state="D3_QUALIFIED", release_state="RELEASE_CANDIDATE", support_state="SUPPORTED")
        with self.assertRaisesRegex(mod.ClaimControlError,"before authorized release"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

    def test_release_requires_support(self):
        c=self.claim(); c.update(admission_state="ADMITTED_D3", qualification_state="RC_QUALIFIED", release_state="RELEASED")
        with self.assertRaisesRegex(mod.ClaimControlError,"must be supported"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

    def test_template_cannot_be_current_release_evidence(self):
        doc={"schema_version":"residual.v1-document-authority.v1","documents":[{"path":"x.md","authority_class":"REFERENCE_TEMPLATE","release_evidence_eligible":True}]}
        with self.assertRaisesRegex(mod.ClaimControlError,"CURRENT_NORMATIVE"):
            mod.validate_document_authority(doc)

if __name__ == "__main__":
    unittest.main()
