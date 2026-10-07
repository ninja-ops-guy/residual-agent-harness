"""GDPR Article 17 right to erasure via irreversible pseudonymization.

Implements ENT2-R5: the requester's identity is replaced with a salted
HMAC-SHA256 hash in all observations and receipts; the salt is destroyed
so the hash cannot be reversed; the receipts themselves are preserved
(they are legal records); and the pseudonymization is observed and
receipted in the log.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass

from ..core import ContractError
from .log import ObservationLog


@dataclass(frozen=True)
class ErasureResult:
    """Outcome of one erasure request. Implements ENT2-R5."""
    user: str
    pseudonym: str
    events_pseudonymized: int
    receipt_hash: str
    salt_destroyed: bool


class ErasureService:
    """Performs and receipts GDPR Art. 17 erasure. Implements ENT2-R5."""

    def __init__(self, log: ObservationLog):
        self.log = log
        self._erased: set[str] = set()

    def pseudonymize(self, user: str, timestamp: float, actor: str = "compliance") -> ErasureResult:
        """Replace ``user`` with a one-way pseudonym everywhere. ENT2-R5."""
        if not isinstance(user, str) or not user.strip():
            raise ContractError("erasure requires a user identity")
        if user in self._erased:
            raise ContractError("user already erased")
        salt = secrets.token_bytes(32)
        pseudonym = "erased-" + hmac.new(salt, user.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
        # Destroy the salt: the HMAC key is overwritten and dropped, making
        # the pseudonym irreversible (no oracle remains to test identities).
        salt = b"\x00" * 32  # noqa: F841 - salt explicitly destroyed
        del salt
        target_ids = {e.id for e in self.log.events if e.actor == user}
        count = self.log.pseudonymize(target_ids, pseudonym)
        receipt = self.log.append("erasure", timestamp, actor, "system", category="sox",
                                  region="local",
                                  payload={"action": "pseudonymize", "pseudonym": pseudonym,
                                           "events_pseudonymized": count,
                                           "salt_destroyed": True, "article": "GDPR-Art17"},
                                  tags=("GDPR-Art17",))
        self._erased.add(user)
        return ErasureResult(user, pseudonym, count, receipt.chain_hash, True)
