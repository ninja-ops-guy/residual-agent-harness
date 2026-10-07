"""Adaptive multi-wave execution on top of Residual FactoryRuntime.

Dynamic here means the host scheduler may change wave size and concurrency only
between completed waves. Every WorkerContract remains frozen before its attempt;
workers never mutate their own limits or spawn peers.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from ..engines.protocol import ContextAssembly, EngineResult, ExecutionEngine, TaskSpec
from ..factory.runtime import FactoryRuntime, RuntimeResult
from ..factory.worker_contract import WorkerContract
from .factory_adapter import (
    FactoryAssuranceError,
    FactoryFixedSwarmJob,
    FactoryWorkerTemplate,
    _authoring_task,
    _python_source,
    candidate_manifest,
)


@dataclass(frozen=True)
class DynamicWaveDecision:
    batch_size: int
    capacity: int

    def __post_init__(self) -> None:
        if type(self.batch_size) is not int or self.batch_size < 1:
            raise FactoryAssuranceError("dynamic wave batch_size must be positive")
        if type(self.capacity) is not int or not 1 <= self.capacity <= 32:
            raise FactoryAssuranceError("dynamic wave capacity must be between 1 and 32")


class DynamicSwarmPolicy(Protocol):
    def __call__(
        self,
        remaining: tuple[FactoryWorkerTemplate, ...],
        completed: tuple[RuntimeResult, ...],
    ) -> DynamicWaveDecision: ...


@dataclass(frozen=True)
class FactoryDynamicSwarmJob:
    base: FactoryFixedSwarmJob
    policy: DynamicSwarmPolicy

    def __post_init__(self) -> None:
        if not isinstance(self.base, FactoryFixedSwarmJob):
            raise FactoryAssuranceError("dynamic swarm requires a validated FactoryFixedSwarmJob base")
        if not callable(self.policy):
            raise FactoryAssuranceError("dynamic swarm policy must be callable")


class FactoryDynamicJobBuilder(Protocol):
    def __call__(
        self,
        engine: ExecutionEngine,
        task: TaskSpec,
        context: ContextAssembly,
    ) -> FactoryDynamicSwarmJob: ...


class FactoryAdmissionProtocol(Protocol):
    def admit(
        self,
        contracts: Sequence[WorkerContract],
        results: Sequence[RuntimeResult],
    ) -> Any: ...


@dataclass
class FactoryDynamicSwarmExecutor:
    runtime: FactoryRuntime
    build_job: FactoryDynamicJobBuilder
    admission: FactoryAdmissionProtocol | None = None

    def __call__(self, engine: ExecutionEngine, task: TaskSpec, context: ContextAssembly) -> EngineResult:
        if not isinstance(self.runtime, FactoryRuntime):
            raise FactoryAssuranceError("FactoryDynamicSwarmExecutor requires FactoryRuntime")
        job = self.build_job(engine, task, context)
        if not isinstance(job, FactoryDynamicSwarmJob):
            raise FactoryAssuranceError("dynamic job builder returned invalid job")

        base = job.base
        engine_id = f"{engine.name}@{engine.version}"
        authored_sources: dict[str, str] = {}
        token_total = 0
        author_traces: list[Mapping[str, Any]] = []
        started = time.monotonic()

        # Author every frozen worker before dispatch so an authoring failure cannot
        # partially expand the swarm after runtime execution has begun.
        for index, template in enumerate(base.workers, 1):
            contract = template.contract
            if contract.engine_hint != engine_id:
                raise FactoryAssuranceError("WorkerContract.engine_hint must bind the market-selected engine")
            authored = engine.execute(
                _authoring_task(parent=task, context=context, template=template, index=index),
                context,
            )
            source = _python_source(authored.candidate)
            if authored.token_usage is None:
                raise FactoryAssuranceError("worker authoring token usage is unknown")
            if authored.token_usage > contract.token_budget:
                raise FactoryAssuranceError("worker authoring token usage exceeds WorkerContract budget")
            authored_sources[contract.attempt_id] = source
            token_total += authored.token_usage
            author_traces.append({
                "worker_id": contract.worker_id,
                "attempt_id": contract.attempt_id,
                "contract_hash": contract.contract_hash,
                "author_token_usage": authored.token_usage,
                "author_wall_clock_ms": authored.wall_clock_ms,
            })

        pending = list(base.workers)
        completed: list[RuntimeResult] = []
        waves: list[dict[str, Any]] = []
        wave_number = 0
        while pending:
            decision = job.policy(tuple(pending), tuple(completed))
            if not isinstance(decision, DynamicWaveDecision):
                raise FactoryAssuranceError("dynamic swarm policy returned invalid decision")
            if decision.batch_size > len(pending):
                raise FactoryAssuranceError("dynamic wave batch_size exceeds remaining workers")
            if decision.capacity > decision.batch_size:
                raise FactoryAssuranceError("dynamic wave capacity cannot exceed batch_size")

            selected = pending[:decision.batch_size]
            pairs = [(item.contract, authored_sources[item.contract.attempt_id]) for item in selected]
            results = tuple(self.runtime.run_many(
                base.plan,
                base.approval,
                pairs,
                capacity=decision.capacity,
            ))
            expected = {item.contract.attempt_id for item in selected}
            if len(results) != len(selected) or {r.attempt_id for r in results} != expected:
                raise FactoryAssuranceError("FactoryRuntime dynamic wave result identities differ from approved attempts")

            completed.extend(results)
            del pending[:decision.batch_size]
            wave_number += 1
            waves.append({
                "wave": wave_number,
                "batch_size": decision.batch_size,
                "capacity": decision.capacity,
                "attempt_ids": [item.contract.attempt_id for item in selected],
                "statuses": {result.attempt_id: result.status for result in results},
            })

        receipt_hashes: tuple[str, ...] = ()
        admitted = False
        if self.admission is not None:
            admission_result = self.admission.admit(
                tuple(item.contract for item in base.workers),
                tuple(completed),
            )
            receipt_hashes = tuple(getattr(admission_result, "receipt_hashes", ()))
            if len(receipt_hashes) != len(base.workers):
                raise FactoryAssuranceError("M3 admission did not return one receipt per worker")
            admitted = True

        elapsed_ms = int((time.monotonic() - started) * 1000)
        return EngineResult(
            candidate=candidate_manifest(tuple(completed)),
            token_usage=token_total,
            wall_clock_ms=elapsed_ms,
            engine_trace=tuple(author_traces),
            raw_metadata={
                "strategy_backend": "factory-runtime",
                "factory_profile": "dynamic-swarm-v1",
                "factory_plan_hash": base.plan.graph_hash,
                "factory_waves": waves,
                "engine_attribution": engine_id,
                "candidate_state": "m3-admitted" if admitted else "quarantined",
                "merge_performed": False,
                "station_receipt_issued": admitted,
                "station_receipt_hashes": receipt_hashes,
            },
        )
