"""Cryptographic report signing with a pluggable Station signer.

Implements ENT2-R7: compliance reports are signed by the Station with
HMAC-SHA256 over the canonical report body; the signer is pluggable so
deployments can substitute an HSM/KMS-backed implementation.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..core import ContractError, canonical


@runtime_checkable
class Signer(Protocol):
    """Pluggable signing interface. Implements ENT2-R7."""

    @property
    def key_id(self) -> str: ...

    def sign(self, message: bytes) -> str: ...


class HmacSigner:
    """HMAC-SHA256 station key signer (default). Implements ENT2-R7."""

    def __init__(self, key: bytes, key_id: str = "station-hmac"):
        if not isinstance(key, bytes) or len(key) < 16:
            raise ContractError("station signing key must be at least 16 bytes")
        if not isinstance(key_id, str) or not key_id.strip():
            raise ContractError("signer requires a key id")
        self._key = key
        self._key_id = key_id

    @property
    def key_id(self) -> str:
        return self._key_id

    def sign(self, message: bytes) -> str:
        return hmac.new(self._key, message, hashlib.sha256).hexdigest()

    def verify(self, message: bytes, signature: str) -> bool:
        return hmac.compare_digest(self.sign(message), signature)


@dataclass(frozen=True)
class SignedReport:
    """A report body plus its Station signature. Implements ENT2-R7."""
    body: dict
    signature: str
    key_id: str
    algorithm: str = "HMAC-SHA256"

    def canonical_body(self) -> bytes:
        return canonical(self.body).encode("utf-8")

    def verify(self, signer: Signer) -> bool:
        """Verify the signature with any compatible signer."""
        expected = signer.sign(self.canonical_body())
        return hmac.compare_digest(expected, self.signature)


def sign_report(body: dict, signer: Signer) -> SignedReport:
    """Sign a canonical report body. Implements ENT2-R7."""
    canonical(body)  # strict validation
    return SignedReport(body, signer.sign(canonical(body).encode("utf-8")), signer.key_id)
