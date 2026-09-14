"""Measured engine-backed driver for SPEC-EVAL-001.

This driver executes a FrozenWorkload through a real ExecutionEngine.  It does
not call a shell and it refuses to classify a run as measured unless every
engine result carries explicit measured provenance and a finalizer binds the
run to a concrete Git output commit.
"""
from __future__ import annotations

import hashlib
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from residual.core import canonical
from residual.engines.protocol import ContextAssembly, EngineResult, ExecutionEngine, TaskSpec
from .eval_framework import EvaluationError, FrozenWorkload, RunMeasurement


@dataclass(frozen=True, slots=True)
class CostRates:
    """Explicit rates used to turn measured usage into comparable cost."""
    api_per_1k_tokens_usd: float = 0.0
    gpu_per_minute_usd: float = 0.0
    infrastructure_per_minute_usd: float = 0.0

    def __post_init__(self):
        for value in (self.api_per_1k_tokens_usd, self.gpu_per_minute_usd,
                      self.infrastructure_per_minute_usd):
            if type(value) not in (int, float) or value < 0:
                raise EvaluationError("invalid evaluation cost rate")


@dataclass(frozen=True, slots=True)
class FinalizedRun:
    output_commit: str
    final_tests_passed: int
    final_tests_total: int
    merge_conflicts: int = 0


class RunFinalizer(Protocol):
    def __call__(self, workload: FrozenWorkload, outputs: Mapping[str, Any],
                 config: str, run_index: int) -> FinalizedRun: ...


class AcceptanceVerifier(Protocol):
    def __call__(self, task_id: str, acceptance: tuple[str, ...], candidate: Any) -> bool: ...


@dataclass(slots=True)
class _TaskRecord:
    result: EngineResult
    elapsed_s: float
    accepted: bool


