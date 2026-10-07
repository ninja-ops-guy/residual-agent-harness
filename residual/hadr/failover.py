"""Mid-run failover and run resumption.

Implements ENT4-R3: when the primary station fails mid-run, a secondary
station resumes from the last verified receipt, identifies incomplete
tasks, reassigns them to available workers, and continues execution
without human intervention. Implements ENT4-R4: measured failover time
(RTO) must be under 60 seconds, measured with the injected clock.
Failover events are observed and receipted per ENT4-R8.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core import ContractError
from .chain import ReceiptChain
from .clock import Clock
from .cluster import Station, StationRegistry
from .events import EventJournal, FAILOVER_EVENT

RTO_LIMIT_SECONDS = 60.0

TASK_PENDING = "pending"
TASK_RUNNING = "running"
TASK_DONE = "done"
_STATUSES = {TASK_PENDING, TASK_RUNNING, TASK_DONE}


@dataclass
class TaskRecord:
    """A unit of work in a run. Implements ENT4-R3."""

    task_id: str
    status: str = TASK_PENDING
    worker: str | None = None
    receipt_id: str | None = None

    def __post_init__(self):
        if self.status not in _STATUSES:
            raise ContractError(f"invalid task status: {self.status!r}")

    @property
    def incomplete(self) -> bool:
        return self.status != TASK_DONE


@dataclass
class RunState:
    """A run: tasks plus the receipt chain recording progress. Implements ENT4-R3."""

    run_id: str
    station_id: str
    tasks: list[TaskRecord] = field(default_factory=list)
    chain: ReceiptChain = field(default_factory=ReceiptChain)

    def complete(self, task_id: str, worker: str, payload: str) -> None:
        task = self._task(task_id)
        task.status = TASK_DONE
        task.worker = worker
        task.receipt_id = self.chain.append(task_id, payload).receipt_id

    def incomplete_tasks(self) -> list[TaskRecord]:
        """Tasks needing reassignment after failover. Implements ENT4-R3."""
        return [t for t in self.tasks if t.incomplete]

    def _task(self, task_id: str) -> TaskRecord:
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        raise ContractError(f"unknown task: {task_id!r}")


@dataclass(frozen=True)
class FailoverReport:
    """Outcome of an automatic mid-run failover. Implements ENT4-R3 and ENT4-R4."""

    run_id: str
    failed_station: str
    successor_station: str
    resumed_from_receipt: str | None
    incomplete_tasks: tuple[str, ...]
    reassignments: tuple[tuple[str, str], ...]
    rto_seconds: float
    within_rto: bool


@dataclass
class FailoverController:
    """Coordinates mid-run failover between stations.

    Implements ENT4-R3 (resume from last verified receipt, identify
    incomplete tasks, reassign to available workers, no human
    intervention) and ENT4-R4 (RTO < 60s, measured on the injected
    clock). Events are observed and receipted per ENT4-R8.
    """

    clock: Clock
    registry: StationRegistry
    journal: EventJournal
    rto_limit_seconds: float = RTO_LIMIT_SECONDS

    def failover(self, run: RunState, failed_station_id: str) -> FailoverReport:
        started = self.clock.now()
        failed = self.registry.stations.get(failed_station_id)
        if failed is None:
            raise ContractError(f"unknown station: {failed_station_id!r}")
        if failed.alive:
            failed.fail()

        # Resume from the last verified receipt (chain must verify). ENT4-R3.
        last = run.chain.last_verified
        successor = self.registry._successor_for(failed)
        run.station_id = successor.station_id

        # Identify incomplete tasks and reassign to available workers. ENT4-R3.
        workers = list(successor.workers)
        if not workers:
            raise ContractError("successor station has no available workers")
        incomplete = run.incomplete_tasks()
        reassignments: list[tuple[str, str]] = []
        for index, task in enumerate(incomplete):
            worker = workers[index % len(workers)]
            task.worker = worker
            task.status = TASK_PENDING
            reassignments.append((task.task_id, worker))

        completed = self.clock.now()
        rto = completed - started
        report = FailoverReport(
            run_id=run.run_id,
            failed_station=failed_station_id,
            successor_station=successor.station_id,
            resumed_from_receipt=last.receipt_id if last else None,
            incomplete_tasks=tuple(t.task_id for t in incomplete),
            reassignments=tuple(reassignments),
            rto_seconds=rto,
            within_rto=rto < self.rto_limit_seconds,
        )
        self.journal.record(FAILOVER_EVENT, {
            "run_id": report.run_id,
            "failed_station": report.failed_station,
            "successor_station": report.successor_station,
            "resumed_from_receipt": report.resumed_from_receipt or "",
            "incomplete_tasks": list(report.incomplete_tasks),
            "rto_seconds": report.rto_seconds,
            "within_rto": report.within_rto,
        })
        return report
