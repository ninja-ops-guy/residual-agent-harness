"""Quarterly restore drills with integrity verification.

Implements ENT4-R6: restoration is tested at least quarterly; a
restoration test restores from a backup, verifies receipt chain
integrity, verifies observation log completeness, and produces a
restoration report. Restore tests are observed and receipted per
ENT4-R8.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core import ContractError
from .backup import BackupManager, BackupRecord, KeyManager, REQUIRED_COMPONENTS, decrypt_backup
from .chain import ChainReceipt, ReceiptChain
from .clock import Clock
from .events import EventJournal, RESTORE_EVENT

QUARTER_SECONDS = 92 * 24 * 60 * 60  # worst-case quarter (Jul+Aug+Sep)


@dataclass(frozen=True)
class RestorationReport:
    """Result of a restoration test. Implements ENT4-R6."""

    backup_id: str
    tested_at: float
    restored: bool
    chain_intact: bool
    observation_log_complete: bool
    components_present: tuple[str, ...]
    ok: bool
    notes: tuple[str, ...]


@dataclass
class RestoreDrill:
    """Runs restoration tests against backups. Implements ENT4-R6."""

    clock: Clock
    journal: EventJournal
    key_manager: KeyManager
    reports: list[RestorationReport] = field(default_factory=list)

    def run(self, backup: BackupRecord, expected_observations: int | None = None) -> RestorationReport:
        """Restore, verify integrity, and report. Implements ENT4-R6 and ENT4-R8."""
        notes: list[str] = []
        restored = False
        chain_intact = False
        log_complete = False
        components: tuple[str, ...] = ()
        try:
            snapshot = decrypt_backup(backup, self.key_manager)
            restored = True
            missing = [c for c in REQUIRED_COMPONENTS if c not in snapshot]
            components = tuple(c for c in REQUIRED_COMPONENTS if c in snapshot)
            if missing:
                notes.append(f"missing components: {', '.join(missing)}")
            chain = ReceiptChain([
                ChainReceipt(
                    receipt_id=r["receipt_id"],
                    sequence=int(r["sequence"]),
                    task_id=r["task_id"],
                    payload=r["payload"],
                    prev_hash=r["prev_hash"],
                )
                for r in snapshot.get("receipt_chain", [])
            ])
            chain_intact = chain.verify()
            if not chain_intact:
                notes.append("receipt chain integrity check failed")
            log = snapshot.get("observation_log", [])
            if expected_observations is not None:
                log_complete = len(log) >= expected_observations
            else:
                log_complete = isinstance(log, list)
            if not log_complete:
                notes.append("observation log incomplete")
        except ContractError as exc:
            notes.append(f"restore failed: {exc}")
        report = RestorationReport(
            backup_id=backup.backup_id,
            tested_at=self.clock.now(),
            restored=restored,
            chain_intact=chain_intact,
            observation_log_complete=log_complete,
            components_present=components,
            ok=restored and chain_intact and log_complete and not any(
                n.startswith("missing components") for n in notes),
            notes=tuple(notes),
        )
        self.reports.append(report)
        self.journal.record(RESTORE_EVENT, {
            "backup_id": report.backup_id,
            "ok": report.ok,
            "chain_intact": report.chain_intact,
            "observation_log_complete": report.observation_log_complete,
            "notes": list(report.notes),
        })
        return report

    def quarterly_test_due(self) -> bool:
        """True when a quarterly restoration test is overdue. Implements ENT4-R6."""
        if not self.reports:
            return True
        last = max(r.tested_at for r in self.reports)
        return self.clock.now() - last >= QUARTER_SECONDS

    def assert_quarterly_tested(self) -> None:
        if self.quarterly_test_due():
            raise ContractError("restoration test overdue (must be at least quarterly)")
