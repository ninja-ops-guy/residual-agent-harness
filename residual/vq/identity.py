"""VQ-R2: versioned verifier identity.

A verifier is identified by content hashes of its implementation,
configuration, policy, and (optionally) a proof artifact. Identity is
immutable; any change to any component yields a distinct revision.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional

from residual.core import ContractError


def hash_payload(value) -> str:
    """Deterministic SHA-256 content hash of a JSON-serializable payload."""
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class VerifierIdentity:
    """VQ-R2: versioned verifier identity.

    implementation_hash: content hash of verifier code/logic.
    configuration_hash:  content hash of runtime configuration.
    policy_hash:         content hash of the acceptance policy.
    proof_hash:          optional content hash of a proof artifact.
    """
    name: str
    implementation_hash: str
    configuration_hash: str
    policy_hash: str
    proof_hash: Optional[str] = None

    def __post_init__(self):
        if not self.name:
            raise ContractError("verifier identity name is required")
        for f in ("implementation_hash", "configuration_hash", "policy_hash"):
            v = getattr(self, f)
            if not v or not isinstance(v, str):
                raise ContractError(f"verifier identity {f} is required")

    @property
    def revision(self) -> str:
        """Single content hash binding all component hashes."""
        return hash_payload({
            "name": self.name,
            "implementation_hash": self.implementation_hash,
            "configuration_hash": self.configuration_hash,
            "policy_hash": self.policy_hash,
            "proof_hash": self.proof_hash,
        })

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "implementation_hash": self.implementation_hash,
            "configuration_hash": self.configuration_hash,
            "policy_hash": self.policy_hash,
            "proof_hash": self.proof_hash,
            "revision": self.revision,
        }

    @classmethod
    def build(cls, name: str, implementation, configuration,
              policy, proof=None) -> "VerifierIdentity":
        """Construct an identity by hashing each component payload."""
        return cls(
            name=name,
            implementation_hash=hash_payload(implementation),
            configuration_hash=hash_payload(configuration),
            policy_hash=hash_payload(policy),
            proof_hash=hash_payload(proof) if proof is not None else None,
        )
