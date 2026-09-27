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
            "claim_id": "X",
            "capability": "x",
            "documented_state": "DOCUMENTED",
            "implemented": True,
            "admission_state": "NOT_ADMITTED",
            "qualification_state": "NOT_QUALIFIED",
            "qualification_evidence": [],
            "release_state": "NOT_RELEASED",
            "support_state": "NOT_SUPPORTED",
            "public_claim": "experimental",
        }

    def evidence(self, *, head="1"*40, tree="2"*40, result="PASS"):
        return {
            "evidence_id": "receipt:synthetic",
            "source": "unit-test",
            "subject_head": head,
            "subject_tree": tree,
            "result": result,
            "evidence_sha256": "a"*64,
        }

    def test_checked_in_registries_validate(self):
        claims = json.loads((ROOT/"docs/v1/CLAIM_REGISTRY.json").read_text(encoding="utf-8"))
        docs = json.loads((ROOT/"docs/v1/DOCUMENT_AUTHORITY.json").read_text(encoding="utf-8"))
        mod.validate_claim_registry(claims)
        mod.validate_document_authority(docs)

    def test_missing_or_empty_claim_inventory_fails_closed(self):
        with self.assertRaisesRegex(mod.ClaimControlError, "claims must be a non-empty list"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1"})
        with self.assertRaisesRegex(mod.ClaimControlError, "claims must be a non-empty list"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[]})

    def test_missing_document_inventory_fails_closed(self):
        with self.assertRaisesRegex(mod.ClaimControlError, "documents must be a non-empty list"):
            mod.validate_document_authority({"schema_version":"residual.v1-document-authority.v1"})

    def test_not_qualified_rejects_fake_evidence_or_subject(self):
        c = self.claim()
        c["qualification_evidence"] = [self.evidence()]
        with self.assertRaisesRegex(mod.ClaimControlError, "NOT_QUALIFIED"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})
        c = self.claim()
        c["qualified_subject_head"] = "1"*40
        c["qualified_subject_tree"] = "2"*40
        with self.assertRaisesRegex(mod.ClaimControlError, "NOT_QUALIFIED"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

    def test_experimental_evidence_requires_structured_binding(self):
        c = self.claim()
        c["qualification_state"] = "EXPERIMENTAL_EVIDENCE"
        c["qualification_evidence"] = ["receipt:synthetic"]
        with self.assertRaisesRegex(mod.ClaimControlError, "must be an object"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})
        c["qualification_evidence"] = [self.evidence(result="FAIL")]
        mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

    def test_d3_qualification_requires_admission_exact_subject_and_pass(self):
        c = self.claim()
        c.update(
            qualification_state="D3_QUALIFIED",
            qualification_evidence=[self.evidence()],
            qualified_subject_head="1"*40,
            qualified_subject_tree="2"*40,
        )
        with self.assertRaisesRegex(mod.ClaimControlError, "cannot confer admission"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

        c["admission_state"] = "ADMITTED_D3"
        c["qualification_evidence"] = [self.evidence(tree="3"*40)]
        with self.assertRaisesRegex(mod.ClaimControlError, "bind the qualified subject"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

        c["qualification_evidence"] = [self.evidence(result="FAIL")]
        with self.assertRaisesRegex(mod.ClaimControlError, "requires only PASS"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

        c["qualification_evidence"] = [self.evidence()]
        mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

    def test_support_requires_authorized_release(self):
        c = self.claim()
        c.update(
            admission_state="ADMITTED_D3",
            qualification_state="RC_QUALIFIED",
            qualification_evidence=[self.evidence()],
            qualified_subject_head="1"*40,
            qualified_subject_tree="2"*40,
            release_state="RELEASE_CANDIDATE",
            support_state="SUPPORTED",
        )
        with self.assertRaisesRegex(mod.ClaimControlError, "before authorized release"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

    def test_released_state_requires_external_authorization_binding(self):
        c = self.claim()
        c.update(
            admission_state="ADMITTED_D3",
            qualification_state="RC_QUALIFIED",
            qualification_evidence=[self.evidence()],
            qualified_subject_head="1"*40,
            qualified_subject_tree="2"*40,
            release_state="RELEASED",
            support_state="SUPPORTED",
        )
        with self.assertRaisesRegex(mod.ClaimControlError, "release_authorization"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

        c["release_authorization"] = {
            "release": "v1.0.0",
            "identity": "owner-authorization",
            "source_head": "3"*40,
            "source_tree": "2"*40,
            "artifact_set_sha256": "b"*64,
            "evidence_sha256": "c"*64,
        }
        with self.assertRaisesRegex(mod.ClaimControlError, "RC-qualified subject"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

        c["release_authorization"]["source_head"] = "1"*40
        mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

    def test_release_authorization_rejected_before_release(self):
        c = self.claim()
        c["release_authorization"] = {
            "release": "v1.0.0",
            "identity": "owner-authorization",
            "source_head": "1"*40,
            "source_tree": "2"*40,
            "artifact_set_sha256": "b"*64,
            "evidence_sha256": "c"*64,
        }
        with self.assertRaisesRegex(mod.ClaimControlError, "only for RELEASED"):
            mod.validate_claim_registry({"schema_version":"residual.v1-claim-registry.v1","claims":[c]})

    def test_template_cannot_be_current_release_evidence(self):
        doc = {
            "schema_version":"residual.v1-document-authority.v1",
            "documents":[{"path":"x.md","authority_class":"REFERENCE_TEMPLATE","release_evidence_eligible":True}],
        }
        with self.assertRaisesRegex(mod.ClaimControlError, "CURRENT_NORMATIVE"):
            mod.validate_document_authority(doc)


if __name__ == "__main__":
    unittest.main()
