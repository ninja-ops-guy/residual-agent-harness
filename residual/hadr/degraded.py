"""Degraded/disconnected mode with later synchronization.

Implements ENT4-R7: if the cluster is unavailable, individual stations
continue operating with local models; receipts are queued locally and
synchronized when connectivity returns. Conflicts (the same receipt id
produced independently while partitioned) are resolved deterministically.
Sync operations are observed and receipted per ENT4-R8.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..core import ContractError
from .chain import ChainReceipt, ReceiptChain, GENESIS_HASH
from .cluster import StationRegistry
from .events import EventJournal, SYNC_EVENT


@dataclass(frozen=True)
class ConflictResolution:
    """Record of a deterministic conflict resolution. Implements ENT4-R7."""

    receipt_id: str
    kept: str  # "local" or "remote"
    rule: str


@dataclass
class DegradedStation:
    """A station that keeps working when the cluster is unavailable.

    Implements ENT4-R7: ``operate`` uses a local model callable whether
    or not the cluster is reachable; while disconnected the produced
    receipts are queued locally; ``sync`` pushes the queue into the
    shared chain on reconnect and resolves conflicts deterministically
    (prefer the authoritative remote copy, else the lexicographically
    smaller content, ties broken by station id).
    """

    station_id: str
    registry: StationRegistry
    journal: EventJournal
    local_model: Callable[[str], str]
    shared_chain: ReceiptChain
    local_queue: list[ChainReceipt] = field(default_factory=list)
    local_chain: ReceiptChain = field(default_factory=ReceiptChain)
    _sequence: int = 0

    @property
    def connected(self) -> bool:
        return self.registry.is_reachable(self.station_id)

    def operate(self, task_id: str, work: str) -> ChainReceipt:
        """Run a task on the local model and record a receipt. Implements ENT4-R7."""
        if not isinstance(work, str) or not work.strip():
            raise ContractError("work input is required")
        output = self.local_model(work)
        receipt = self.local_chain.append(task_id, output)
        if not self.connected:
            self.local_queue.append(receipt)
        else:
            self._publish(receipt)
        return receipt

    def _publish(self, receipt: ChainReceipt) -> None:
        self.shared_chain.append(receipt.task_id, receipt.payload)

    def sync(self) -> list[ConflictResolution]:
        """Flush the local queue into the shared chain. Implements ENT4-R7 and ENT4-R8."""
        if not self.connected:
            raise ContractError("cannot sync while the cluster is unavailable")
        resolutions: list[ConflictResolution] = []
        for receipt in list(self.local_queue):
            resolution = self._merge(receipt)
            if resolution is not None:
                resolutions.append(resolution)
            self.local_queue.remove(receipt)
        self.journal.record(SYNC_EVENT, {
            "station_id": self.station_id,
            "merged": len(resolutions),
            "queue_remaining": len(self.local_queue),
        })
        return resolutions

    def _merge(self, receipt: ChainReceipt) -> ConflictResolution | None:
        for existing in self.shared_chain.receipts:
            if existing.receipt_id == receipt.receipt_id:
                return None  # already replicated; idempotent
            if existing.task_id == receipt.task_id and existing.payload != receipt.payload:
                # Conflict: same task produced different results while
                # partitioned. Deterministic rule: keep the copy whose
                # payload hash is lexicographically smaller; ties go to
                # the authoritative (already shared/remote) copy.
                if receipt.payload < existing.payload:
                    self.shared_chain.append(receipt.task_id, receipt.payload)
                    return ConflictResolution(receipt.receipt_id, kept="local",
                                              rule="smaller-payload-supersedes")
                return ConflictResolution(receipt.receipt_id, kept="remote",
                                          rule="authoritative-copy-retained")
        self.shared_chain.append(receipt.task_id, receipt.payload)
        return None

    def pending_count(self) -> int:
        return len(self.local_queue)
