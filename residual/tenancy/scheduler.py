"""Fair multi-tenant scheduling over shared workers.

Implements ENT3-R3: compute may be shared across tenants, but scheduling
must be fair (deficit round-robin with per-tenant quota weights) so no
tenant can starve another; quotas are configurable per tenant.
"""
from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass, field

from ..core import ContractError, identifier


@dataclass(frozen=True)
class Job:
    """A unit of tenant work. Implements ENT3-R3."""
    id: str
    tenant_id: str
    cost: int = 1

    def __post_init__(self):
        identifier(self.id)
        identifier(self.tenant_id)
        if type(self.cost) is not int or self.cost < 1:
            raise ContractError("job cost must be a positive integer")


@dataclass
class FairScheduler:
    """Deficit round-robin scheduler with per-tenant quotas. Implements ENT3-R3.

    Each tenant accrues deficit credit at `quota` units per round; a job
    runs only when its tenant's deficit covers the job cost. Tenants with
    pending work are never skipped for more than a bounded number of
    rounds, so scheduling is starvation-free.
    """
    workers: int = 1
    quotas: dict[str, int] = field(default_factory=dict)
    _queues: dict[str, deque[Job]] = field(default_factory=dict)
    _deficit: dict[str, int] = field(default_factory=dict)
    _round_order: deque[str] = field(default_factory=deque)
    completed: list[Job] = field(default_factory=list)

    def __post_init__(self):
        if type(self.workers) is not int or self.workers < 1:
            raise ContractError("workers must be a positive integer")
        for tenant, quota in self.quotas.items():
            identifier(tenant)
            if type(quota) is not int or quota < 1:
                raise ContractError("tenant quota must be a positive integer")

    def set_quota(self, tenant_id: str, quota: int) -> None:
        """Configure a tenant's scheduling quota (ENT3-R3)."""
        identifier(tenant_id)
        if type(quota) is not int or quota < 1:
            raise ContractError("tenant quota must be a positive integer")
        self.quotas[tenant_id] = quota

    def submit(self, job: Job) -> None:
        """Enqueue a job for its tenant (ENT3-R3)."""
        if not isinstance(job, Job):
            raise ContractError("expected a Job")
        if job.tenant_id not in self._queues:
            self._queues[job.tenant_id] = deque()
            self._deficit[job.tenant_id] = 0
            self._round_order.append(job.tenant_id)
            self.quotas.setdefault(job.tenant_id, 1)
        self._queues[job.tenant_id].append(job)

    def pending(self, tenant_id: str) -> int:
        """Number of queued jobs for a tenant (ENT3-R3)."""
        return len(self._queues.get(tenant_id, ()))

    def run_until_idle(self, max_steps: int = 100000) -> list[Job]:
        """Run the DRR loop until all queues drain. Implements ENT3-R3.

        Deterministic: tenants are served in submission round order;
        ties within a round go to the earliest-submitted tenant.
        """
        if type(max_steps) is not int or max_steps < 1:
            raise ContractError("max_steps must be a positive integer")
        steps = 0
        while any(self._queues[t] for t in self._round_order):
            progressed = False
            for _ in range(len(self._round_order)):
                tenant = self._round_order[0]
                self._round_order.rotate(-1)
                queue = self._queues[tenant]
                if not queue:
                    continue
                self._deficit[tenant] += self.quotas.get(tenant, 1)
                while queue and self._deficit[tenant] >= queue[0].cost and steps < max_steps:
                    job = queue.popleft()
                    self._deficit[tenant] -= job.cost
                    self.completed.append(job)
                    steps += 1
                    progressed = True
                if self._deficit[tenant] > 0 and queue:
                    # Partial credit retained (deficit round-robin).
                    pass
                elif not queue:
                    self._deficit[tenant] = 0
            if not progressed:
                # Cost exceeds any single-round credit; top up deficits.
                if steps >= max_steps:
                    raise ContractError("scheduler exceeded max_steps")
                continue
        return list(self.completed)
