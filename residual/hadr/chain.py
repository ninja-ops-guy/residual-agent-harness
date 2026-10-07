"""Hash-chained receipts for the HA/DR layer.

Implements ENT4-R4 (RPO=0: no verified receipt may be lost) by giving
the replication layer a minimal, verifiable receipt chain, and
ENT4-R6 by giving restore drills a chain whose integrity can be
re-verified after restore. This module is self-contained so the HA/DR
simulation does not depend on the station runtime.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from ..core import ContractError, canonical

HADR_CHAIN_SCHEMA = "residual.hadr.chain.v1"
GENESIS_HASH = "0" * 64


def _receipt_hash(sequence: int, task_id: str, payload: str, prev_hash: str) -> str:
    body = {
        "sequence": sequence,
        "task_id": task_id,
        "payload": payload,
        "prev_hash": prev_hash,
    }
    return hashlib.sha256((HADR_CHAIN_SCHEMA + "\n" + canonical(body)).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ChainReceipt:
    """A single hash-linked receipt. Implements ENT4-R4."""

    receipt_id: str
    sequence: int
    task_id: str
    payload: str
    prev_hash: str

    def verify(self) -> bool:
        """Recompute the content hash. Implements ENT4-R6."""
        return self.receipt_id == _receipt_hash(
            self.sequence, self.task_id, self.payload, self.prev_hash)


@dataclass
class ReceiptChain:
    """Append-only receipt chain with integrity verification.

    Implements ENT4-R4 (receipts are never lost once appended and
    acknowledged) and ENT4-R6 (``verify`` re-checks every link during
    restoration tests).
    """

    receipts: list[ChainReceipt] = field(default_factory=list)

    @property
    def head_hash(self) -> str:
        return self.receipts[-1].receipt_id if self.receipts else GENESIS_HASH

    @property
    def last_verified(self) -> ChainReceipt | None:
        """Last receipt on a verified chain; resume point for ENT4-R3."""
        if not self.verify():
            raise ContractError("receipt chain failed integrity verification")
        return self.receipts[-1] if self.receipts else None

    def append(self, task_id: str, payload: str) -> ChainReceipt:
        if not isinstance(task_id, str) or not task_id.strip():
            raise ContractError("task_id is required")
        if not isinstance(payload, str):
            raise ContractError("payload must be text")
        receipt = ChainReceipt(
            receipt_id=_receipt_hash(len(self.receipts), task_id, payload, self.head_hash),
            sequence=len(self.receipts),
            task_id=task_id,
            payload=payload,
            prev_hash=self.head_hash,
        )
        self.receipts.append(receipt)
        return receipt

    def clone(self) -> "ReceiptChain":
        return ReceiptChain(list(self.receipts))

    def verify(self) -> bool:
        """Verify every hash link. Implements ENT4-R6."""
        prev = GENESIS_HASH
        for index, receipt in enumerate(self.receipts):
            if receipt.sequence != index or receipt.prev_hash != prev or not receipt.verify():
                return False
            prev = receipt.receipt_id
        return True
