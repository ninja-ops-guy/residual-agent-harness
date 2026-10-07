"""Track E: verified retrieval with provenance binding.

Requirement IDs (RFC 2119):
- E-R4: A retrieved artifact MUST be returned only when its provenance chain
  verifies end-to-end: entry integrity, receipt_hash binding, value binding
  (digest(value) == receipt.value_hash), verifier revision match, and a live
  host verification callback.
- E-R5: Retrieval MUST fail closed: any mismatch, parse error, or verifier
  exception yields None, never a partial artifact.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from ..core import canonical, digest, strict_json
from ..memory import EpistemicMemoryStore, MemoryEntry
from ..receipts import StationReceipt


@dataclass(frozen=True)
class VerifiedArtifact:
    """A memory artifact whose provenance chain verified end-to-end."""

    entry: MemoryEntry
    receipt: StationReceipt
    value: Any
    artifact_hash: str       # digest(value) — MUST equal receipt.value_hash
    receipt_hash: str        # MUST equal entry.receipt_hash


def retrieve_bound(store: EpistemicMemoryStore, goal_description: str, *,
                   verifier_revision: str,
                   verify: Callable[[StationReceipt, Any], bool]) -> Optional[VerifiedArtifact]:
    """E-R4/E-R5: provenance-bound retrieval. Fails closed on any mismatch."""
    entry = store.retrieve_verified(goal_description,
                                    verifier_revision=verifier_revision, verify=verify)
    if entry is None:
        return None
    try:
        receipt = StationReceipt.from_dict(strict_json(canonical(entry.artifact_payload["receipt"])))
        value = strict_json(canonical(entry.artifact_payload["value"]))
        artifact_hash = digest(value)
        # Provenance binding: artifact hash MUST match the receipt, and the
        # receipt hash MUST match the indexed entry.
        if (artifact_hash != receipt.value_hash
                or receipt.receipt_hash != entry.receipt_hash
                or receipt.verdict.value != "pass"
                or receipt.verifier_revision != verifier_revision):
            return None
    except Exception:
        return None
    return VerifiedArtifact(entry=entry, receipt=receipt, value=value,
                            artifact_hash=artifact_hash, receipt_hash=entry.receipt_hash)
