"""Assurance strategy adapter for Residual Factory's bounded local swarm runtime.

The selected ExecutionEngine authors worker source on the trusted host. The source
is then executed only inside FactoryRuntime's preapproved WorkerContracts. Factory
candidates remain quarantined; this adapter never merges or issues Station receipts.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol, Sequence

from ..engines.protocol import ContextAssembly, EngineResult, ExecutionEngine, TaskSpec
from ..factory.models import ExecutionPlan as FactoryExecutionPlan, FrozenPlan
from ..factory.runtime import FactoryRuntime, RuntimeResult
from ..factory.worker_contract import WorkerContract


class FactoryAssuranceError(RuntimeError):
    """Factory-backed assurance execution could not preserve its bindings."""


@dataclass(frozen=True)
class FactoryWorkerTemplate:
    contract: WorkerContract
    author_prompt: str

    def __post_init__(self) -> None:
        if not isinstance(self.contract, WorkerContract):
            raise FactoryAssuranceError("worker template requires a WorkerContract")
        if not isinstance(self.author_prompt, str) or not self.author_prompt.strip():
            raise FactoryAssuranceError("worker author prompt is required")


@dataclass(frozen=True)
class FactoryFixedSwarmJob:
    plan: FactoryExecutionPlan
    approval: FrozenPlan
    workers: tuple[FactoryWorkerTemplate, ...]
    capacity: int = 2

    def __post_init__(self) -> None:
        if not isinstance(self.plan, FactoryExecutionPlan) or not isinstance(self.approval, FrozenPlan):
            raise FactoryAssuranceError("factory job requires ExecutionPlan and FrozenPlan")
        self.approval.assert_matches(self.plan)
        if len(self.workers) < 2:
            raise FactoryAssuranceError("fixed swarm requires at least two workers")
        if type(self.capacity) is not int or not 1 <= self.capacity <= 32:
            raise FactoryAssuranceError("factory swarm capacity must be between 1 and 32")
        attempts = [item.contract.attempt_id for item in self.workers]
        workers = [item.contract.worker_id for item in self.workers]
        if len(attempts) != len(set(attempts)) or len(workers) != len(set(workers)):
            raise FactoryAssuranceError("factory swarm worker and attempt ids must be unique")
        for item in self.workers:
            item.contract.assert_matches_plan(self.plan)


class FactoryJobBuilder(Protocol):
    def __call__(
        self,
        engine: ExecutionEngine,
        task: TaskSpec,
        context: ContextAssembly,
    ) -> FactoryFixedSwarmJob: ...


CandidateIntegrator = Callable[[Sequence[RuntimeResult]], Any]


def candidate_manifest(results: Sequence[RuntimeResult]) -> dict[str, Any]:
    """Deterministic, content-hash-only view of quarantined Factory candidates."""
    rows = []
    for result in sorted(results, key=lambda value: value.attempt_id):
        candidate = result.candidate.to_dict() if result.candidate is not None else None
        rows.append({
            "attempt_id": result.attempt_id,
            "status": result.status,
            "contract_hash": result.contract_hash,
            "execution_plan_hash": result.execution_plan_hash,
            "candidate": candidate,
            "reason": result.reason,
        })
    return {
        "schema_version": "residual.assurance-factory-candidates.v1",
        "status": "QUARANTINED_CANDIDATES",
        "workers": rows,
    }


def _python_source(candidate: Any) -> str:
    if not isinstance(candidate, str):
        raise FactoryAssuranceError("worker author engine must return Python source text")
    source = candidate.strip()
    # Do not silently reinterpret fenced prose as executable source. The authoring
    # contract requires raw Python so the exact engine output is what gets sandboxed.
    if source.startswith("```") or source.endswith("```"):
        raise FactoryAssuranceError("worker author engine returned fenced source")
    if not source:
        raise FactoryAssuranceError("worker author engine returned empty source")
    return source


def _authoring_task(
    *,
    parent: TaskSpec,
    context: ContextAssembly,
    template: FactoryWorkerTemplate,
    index: int,
) -> TaskSpec:
    contract = template.contract
    prompt = (
        "Author raw Python source for a Residual Factory worker. Return Python only; no Markdown fences.\n"
        "The sandbox exposes exactly these host-brokered functions when allowed by the WorkerContract:\n"
        "  read_file(path) -> text\n"
        "  write_file(path, content)\n"
        "  delete_file(path)\n"
        "Direct filesystem, network, process creation and shell access are unavailable.\n"
        "Do not use eval, exec, dynamic imports, or unapproved interfaces.\n"
        "Complete the assigned work using only the broker functions and ordinary in-memory Python.\n\n"
        f"Parent task id: {parent.task_id}\n"
        f"Parent task input: {parent.input!r}\n"
        f"Worker id: {contract.worker_id}\n"
        f"Factory task id: {contract.task_id}\n"
        f"Requirements: {', '.join(contract.requirements)}\n"
        f"Acceptance: {', '.join(contract.acceptance)}\n"
        f"Readable paths: {', '.join(contract.inputs) or '(none)'}\n"
        f"Writable paths: {', '.join(contract.allowed_outputs) or '(none)'}\n"
        f"Allowed broker tools: {', '.join(contract.allowed_tools) or '(none)'}\n"
        f"Worker assignment: {template.author_prompt.strip()}\n"
    )
    if context.values:
        prompt += f"Trusted context keys available to the authoring model: {', '.join(sorted(map(str, context.values)))}\n"
    return TaskSpec(
        task_id=f"{parent.task_id}.factory-author.{index}",
        capability=parent.capability,
        input=prompt,
        metadata={**dict(parent.metadata), "factory_worker_id": contract.worker_id, "factory_attempt_id": contract.attempt_id},
    )


@dataclass
class FactoryFixedSwarmExecutor:
    """Callable `StrategyExecutor` for `ExecutionStrategy.FIXED_SWARM`.

    The market-selected engine authors every worker. Contracts must bind that exact
    engine id through `engine_hint`; this prevents a Factory swarm from being credited
    to a model that did not author its worker source. Unknown authoring token usage is
    rejected because the WorkerContract token budget could not otherwise be enforced.
    """

    runtime: FactoryRuntime
    build_job: FactoryJobBuilder
    integrate: CandidateIntegrator = candidate_manifest

    def __call__(self, engine: ExecutionEngine, task: TaskSpec, context: ContextAssembly) -> EngineResult:
        if not isinstance(self.runtime, FactoryRuntime):
            raise FactoryAssuranceError("FactoryFixedSwarmExecutor requires FactoryRuntime")
        job = self.build_job(engine, task, context)
        if not isinstance(job, FactoryFixedSwarmJob):
            raise FactoryAssuranceError("factory job builder returned invalid job")

        engine_id = f"{engine.name}@{engine.version}"
        sources: list[tuple[WorkerContract, str]] = []
        token_total = 0
        author_traces: list[Mapping[str, Any]] = []

        started = time.monotonic()
        for index, template in enumerate(job.workers, 1):
            contract = template.contract
            if contract.engine_hint != engine_id:
                raise FactoryAssuranceError("WorkerContract.engine_hint must bind the market-selected engine")
            authored = engine.execute(_authoring_task(
                parent=task, context=context, template=template, index=index,
            ), context)
            source = _python_source(authored.candidate)
            if authored.token_usage is None:
                raise FactoryAssuranceError("worker authoring token usage is unknown")
            if authored.token_usage > contract.token_budget:
                raise FactoryAssuranceError("worker authoring token usage exceeds WorkerContract budget")
            token_total += authored.token_usage
            sources.append((contract, source))
            author_traces.append({
                "worker_id": contract.worker_id,
                "attempt_id": contract.attempt_id,
                "contract_hash": contract.contract_hash,
                "author_token_usage": authored.token_usage,
                "author_wall_clock_ms": authored.wall_clock_ms,
            })

        results = tuple(self.runtime.run_many(
            job.plan,
            job.approval,
            sources,
            capacity=job.capacity,
        ))
        if len(results) != len(job.workers):
            raise FactoryAssuranceError("FactoryRuntime returned an incomplete swarm result set")
        expected = {item.contract.attempt_id for item in job.workers}
        if {result.attempt_id for result in results} != expected:
            raise FactoryAssuranceError("FactoryRuntime result identities differ from approved worker attempts")

        candidate = self.integrate(results)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        statuses = {result.attempt_id: result.status for result in results}
        return EngineResult(
            candidate=candidate,
            token_usage=token_total,
            wall_clock_ms=elapsed_ms,
            engine_trace=tuple(author_traces),
            raw_metadata={
                "strategy_backend": "factory-runtime",
                "factory_profile": "fixed-swarm-v1",
                "factory_plan_hash": job.plan.graph_hash,
                "factory_capacity": job.capacity,
                "factory_statuses": statuses,
                "engine_attribution": engine_id,
                "candidate_state": "quarantined",
                "merge_performed": False,
                "station_receipt_issued": False,
            },
        )
