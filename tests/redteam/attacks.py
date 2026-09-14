"""Shared helpers for the redteam corpus (track K, K-R2)."""
from __future__ import annotations

import hashlib

from residual.core import digest
from residual.receipts import StationReceipt
from residual.verifier import CheckResult

ZERO_HASH = hashlib.sha256(b"").hexdigest()
ATTACK_VERIFIER = "redteam:attack"
ATTACK_REVISION = hashlib.sha256(b"redteam-corpus-v1").hexdigest()


def attack_receipt(attack_id: str, description: str) -> StationReceipt:
    """A FAIL-verdict receipt recording that an attack was attempted and
    blocked/observed. The receipt system supports FAIL verdicts; this is
    the audit trail required by K-R2."""
    return StationReceipt(
        task_id=attack_id,
        cache_key=hashlib.sha256(f"attack:{attack_id}".encode()).hexdigest(),
        value_hash=digest({"attack": attack_id, "description": description}),
        verifier_name=ATTACK_VERIFIER,
        verifier_revision=ATTACK_REVISION,
        verdict=CheckResult.FAIL,
    )
