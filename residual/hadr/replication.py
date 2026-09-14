"""Receipt chain replication across regions.

Implements ENT4-R2: the receipt chain is replicated in real time —
synchronously within the primary region, asynchronously to secondary
regions — with lag tracking and an assertion/alert when a receipt in
the primary region has not reached at least one secondary within 30
seconds. Implements ENT4-R4 (RPO=0): a receipt is only acknowledged
once it is durably replicated per policy (synchronous copies in the
primary region); if the policy cannot be satisfied the receipt is
refused rather than acknowledged and lost.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core import ContractError
from .chain import ChainReceipt, ReceiptChain
from .clock import Clock
from .events import EventJournal, LAG_ALERT_EVENT

MAX_SECONDARY_LAG_SECONDS = 30.0


@dataclass(frozen=True)
class ReplicaMessage:
    """A receipt in flight to a replica. Implements ENT4-R2."""

    origin: str
    target: str
    receipt: ChainReceipt
    enqueued_at: float
    deliver_at: float


@dataclass
class SimulatedTransport:
    """Deterministic in-process transport with per-region latency.

    Implements ENT4-R2 by making asynchronous secondary replication
    deliver only after the injected clock has advanced past the
    configured latency, so the 30 second lag budget is testable.
    """

    clock: Clock
    latency_seconds: dict[str, float] = field(default_factory=dict)
    pending: list[ReplicaMessage] = field(default_factory=list)

    def latency_for(self, region: str) -> float:
        return float(self.latency_seconds.get(region, 0.0))

    def send(self, origin: str, target_region: str, receipt: ChainReceipt) -> ReplicaMessage:
        now = self.clock.now()
        message = ReplicaMessage(
            origin=origin,
            target=target_region,
            receipt=receipt,
            enqueued_at=now,
            deliver_at=now + self.latency_for(target_region),
        )
        self.pending.append(message)
        return message

    def flush_due(self) -> list[ReplicaMessage]:
        """Deliver every message whose latency has elapsed. Implements ENT4-R2."""
        now = self.clock.now()
        due = [m for m in self.pending if m.deliver_at <= now]
        self.pending = [m for m in self.pending if m.deliver_at > now]
        return due

    def pending_for(self, region: str) -> list[ReplicaMessage]:
        return [m for m in self.pending if m.target == region]


@dataclass
class ReplicaNode:
    """A replication peer holding its own copy of the chain. Implements ENT4-R2."""

    node_id: str
    region: str
    is_primary_region: bool = False
    available: bool = True
    chain: ReceiptChain = field(default_factory=ReceiptChain)

    def install(self, receipt: ChainReceipt) -> None:
        if not self.available:
            raise ContractError(f"replica {self.node_id!r} is unavailable")
        self.chain.receipts.append(receipt)


@dataclass(frozen=True)
class LagAlert:
    """Raised/returned when the 30s secondary budget is exceeded. Implements ENT4-R2."""

    region: str
    receipt_id: str
    lag_seconds: float
    max_lag_seconds: float


@dataclass
class ReceiptReplicator:
    """Real-time receipt chain replicator.

    Implements ENT4-R2 (sync primary region / async secondaries with
    lag tracking and a 30 second max-lag alert) and ENT4-R4 (RPO=0:
    ``append`` acknowledges only after the durability policy is met).
    """

    clock: Clock
    transport: SimulatedTransport
    journal: EventJournal
    primary_region: str
    max_lag_seconds: float = MAX_SECONDARY_LAG_SECONDS
    chain: ReceiptChain = field(default_factory=ReceiptChain)
    replicas: dict[str, ReplicaNode] = field(default_factory=dict)

    def add_replica(self, node: ReplicaNode) -> None:
        if node.node_id in self.replicas:
            raise ContractError("duplicate replica registration")
        node.is_primary_region = node.region == self.primary_region
        self.replicas[node.node_id] = node

    def append(self, task_id: str, payload: str) -> ChainReceipt:
        """Append a receipt and acknowledge only once durable. Implements ENT4-R4."""
        receipt = self.chain.append(task_id, payload)
        try:
            self._replicate_sync_primary(receipt)
        except ContractError:
            # RPO=0: roll back the local head rather than acknowledge a
            # receipt that is not durably replicated per policy.
            self.chain.receipts.pop()
            raise
        self._replicate_async_secondaries(receipt)
        return receipt

    def _replicate_sync_primary(self, receipt: ChainReceipt) -> None:
        """Synchronous replication inside the primary region. Implements ENT4-R2."""
        primaries = [n for n in self.replicas.values()
                     if n.is_primary_region and n.available]
        if not primaries:
            raise ContractError(
                "durability policy unmet: no available primary-region replica (RPO=0)")
        for node in sorted(primaries, key=lambda n: n.node_id):
            node.install(receipt)

    def _replicate_async_secondaries(self, receipt: ChainReceipt) -> None:
        """Asynchronous replication to secondary regions. Implements ENT4-R2."""
        secondaries = sorted(
            {n.region for n in self.replicas.values() if not n.is_primary_region})
        for region in secondaries:
            self.transport.send(self.primary_region, region, receipt)

    def deliver(self) -> list[ReplicaMessage]:
        """Deliver due async messages to secondary replicas. Implements ENT4-R2."""
        delivered = self.transport.flush_due()
        for message in delivered:
            for node in sorted(self.replicas.values(), key=lambda n: n.node_id):
                if node.region == message.target and not node.is_primary_region and node.available:
                    node.install(message.receipt)
        return delivered

    def lag(self, region: str) -> float:
        """Oldest undelivered secondary lag for a region. Implements ENT4-R2."""
        pending = self.transport.pending_for(region)
        if not pending:
            return 0.0
        return self.clock.now() - min(m.enqueued_at for m in pending)

    def check_max_lag(self) -> list[LagAlert]:
        """Assert the 30 second budget and receipt any breach. Implements ENT4-R2."""
        alerts: list[LagAlert] = []
        now = self.clock.now()
        seen: set[tuple[str, str]] = set()
        for message in sorted(self.transport.pending, key=lambda m: (m.target, m.enqueued_at)):
            lag = now - message.enqueued_at
            if lag > self.max_lag_seconds and (message.target, message.receipt.receipt_id) not in seen:
                seen.add((message.target, message.receipt.receipt_id))
                alert = LagAlert(message.target, message.receipt.receipt_id, lag, self.max_lag_seconds)
                alerts.append(alert)
                self.journal.record(LAG_ALERT_EVENT, {
                    "region": alert.region,
                    "receipt_id": alert.receipt_id,
                    "lag_seconds": alert.lag_seconds,
                    "max_lag_seconds": alert.max_lag_seconds,
                })
        return alerts

    def assert_max_lag(self) -> None:
        """Raise ContractError if any secondary lag exceeds 30s. Implements ENT4-R2."""
        alerts = self.check_max_lag()
        if alerts:
            worst = max(alerts, key=lambda a: a.lag_seconds)
            raise ContractError(
                f"replication lag {worst.lag_seconds:.3f}s to {worst.region!r} "
                f"exceeds {worst.max_lag_seconds:.3f}s budget")
