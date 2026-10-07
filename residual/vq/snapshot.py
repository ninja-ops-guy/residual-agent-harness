"""VQ-R8: receipts carry the verifier quality snapshot used at acceptance.

A VerifierQualitySnapshot binds the verifier identity revision to the
profile metrics in force when acceptance happened, so any receipt can be
audited against the exact quality state that authorized it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .identity import VerifierIdentity, hash_payload
from .profile import VerifierQualityProfile


@dataclass(frozen=True)
class VerifierQualitySnapshot:
    """Immutable quality state of a verifier at acceptance time."""
    identity: VerifierIdentity
    profile: VerifierQualityProfile

    @property
    def snapshot_hash(self) -> str:
        return hash_payload({
            "identity_revision": self.identity.revision,
            "profile": self.profile.to_dict(),
        })

    def to_dict(self) -> dict:
        return {
            "identity": self.identity.to_dict(),
            "profile": self.profile.to_dict(),
            "snapshot_hash": self.snapshot_hash,
        }


def attach_snapshot_to_receipt(receipt_payload: dict,
                               snapshot: VerifierQualitySnapshot) -> dict:
    """Return a new receipt payload carrying the quality snapshot (VQ-R8).

    Never mutates the input. The snapshot is recorded under
    ``verifier_quality`` with identity revision and snapshot hash so the
    acceptance-time quality state is hash-bound into the receipt.
    """
    out = dict(receipt_payload)
    out["verifier_quality"] = {
        "verifier_revision": snapshot.identity.revision,
        "snapshot_hash": snapshot.snapshot_hash,
        "precision": snapshot.profile.precision.to_dict(),
        "recall": snapshot.profile.recall.to_dict(),
        "false_accept": snapshot.profile.false_accept.to_dict(),
        "sample_count": snapshot.profile.sample_count,
    }
    return out
