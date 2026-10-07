"""Data residency: regional storage and approved cross-border transfer.

Implements ENT2-R4: receipts, observations, and station state are stored
in the region where the task executed. Cross-border data flow requires
explicit policy approval and is observed in the log.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from pathlib import Path

from ..core import ContractError, canonical
from .log import ObservationEvent, ObservationLog

_REGION = __import__("re").compile(r"^[a-z]{2}-[a-z]+-[0-9]+$|^local$")


@dataclass(frozen=True)
class ResidencyPolicy:
    """Known regions plus which cross-border pairs are approvable. ENT2-R4."""
    regions: tuple[str, ...] = ("local",)
    allowed_flows: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if not self.regions or any(not _REGION.fullmatch(r) for r in self.regions):
            raise ContractError("invalid region name")
        for src, dst in self.allowed_flows:
            if src not in self.regions or dst not in self.regions:
                raise ContractError("allowed flow references unknown region")


@dataclass(frozen=True)
class TransferApproval:
    """Explicit, recorded approval of one cross-border transfer. ENT2-R4."""
    id: int
    source_region: str
    target_region: str
    approver: str
    event_ids: tuple[int, ...]
    receipt_hash: str


class RegionStore:
    """Writes events to region-partitioned files. Implements ENT2-R4."""

    def __init__(self, root: Path | str, policy: ResidencyPolicy, log: ObservationLog | None = None):
        self.root = Path(root)
        self.policy = policy
        self.log = log
        self._counter = itertools.count(1)
        self._approvals: list[TransferApproval] = []

    def _check_region(self, region: str) -> None:
        if region not in self.policy.regions:
            raise ContractError(f"unknown residency region: {region!r}")

    def store(self, event: ObservationEvent) -> Path:
        """Persist an event in the region where its task executed."""
        self._check_region(event.region)
        directory = self.root / event.region
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"event-{event.id}.json"
        path.write_text(json.dumps(event.body(), sort_keys=True), encoding="utf-8")
        return path

    def transfer(self, event: ObservationEvent, target_region: str, *,
                 approved: bool, approver: str = "", timestamp: float = 0.0) -> Path:
        """Cross-border transfer: explicit approval required and observed.

        Implements ENT2-R4. Raises ContractError without approval or when
        the flow is not permitted by policy.
        """
        self._check_region(event.region)
        self._check_region(target_region)
        if event.region == target_region:
            return self.store(event)
        if not approved or not approver.strip():
            raise ContractError("cross-border transfer requires explicit policy approval")
        if (event.region, target_region) not in self.policy.allowed_flows:
            raise ContractError("cross-border flow is not permitted by residency policy")
        payload = {"source_region": event.region, "target_region": target_region,
                   "approver": approver, "event_id": event.id}
        receipt_hash = hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()
        if self.log is not None:
            receipt = self.log.append("transfer", timestamp, approver, event.task_id,
                                      category="sox", region=target_region, payload=payload,
                                      tags=("GDPR-Art44", "ISO27001-A.13.2"))
            receipt_hash = receipt.chain_hash
        self._approvals.append(TransferApproval(next(self._counter), event.region,
                                                target_region, approver, (event.id,), receipt_hash))
        directory = self.root / target_region
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"event-{event.id}.json"
        path.write_text(json.dumps(event.body(), sort_keys=True), encoding="utf-8")
        return path

    @property
    def approvals(self) -> tuple[TransferApproval, ...]:
        return tuple(self._approvals)
