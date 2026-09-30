"""Authority tests for Station-admitted substrate qualification."""
from __future__ import annotations

import copy
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from residual.core import ContractError
from residual.substrates.admission import (
    AdmittedQualificationRegistry,
    QualificationAdmission,
    QualificationAdmissionBundle,
    SIGNATURE_DOMAIN,
)
from residual.substrates.qualification import (
    QualificationGate,
    SubstrateQualificationRecord,
    SubstrateQualificationRegistry,
    SubstrateQualificationTuple,
    inference_route_digest,
    provider_set_digest,
)


def make_tuple():
    return SubstrateQualificationTuple(
        substrate_name="openshell",
        substrate_version="0.1.1",
        substrate_source_identity="openshell@fixture",
        driver="docker",
        platform_class="linux-x86_64",
        environment_digest="a" * 64,
        agent_profile="openshell/direct",
        agent_identity="hermes@fixture",
        image_digest="1" * 64,
        requested_policy_digest="2" * 64,
        enforcement_state_digest="3" * 64,
        provider_set_digest=provider_set_digest({"provider-a": "b" * 64}),
        inference_route_digest=inference_route_digest("route-a"),
    )


def make_record(status="PASS", evidence_digest="4" * 64):
    return SubstrateQualificationRecord(
        qualification_tuple=make_tuple(),
        gates=(
            QualificationGate(
                gate_id="Q0",
                status=status,
                evidence_digest=evidence_digest,
            ),
        ),
        capabilities=("sandboxed_execution", "filesystem_policy"),
        evidence_root_digest="5" * 64,
    )


def public_bytes(private_key):
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )


class QualificationAdmissionTests(unittest.TestCase):
    def test_station_admission_exposes_capabilities_only_after_signature_verification(self):
        record = make_record()
        evidence = SubstrateQualificationRegistry()
        evidence.add(record)
        admitted = AdmittedQualificationRegistry(evidence)

        self.assertIsNone(
            admitted.get(record.qualification_tuple, record_digest=record.record_digest)
        )
        self.assertEqual(
            admitted.qualified_capabilities(
                record.qualification_tuple,
                record_digest=record.record_digest,
            ),
            frozenset(),
        )

        private = Ed25519PrivateKey.generate()
        admission = QualificationAdmission.issue(record, private, issued_at_ns=1)
        admitted.admit(
            record,
            admission,
            station_public_key=public_bytes(private),
        )

        selected = admitted.require(
            record.qualification_tuple,
            "sandboxed_execution",
            record_digest=record.record_digest,
        )
        self.assertEqual(selected.record_digest, record.record_digest)
        self.assertIn(
            "filesystem_policy",
            admitted.qualified_capabilities(
                record.qualification_tuple,
                record_digest=record.record_digest,
            ),
        )

    def test_wrong_station_key_is_rejected(self):
        record = make_record()
        private = Ed25519PrivateKey.generate()
        wrong = Ed25519PrivateKey.generate()
        admission = QualificationAdmission.issue(record, private, issued_at_ns=1)

        admitted = AdmittedQualificationRegistry()
        with self.assertRaisesRegex(ContractError, "signature is invalid"):
            admitted.admit(
                record,
                admission,
                station_public_key=public_bytes(wrong),
            )

    def test_signature_cannot_be_replayed_to_modified_record(self):
        record = make_record()
        private = Ed25519PrivateKey.generate()
        admission = QualificationAdmission.issue(record, private, issued_at_ns=1)
        modified = make_record(evidence_digest="6" * 64)

        self.assertNotEqual(record.record_digest, modified.record_digest)
        self.assertFalse(admission.verify(modified, public_bytes(private)))

    def test_factory_domain_signature_does_not_verify_as_substrate_admission(self):
        record = make_record()
        private = Ed25519PrivateKey.generate()
        valid = QualificationAdmission.issue(record, private, issued_at_ns=1)

        factory_domain = b"residual.factory.worker-receipt.v1\n"
        wrong_signature = private.sign(
            factory_domain + valid.admission_hash.encode("ascii")
        ).hex()
        wrong_domain = QualificationAdmission(
            record_digest=valid.record_digest,
            tuple_digest=valid.tuple_digest,
            station_key_id=valid.station_key_id,
            issued_at_ns=valid.issued_at_ns,
            station_signature=wrong_signature,
        )
        self.assertFalse(wrong_domain.verify(record, public_bytes(private)))
        self.assertNotEqual(factory_domain, SIGNATURE_DOMAIN)

    def test_non_pass_record_cannot_be_admitted(self):
        failed = make_record(status="FAIL")
        private = Ed25519PrivateKey.generate()
        with self.assertRaisesRegex(ContractError, "only PASS"):
            QualificationAdmission.issue(failed, private, issued_at_ns=1)

    def test_admission_bundle_rebuilds_authority_from_pinned_station_key(self):
        record = make_record()
        evidence = SubstrateQualificationRegistry()
        evidence.add(record)
        private = Ed25519PrivateKey.generate()
        public = public_bytes(private)
        admission = QualificationAdmission.issue(record, private, issued_at_ns=1)
        bundle = QualificationAdmissionBundle((admission,))

        replayed = QualificationAdmissionBundle.from_payload(bundle.payload())
        self.assertEqual(replayed.bundle_digest, bundle.bundle_digest)
        admitted = replayed.admitted_registry(
            evidence,
            trusted_public_keys={admission.station_key_id: public},
        )
        self.assertEqual(
            admitted.require(
                record.qualification_tuple,
                "sandboxed_execution",
                record_digest=record.record_digest,
            ).record_digest,
            record.record_digest,
        )

        with self.assertRaisesRegex(ContractError, "not in trusted Station key set"):
            replayed.admitted_registry(evidence, trusted_public_keys={})

    def test_admission_serialization_is_tamper_evident(self):
        record = make_record()
        private = Ed25519PrivateKey.generate()
        admission = QualificationAdmission.issue(record, private, issued_at_ns=1)
        replayed = QualificationAdmission.from_payload(admission.payload())
        self.assertEqual(replayed.admission_hash, admission.admission_hash)

        tampered = copy.deepcopy(admission.payload())
        tampered["issued_at_ns"] = 2
        with self.assertRaisesRegex(ContractError, "hash mismatch"):
            QualificationAdmission.from_payload(tampered)


if __name__ == "__main__":
    unittest.main()
