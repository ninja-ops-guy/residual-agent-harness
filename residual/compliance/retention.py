"""Configurable, automatically enforced retention with archive-before-delete.

Implements ENT2-R2: default policies are 7 years for SOX-relevant events,
3 years for operational events, 1 year for debug events. Expired events
are archived before deletion, and events under an active legal hold
(ENT2-R3) are skipped. Enforcement is itself observed in the log.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from ..core import ContractError, canonical
from .legal_hold import LegalHoldManager
from .log import CATEGORIES, ObservationEvent, ObservationLog

SECONDS_PER_YEAR = 365 * 86400
DEFAULT_RETENTION_YEARS = {"sox": 7, "operational": 3, "debug": 1}


@dataclass(frozen=True)
class RetentionPolicy:
    """Category-to-retention-seconds policy. Implements ENT2-R2."""
    years: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_RETENTION_YEARS))

    def __post_init__(self):
        for category, years in self.years.items():
            if category not in CATEGORIES:
                raise ContractError(f"unknown retention category: {category!r}")
            if type(years) is not int or years < 1:
                raise ContractError("retention years must be positive integers")
        missing = set(CATEGORIES) - set(self.years)
        if missing:
            raise ContractError(f"retention policy missing categories: {sorted(missing)}")

    def max_age_seconds(self, category: str) -> int:
        return self.years[category] * SECONDS_PER_YEAR


@dataclass(frozen=True)
class ArchiveRecord:
    """One archived event plus its archive digest. Implements ENT2-R2."""
    event: ObservationEvent
    archive_digest: str


class ArchiveStore:
    """Immutable archive consulted before any deletion. Implements ENT2-R2."""

    def __init__(self):
        self._records: list[ArchiveRecord] = []

    def archive(self, event: ObservationEvent) -> ArchiveRecord:
        digest = hashlib.sha256(("residual.compliance.archive.v1\n" + canonical(event.body())
                                 + "\n" + event.chain_hash).encode("utf-8")).hexdigest()
        record = ArchiveRecord(event, digest)
        self._records.append(record)
        return record

    @property
    def records(self) -> tuple[ArchiveRecord, ...]:
        return tuple(self._records)


@dataclass(frozen=True)
class RetentionReport:
    """Outcome of one enforcement run. Implements ENT2-R2."""
    archived: tuple[int, ...]
    deleted: tuple[int, ...]
    held: tuple[int, ...]
    receipt_hash: str


def enforce_retention(log: ObservationLog, archive: ArchiveStore, policy: RetentionPolicy,
                      now: float, holds: LegalHoldManager | None = None,
                      actor: str = "compliance") -> RetentionReport:
    """Archive-then-delete expired events, respecting legal holds.

    Implements ENT2-R2 (and honors ENT2-R3 holds). Every enforcement run
    appends an observed receipt to the log.
    """
    if not isinstance(now, (int, float)) or now < 0:
        raise ContractError("retention clock must be nonnegative")
    archived, deleted, held = [], [], []
    for event in list(log.events):
        if now - event.timestamp < policy.max_age_seconds(event.category):
            continue
        if holds is not None and holds.blocked(event):
            held.append(event.id)
            continue
        archive.archive(event)
        archived.append(event.id)
        deleted.append(event.id)
    log.remove(set(deleted))
    log.mark_archived([r.event for r in archive.records if r.event.id in set(archived)])
    receipt = log.append("retention", now, actor, "system", category="operational",
                         region="local",
                         payload={"archived": sorted(archived), "deleted": sorted(deleted),
                                  "held": sorted(held)},
                         tags=("SOX-CC7.2", "ISO27001-A.12.4"))
    return RetentionReport(tuple(sorted(archived)), tuple(sorted(deleted)),
                           tuple(sorted(held)), receipt.chain_hash)
