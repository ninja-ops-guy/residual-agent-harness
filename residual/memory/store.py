"""Track 4: Epistemic Memory — cross-session receipt and solution indexing.

Content-addressed by goal description hash. Written only at run close.
Validated before retrieval. Derived index, not primary store.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..core import ContractError, canonical, digest, strict_json
from ..receipts import StationReceipt, hash_id
from observation_layer.core import freeze


@dataclass(frozen=True)
class MemoryEntry:
    """One indexed memory. Receipt hash must verify before retrieval."""
    key: str                    # full SHA-256 goal hash (display may abbreviate)
    goal_description: str
    receipt_hash: str
    artifact_payload: dict[str, Any]
    verifier_revision: str
    recorded_at_ns: int


class EpistemicMemoryStore:
    """Content-addressed memory store.

    Keys are full SHA-256(goal_description). Integrity checks do not grant
    acceptance; retrieve_verified additionally requires a live host verifier.
    The lifecycle adapter writes only at run close.
    """

    def __init__(self, memory_dir: str):
        if not memory_dir:
            raise ContractError("memory directory is required")
        self._dir = memory_dir
        os.makedirs(memory_dir, exist_ok=True)

    @staticmethod
    def _key(goal_description: str) -> str:
        return hashlib.sha256(goal_description.encode()).hexdigest()

    def index(self, goal_description: str, receipt_hash: str,
              artifact_payload: dict[str, Any], verifier_revision: str) -> MemoryEntry:
        """Index a validated result. Called only at run close."""
        if not goal_description.strip():
            raise ContractError("goal description is required")
        hash_id(receipt_hash)
        key = self._key(goal_description)
        entry = MemoryEntry(
            key=key,
            goal_description=goal_description,
            receipt_hash=receipt_hash,
            artifact_payload=freeze(artifact_payload),
            verifier_revision=verifier_revision,
            recorded_at_ns=time.time_ns(),
        )
        path = os.path.join(self._dir, f"{key}.json")
        with open(path, "w") as f:
            data = {
                "schema_version": "residual.memory.v1",
                "key": key,
                "goal_description": goal_description,
                "receipt_hash": receipt_hash,
                "artifact_payload": artifact_payload,
                "verifier_revision": verifier_revision,
                "recorded_at_ns": entry.recorded_at_ns,
            }
            json.dump({**data, "entry_hash": digest(data)}, f, indent=2, sort_keys=True)
        return entry

    def retrieve(self, goal_description: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry. Validates receipt hash on load."""
        key = self._key(goal_description)
        path = os.path.join(self._dir, f"{key}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                data = strict_json(f.read())
            entry_hash = data.pop("entry_hash")
            if (digest(data) != entry_hash or data["schema_version"] != "residual.memory.v1"
                    or data["key"] != key or data["goal_description"] != goal_description):
                return None
            hash_id(data["receipt_hash"])
        except (ValueError, KeyError, TypeError, OSError):
            return None
        entry = MemoryEntry(
            key=data["key"],
            goal_description=data["goal_description"],
            receipt_hash=data["receipt_hash"],
            artifact_payload=freeze(data["artifact_payload"]),
            verifier_revision=data["verifier_revision"],
            recorded_at_ns=data["recorded_at_ns"],
        )
        return entry

    def retrieve_verified(self, goal_description: str, *, verifier_revision: str, verify) -> Optional[MemoryEntry]:
        """A derived index cannot replace live, context-aware host verification."""
        entry = self.retrieve(goal_description)
        if entry is None or entry.verifier_revision != verifier_revision:
            return None
        try:
            receipt = StationReceipt.from_dict(strict_json(canonical(entry.artifact_payload["receipt"])))
            value = strict_json(canonical(entry.artifact_payload["value"]))
            if (receipt.receipt_hash != entry.receipt_hash or receipt.verifier_revision != verifier_revision
                    or receipt.verdict.value != "pass" or receipt.value_hash != digest(value)):
                return None
            # Callback must validate context/evidence and the candidate, not just its hash.
            if verify(receipt, value) is not True:
                return None
        except Exception:
            return None
        return entry

    def validate_receipt(self, entry: MemoryEntry, expected_receipt_hash: str) -> bool:
        """Compare identity only. This does not establish candidate correctness."""
        return entry.receipt_hash == expected_receipt_hash