class EngineBackedEvaluationDriver:
    """Execute the frozen task DAG with an actual Residual ExecutionEngine.

    Configuration semantics are deliberately narrow:
      * single  -> one worker
      * fixed   -> ``fixed_workers`` workers
      * dynamic -> expands/contracts to the ready frontier up to ``max_workers``

    Engine results must include ``raw_metadata['provenance'] == 'measured'``.
    Optional ``gpu_time_ms`` and ``api_cost_usd`` metadata are consumed when
    present. Token usage must be reported by the engine for a measured run.
    """

    def __init__(self, engine: ExecutionEngine, *, finalizer: RunFinalizer,
                 verifier: AcceptanceVerifier | None = None,
                 rates: CostRates | None = None, fixed_workers: int = 4,
                 max_workers: int = 16):
        if not isinstance(fixed_workers, int) or not isinstance(max_workers, int):
            raise EvaluationError("worker limits must be integers")
        if fixed_workers < 1 or max_workers < 1 or fixed_workers > max_workers:
            raise EvaluationError("invalid worker limits")
        self.engine = engine
        self.finalizer = finalizer
        self.verifier = verifier or (lambda _task, _acceptance, candidate: candidate is not None)
        self.rates = rates or CostRates()
        self.fixed_workers = fixed_workers
        self.max_workers = max_workers

    @staticmethod
    def _workers(config: str, ready_count: int, fixed: int, maximum: int) -> int:
        if config == "single":
            return 1
        if config == "fixed":
            return fixed
        if config == "dynamic":
            return max(1, min(maximum, ready_count))
        raise EvaluationError("invalid evaluation config")

    def _execute(self, task, values: Mapping[str, Any]) -> _TaskRecord:
        spec = TaskSpec(
            task_id=task.task_id,
            capability="agent",
            input={"requirements": list(task.requirement_ids), "acceptance": list(task.acceptance)},
            metadata={"evaluation": True},
        )
        context = ContextAssembly({"dependencies": {d: values[d] for d in task.depends_on}})
        started = time.monotonic()
        result = self.engine.execute(spec, context)
        elapsed = time.monotonic() - started
        if not isinstance(result, EngineResult):
            raise EvaluationError("engine returned invalid result")
        if result.token_usage is None or type(result.token_usage) is not int or result.token_usage < 0:
            raise EvaluationError("measured evaluation requires reported token usage")
        if result.raw_metadata.get("provenance") != "measured":
            raise EvaluationError("engine result lacks measured provenance")
        accepted = bool(self.verifier(task.task_id, task.acceptance, result.candidate))
        return _TaskRecord(result=result, elapsed_s=elapsed, accepted=accepted)

    def run(self, workload: FrozenWorkload, config: str, run_index: int,
            observe: Callable[[dict], None]) -> RunMeasurement:
        if self.engine.name != workload.engine_name or self.engine.version != workload.engine_version:
            raise EvaluationError("engine identity does not match frozen workload")
        by_id = {t.task_id: t for t in workload.tasks}
        pending = set(by_id)
        completed: set[str] = set()
        values: dict[str, Any] = {}
        records: dict[str, _TaskRecord] = {}
        verifier_total = verifier_rejected = rework = 0
        token_total = 0
        gpu_ms = 0.0
        api_cost = 0.0
        coordination_s = 0.0
        peak_workers = 1
        lock = threading.Lock()
        started = time.monotonic()

        observe({"event": "MeasuredFactoryRunStarted", "config": config,
                 "run_index": run_index, "engine_name": self.engine.name,
                 "engine_version": self.engine.version})

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            active = {}
            while pending or active:
                coord_started = time.monotonic()
                ready = sorted(tid for tid in pending if set(by_id[tid].depends_on) <= completed)
                capacity = self._workers(config, len(ready), self.fixed_workers, self.max_workers)
                free = max(0, capacity - len(active))
                for tid in ready[:free]:
                    pending.remove(tid)
                    dep_values = dict(values)
                    active[pool.submit(self._execute, by_id[tid], dep_values)] = tid
                peak_workers = max(peak_workers, len(active))
                coordination_s += time.monotonic() - coord_started
                if not active:
                    if pending:
                        raise EvaluationError("evaluation DAG made no progress")
                    break
                done, _ = wait(tuple(active), return_when=FIRST_COMPLETED)
                for future in done:
                    tid = active.pop(future)
                    record = future.result()
                    with lock:
                        records[tid] = record
                        verifier_total += 1
                        if record.accepted:
                            values[tid] = record.result.candidate
                            completed.add(tid)
                        else:
                            verifier_rejected += 1
                            rework += 1
                            # A rejected task is terminal for reproducible evaluation;
                            # dependants cannot silently run on an unverified candidate.
                            raise EvaluationError(f"task {tid} rejected during measured evaluation")
                        token_total += record.result.token_usage or 0
                        md = record.result.raw_metadata
                        gpu_ms += float(md.get("gpu_time_ms", 0.0))
                        api_cost += float(md.get("api_cost_usd", 0.0))
                    observe({"event": "MeasuredFactoryTaskCompleted", "task_id": tid,
                             "accepted": record.accepted, "token_usage": record.result.token_usage,
                             "wall_clock_ms": record.result.wall_clock_ms})

        finalized = self.finalizer(workload, values, config, run_index)
        elapsed_s = time.monotonic() - started
        gpu_minutes = gpu_ms / 60000.0
        if api_cost == 0.0 and self.rates.api_per_1k_tokens_usd:
            api_cost = token_total / 1000.0 * self.rates.api_per_1k_tokens_usd
        gpu_cost = gpu_minutes * self.rates.gpu_per_minute_usd
        infra_cost = elapsed_s / 60.0 * self.rates.infrastructure_per_minute_usd
        digest = hashlib.sha256(canonical({
            "engine": [self.engine.name, self.engine.version],
            "config": config, "run_index": run_index,
            "tasks": {k: {"tokens": v.result.token_usage,
                            "elapsed_s": v.elapsed_s,
                            "accepted": v.accepted}
                      for k, v in sorted(records.items())},
            "output_commit": finalized.output_commit,
            "peak_workers": peak_workers,
        }).encode()).hexdigest()
        observe({"event": "MeasuredFactoryRunCompleted", "config": config,
                 "run_index": run_index, "output_commit": finalized.output_commit,
                 "peak_workers": peak_workers, "observation_digest": digest})
        return RunMeasurement(
            config=config, run_index=run_index,
            elapsed_time_minutes=elapsed_s / 60.0,
            accepted_tasks=len(completed), token_cost_total=token_total,
            gpu_time_minutes=gpu_minutes,
            coordination_time_minutes=coordination_s / 60.0,
            rework_tasks=rework, merge_conflicts=finalized.merge_conflicts,
            verifier_rejected=verifier_rejected, verifier_total=verifier_total,
            final_tests_passed=finalized.final_tests_passed,
            final_tests_total=finalized.final_tests_total,
            api_cost_usd=api_cost, gpu_cost_usd=gpu_cost,
            infrastructure_cost_usd=infra_cost,
            engine_name=self.engine.name, engine_version=self.engine.version,
            output_commit=finalized.output_commit, observation_digest=digest,
            simulation=False,
        )
