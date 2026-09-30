"""R1 lifecycle tests for substrate qualification authority."""
from __future__ import annotations

import copy
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from residual.core import ContractError
from residual.substrates.admission import QualificationAdmission, QualificationAdmissionBundle
from residual.substrates.authority_lifecycle import (
    QualificationAuthorityLifecycleBundle,
    QualificationAuthorityPolicy,
    QualificationRevocation,
    StationKeySuccessor,
    StationTrustStore,
    build_lifecycle_admitted_registry,
)
from residual.substrates.qualification import (
    QualificationGate,
    SubstrateQualificationRecord,
    SubstrateQualificationRegistry,
    SubstrateQualificationTuple,
    inference_route_digest,
    provider_set_digest,
)


def raw_public(private):
    return private.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )


def make_record():
    qtuple = SubstrateQualificationTuple(
        substrate_name="openshell",
        substrate_version="0.1.2",
        substrate_source_identity="openshell:v0.1.2@fixture",
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
    return SubstrateQualificationRecord(
        qualification_tuple=qtuple,
        gates=(
            QualificationGate(
                gate_id="Q0",
                status="PASS",
                evidence_digest="4" * 64,
            ),
        ),
        capabilities=("sandboxed_execution", "filesystem_policy"),
        evidence_root_digest="5" * 64,
    )


def evidence_registry(record):
    registry = SubstrateQualificationRegistry()
    registry.add(record)
    return registry


class FreshnessTests(unittest.TestCase):
    def test_stale_and_future_admissions_are_not_effective(self):
        record = make_record()
        key = Ed25519PrivateKey.generate()
        admissions = QualificationAdmissionBundle((
            QualificationAdmission.issue(record, key, issued_at_ns=100),
        ))
        lifecycle = QualificationAuthorityLifecycleBundle()

        fresh = build_lifecycle_admitted_registry(
            evidence_registry(record),
            admissions,
            lifecycle,
            root_public_keys=(raw_public(key),),
            policy=QualificationAuthorityPolicy(
                now_ns=150,
                max_admission_age_ns=100,
            ),
        )
        self.assertIsNotNone(
            fresh.get(record.qualification_tuple, record_digest=record.record_digest)
        )

        stale = build_lifecycle_admitted_registry(
            evidence_registry(record),
            admissions,
            lifecycle,
            root_public_keys=(raw_public(key),),
            policy=QualificationAuthorityPolicy(
                now_ns=1000,
                max_admission_age_ns=100,
            ),
        )
        self.assertIsNone(
            stale.get(record.qualification_tuple, record_digest=record.record_digest)
        )

        future = build_lifecycle_admitted_registry(
            evidence_registry(record),
            admissions,
            lifecycle,
            root_public_keys=(raw_public(key),),
            policy=QualificationAuthorityPolicy(
                now_ns=50,
                max_admission_age_ns=1000,
                max_future_skew_ns=10,
            ),
        )
        self.assertIsNone(
            future.get(record.qualification_tuple, record_digest=record.record_digest)
        )

    def test_minimum_issue_time_fences_old_generation(self):
        record = make_record()
        key = Ed25519PrivateKey.generate()
        admission = QualificationAdmission.issue(record, key, issued_at_ns=100)
        admitted = build_lifecycle_admitted_registry(
            evidence_registry(record),
            QualificationAdmissionBundle((admission,)),
            QualificationAuthorityLifecycleBundle(),
            root_public_keys=(raw_public(key),),
            policy=QualificationAuthorityPolicy(
                now_ns=150,
                max_admission_age_ns=1000,
                min_issued_at_ns=101,
            ),
        )
        self.assertIsNone(
            admitted.get(record.qualification_tuple, record_digest=record.record_digest)
        )


class RevocationTests(unittest.TestCase):
    def test_effective_revocation_removes_admission(self):
        record = make_record()
        key = Ed25519PrivateKey.generate()
        admission = QualificationAdmission.issue(record, key, issued_at_ns=100)
        revocation = QualificationRevocation.issue(
            admission,
            key,
            effective_at_ns=120,
            reason_code="qualification_superseded",
        )

        before = build_lifecycle_admitted_registry(
            evidence_registry(record),
            QualificationAdmissionBundle((admission,)),
            QualificationAuthorityLifecycleBundle(revocations=(revocation,)),
            root_public_keys=(raw_public(key),),
            policy=QualificationAuthorityPolicy(
                now_ns=110,
                max_admission_age_ns=1000,
            ),
        )
        self.assertIsNotNone(
            before.get(record.qualification_tuple, record_digest=record.record_digest)
        )

        after = build_lifecycle_admitted_registry(
            evidence_registry(record),
            QualificationAdmissionBundle((admission,)),
            QualificationAuthorityLifecycleBundle(revocations=(revocation,)),
            root_public_keys=(raw_public(key),),
            policy=QualificationAuthorityPolicy(
                now_ns=130,
                max_admission_age_ns=1000,
            ),
        )
        self.assertIsNone(
            after.get(record.qualification_tuple, record_digest=record.record_digest)
        )

    def test_untrusted_revocation_is_rejected(self):
        record = make_record()
        trusted = Ed25519PrivateKey.generate()
        attacker = Ed25519PrivateKey.generate()
        admission = QualificationAdmission.issue(record, trusted, issued_at_ns=100)
        revocation = QualificationRevocation.issue(
            admission,
            attacker,
            effective_at_ns=120,
            reason_code="fake",
        )
        with self.assertRaisesRegex(ContractError, "not signed by active trusted key"):
            build_lifecycle_admitted_registry(
                evidence_registry(record),
                QualificationAdmissionBundle((admission,)),
                QualificationAuthorityLifecycleBundle(revocations=(revocation,)),
                root_public_keys=(raw_public(trusted),),
                policy=QualificationAuthorityPolicy(
                    now_ns=130,
                    max_admission_age_ns=1000,
                ),
            )

    def test_revocation_payload_is_tamper_evident(self):
        record = make_record()
        key = Ed25519PrivateKey.generate()
        admission = QualificationAdmission.issue(record, key, issued_at_ns=100)
        revocation = QualificationRevocation.issue(
            admission,
            key,
            effective_at_ns=120,
            reason_code="superseded",
        )
        replay = QualificationRevocation.from_payload(revocation.payload())
        self.assertEqual(replay.revocation_hash, revocation.revocation_hash)
        tampered = copy.deepcopy(revocation.payload())
        tampered["reason_code"] = "different"
        with self.assertRaisesRegex(ContractError, "hash mismatch"):
            QualificationRevocation.from_payload(tampered)


class KeyRotationTests(unittest.TestCase):
    def test_dual_signed_successor_rotates_issuance_authority(self):
        record = make_record()
        old = Ed25519PrivateKey.generate()
        new = Ed25519PrivateKey.generate()
        transition = StationKeySuccessor.issue(
            old,
            new,
            activates_at_ns=200,
            predecessor_retire_at_ns=220,
        )
        trust = StationTrustStore(
            (raw_public(old),),
            transitions=(transition,),
        )
        old_id = transition.predecessor_key_id
        new_id = transition.successor_key_id

        self.assertIn(old_id, trust.active_issuer_keys(199))
        self.assertNotIn(new_id, trust.active_issuer_keys(199))
        self.assertIn(old_id, trust.active_issuer_keys(210))
        self.assertIn(new_id, trust.active_issuer_keys(210))
        self.assertNotIn(old_id, trust.active_issuer_keys(220))
        self.assertIn(new_id, trust.active_issuer_keys(220))

        old_valid = QualificationAdmission.issue(record, old, issued_at_ns=210)
        old_late = QualificationAdmission.issue(record, old, issued_at_ns=230)
        new_valid = QualificationAdmission.issue(record, new, issued_at_ns=230)

        lifecycle = QualificationAuthorityLifecycleBundle(transitions=(transition,))
        admitted = build_lifecycle_admitted_registry(
            evidence_registry(record),
            QualificationAdmissionBundle((old_valid, new_valid)),
            lifecycle,
            root_public_keys=(raw_public(old),),
            policy=QualificationAuthorityPolicy(
                now_ns=240,
                max_admission_age_ns=1000,
            ),
        )
        # Multiple admitted PASS records for one record collapse to the same
        # record authority rather than creating distinct capability identities.
        self.assertIsNotNone(
            admitted.get(record.qualification_tuple, record_digest=record.record_digest)
        )

        only_late_old = build_lifecycle_admitted_registry(
            evidence_registry(record),
            QualificationAdmissionBundle((old_late,)),
            lifecycle,
            root_public_keys=(raw_public(old),),
            policy=QualificationAuthorityPolicy(
                now_ns=240,
                max_admission_age_ns=1000,
            ),
        )
        self.assertIsNone(
            only_late_old.get(
                record.qualification_tuple,
                record_digest=record.record_digest,
            )
        )

    def test_successor_requires_both_signatures(self):
        old = Ed25519PrivateKey.generate()
        new = Ed25519PrivateKey.generate()
        transition = StationKeySuccessor.issue(
            old,
            new,
            activates_at_ns=200,
            predecessor_retire_at_ns=220,
        )
        tampered = copy.deepcopy(transition.payload())
        tampered["successor_signature"] = "00" * 64
        bad = StationKeySuccessor.from_payload(tampered)
        with self.assertRaisesRegex(ContractError, "signature is invalid"):
            StationTrustStore(
                (raw_public(old),),
                transitions=(bad,),
            ).active_issuer_keys(210)

    def test_multiple_successors_from_one_predecessor_are_rejected(self):
        old = Ed25519PrivateKey.generate()
        first = Ed25519PrivateKey.generate()
        second = Ed25519PrivateKey.generate()
        t1 = StationKeySuccessor.issue(
            old, first, activates_at_ns=200, predecessor_retire_at_ns=240,
        )
        t2 = StationKeySuccessor.issue(
            old, second, activates_at_ns=210, predecessor_retire_at_ns=240,
        )
        with self.assertRaisesRegex(ContractError, "ambiguous Station-key successor"):
            StationTrustStore((raw_public(old),), transitions=(t1, t2))

    def test_unrooted_successor_chain_is_rejected(self):
        unrelated = Ed25519PrivateKey.generate()
        old = Ed25519PrivateKey.generate()
        new = Ed25519PrivateKey.generate()
        transition = StationKeySuccessor.issue(
            old,
            new,
            activates_at_ns=200,
            predecessor_retire_at_ns=220,
        )
        with self.assertRaisesRegex(ContractError, "not rooted"):
            StationTrustStore(
                (raw_public(unrelated),),
                transitions=(transition,),
            ).active_issuer_keys(210)

    def test_distrusted_root_invalidates_descendant_chain(self):
        old = Ed25519PrivateKey.generate()
        new = Ed25519PrivateKey.generate()
        transition = StationKeySuccessor.issue(
            old,
            new,
            activates_at_ns=200,
            predecessor_retire_at_ns=220,
        )
        with self.assertRaisesRegex(ContractError, "distrusted key"):
            StationTrustStore(
                (raw_public(old),),
                transitions=(transition,),
                distrusted_key_ids=(transition.predecessor_key_id,),
            ).active_issuer_keys(210)

    def test_transition_payload_round_trip_and_tamper_detection(self):
        old = Ed25519PrivateKey.generate()
        new = Ed25519PrivateKey.generate()
        transition = StationKeySuccessor.issue(
            old,
            new,
            activates_at_ns=200,
            predecessor_retire_at_ns=220,
        )
        replay = StationKeySuccessor.from_payload(transition.payload())
        self.assertEqual(replay.transition_hash, transition.transition_hash)
        tampered = copy.deepcopy(transition.payload())
        tampered["activates_at_ns"] = 201
        with self.assertRaisesRegex(ContractError, "hash mismatch"):
            StationKeySuccessor.from_payload(tampered)


class LifecycleBundleTests(unittest.TestCase):
    def test_bundle_round_trip_is_content_addressed(self):
        old = Ed25519PrivateKey.generate()
        new = Ed25519PrivateKey.generate()
        record = make_record()
        admission = QualificationAdmission.issue(record, old, issued_at_ns=100)
        transition = StationKeySuccessor.issue(
            old,
            new,
            activates_at_ns=200,
            predecessor_retire_at_ns=220,
        )
        revocation = QualificationRevocation.issue(
            admission,
            old,
            effective_at_ns=150,
            reason_code="superseded",
        )
        bundle = QualificationAuthorityLifecycleBundle(
            transitions=(transition,),
            revocations=(revocation,),
        )
        replay = QualificationAuthorityLifecycleBundle.from_payload(bundle.payload())
        self.assertEqual(replay.bundle_digest, bundle.bundle_digest)


if __name__ == "__main__":
    unittest.main()
