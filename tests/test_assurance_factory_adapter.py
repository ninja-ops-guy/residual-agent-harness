from __future__ import annotations

import unittest

from residual.assurance.factory_adapter import (
    FactoryAssuranceError,
    FactoryFixedSwarmExecutor,
    FactoryFixedSwarmJob,
    FactoryWorkerTemplate,
)
from residual.assurance.market import MarketProfile
from residual.assurance.orchestration import ExecutionStrategy
from residual.assurance.quality import AssuranceClass
from residual.assurance.runtime import AdaptiveAssuranceRuntime
from residual.engines.protocol import ContextAssembly, EngineHealth, EngineResult, TaskSpec
from residual.factory.models import ExecutionPlan, FactoryTask, FrozenPlan, Requirement
from residual.factory.runtime import FactoryRuntime, RuntimeResult
from residual.factory.runtime_workspace import CandidateTree
from residual.factory.worker_contract import WorkerContract


class AuthorEngine:
    name = "author"
    version = "v1"
    capability_class = "test"
    locality = "local"

    def __init__(self, token_usage=4):
        self.token_usage = token_usage
        self.calls = []

    @property
    def engine_id(self):
        return f"{self.name}@{self.version}"

    def supports(self, capability):
        return capability == "code"

    def health(self):
        return EngineHealth.HEALTHY

    def execute(self, task, context):
        self.calls.append(task)
        worker = task.metadata["factory_worker_id"]
        return EngineResult(
            candidate=f"write_file('out-{worker}.txt', 'ok')",
            token_usage=self.token_usage,
            wall_clock_ms=2,
        )

    def normalize(self, raw_output):
        return raw_output if isinstance(raw_output, EngineResult) else EngineResult(candidate=raw_output)


class FakeFactoryRuntime(FactoryRuntime):
    def __init__(self):
        self.calls = []

    def run_many(self, plan, approval, workers, *, capacity=2):
        self.calls.append((plan, approval, tuple(workers), capacity))
        rows = []
        for contract, _source in workers:
            candidate = CandidateTree(
                input_commit=contract.input_commit,
                output_commit="b" * 40,
                output_tree="c" * 40,
                artifacts=((f"out-{contract.worker_id}.txt", "d" * 64),),
            )
            rows.append(RuntimeResult(
                attempt_id=contract.attempt_id,
                status="CANDIDATE",
                contract_hash=contract.contract_hash,
                execution_plan_hash=plan.graph_hash,
                returncode=0,
                process_reaped=True,
                usage={"tool_calls": 1, "file_writes": 1, "tokens": 0},
                candidate=candidate,
                reason="awaiting_station_verification",
            ))
        return rows


class FactoryAdapterTests(unittest.TestCase):
    def make_job(self, engine_id="author@v1", token_budget=10):
        plan = ExecutionPlan(
            "parallel bounded edits",
            (
                Requirement("R1", "write first", ("unit",)),
                Requirement("R2", "write second", ("unit",)),
            ),
            (
                FactoryTask("task1", "first", ("R1",), swarm="swarm1"),
                FactoryTask("task2", "second", ("R2",), swarm="swarm1"),
            ),
        )
        approval = FrozenPlan.approve(plan, "test-operator")
        workers = []
        for index, (task_id, req) in enumerate((("task1", "R1"), ("task2", "R2")), 1):
            contract = WorkerContract(
                task_id=task_id,
                worker_id=f"worker{index}",
                swarm_id="swarm1",
                execution_plan_hash=plan.graph_hash,
                attempt_id=f"attempt{index}",
                lease_id=f"lease{index}",
                lease_generation=index,
                input_commit="a" * 40,
                workspace_root=f"/runtime/swarm1/attempt{index}",
                inputs=(),
                allowed_outputs=(f"out-worker{index}.txt",),
                forbidden=("secret.txt",),
                requirements=(req,),
                acceptance=("unit",),
                dependencies=(),
                allowed_tools=("write_file",),
                forbidden_tools=("shell",),
                token_budget=token_budget,
                wall_clock_budget_s=5,
                max_tool_calls=3,
                max_file_writes=2,
                memory_limit_mb=128,
                engine_hint=engine_id,
            )
            workers.append(FactoryWorkerTemplate(contract, f"write output for {task_id}"))
        return FactoryFixedSwarmJob(plan, approval, tuple(workers), capacity=2)

    def test_fixed_swarm_authors_then_runs_quarantined_candidates(self):
        engine = AuthorEngine()
        runtime = FakeFactoryRuntime()
        job = self.make_job(engine.engine_id)
        executor = FactoryFixedSwarmExecutor(runtime, lambda _engine, _task, _context: job)
        result = executor(engine, TaskSpec("parent", "code", "make edits"), ContextAssembly())

        self.assertEqual(len(engine.calls), 2)
        self.assertEqual(len(runtime.calls), 1)
        self.assertEqual(result.token_usage, 8)
        self.assertEqual(result.raw_metadata["engine_attribution"], engine.engine_id)
        self.assertEqual(result.raw_metadata["candidate_state"], "quarantined")
        self.assertFalse(result.raw_metadata["merge_performed"])
        self.assertEqual(result.candidate["status"], "QUARANTINED_CANDIDATES")
        self.assertEqual([row["attempt_id"] for row in result.candidate["workers"]], ["attempt1", "attempt2"])

    def test_engine_hint_and_authoring_budget_are_enforced_before_runtime(self):
        engine = AuthorEngine(token_usage=11)
        runtime = FakeFactoryRuntime()
        job = self.make_job(engine.engine_id, token_budget=10)
        executor = FactoryFixedSwarmExecutor(runtime, lambda _engine, _task, _context: job)
        with self.assertRaisesRegex(FactoryAssuranceError, "token usage"):
            executor(engine, TaskSpec("parent", "code", "make edits"), ContextAssembly())
        self.assertEqual(runtime.calls, [])

        mismatched = self.make_job("other@v1")
        executor = FactoryFixedSwarmExecutor(runtime, lambda _engine, _task, _context: mismatched)
        with self.assertRaisesRegex(FactoryAssuranceError, "engine_hint"):
            executor(AuthorEngine(), TaskSpec("parent", "code", "make edits"), ContextAssembly())
        self.assertEqual(runtime.calls, [])

    def test_unknown_authoring_usage_fails_closed_before_runtime(self):
        engine = AuthorEngine(token_usage=None)
        runtime = FakeFactoryRuntime()
        job = self.make_job(engine.engine_id)
        executor = FactoryFixedSwarmExecutor(runtime, lambda _engine, _task, _context: job)
        with self.assertRaisesRegex(FactoryAssuranceError, "usage is unknown"):
            executor(engine, TaskSpec("parent", "code", "make edits"), ContextAssembly())
        self.assertEqual(runtime.calls, [])

    def test_fenced_worker_source_is_not_silently_reinterpreted(self):
        class FencedEngine(AuthorEngine):
            def execute(self, task, context):
                return EngineResult(candidate="```python\nwrite_file('x','y')\n```", token_usage=1)

        engine = FencedEngine()
        runtime = FakeFactoryRuntime()
        job = self.make_job(engine.engine_id)
        executor = FactoryFixedSwarmExecutor(runtime, lambda _engine, _task, _context: job)
        with self.assertRaisesRegex(FactoryAssuranceError, "fenced"):
            executor(engine, TaskSpec("parent", "code", "make edits"), ContextAssembly())
        self.assertEqual(runtime.calls, [])


class MarketAttributionTests(unittest.TestCase):
    def runtime_with_engine(self):
        engine = AuthorEngine()
        runtime = AdaptiveAssuranceRuntime()
        runtime.register_engine(engine, MarketProfile(
            engine_id=engine.engine_id,
            capabilities=frozenset({"code"}),
            cost_per_task=0.0,
            latency_ms=1.0,
        ))
        return runtime, engine

    def execute_fixed(self, runtime, metadata):
        runtime.register_strategy_executor(
            ExecutionStrategy.FIXED_SWARM,
            lambda _engine, _task, _context: EngineResult(candidate="ok", raw_metadata=metadata),
        )
        return runtime.execute(
            task=TaskSpec("t", "code", "x"),
            context=ContextAssembly(),
            verifier_id="v",
            verifier=lambda candidate: candidate == "ok",
            assurance=AssuranceClass.ROUTINE,
            required_pass_rate=0.0,
            strategies=(ExecutionStrategy.FIXED_SWARM,),
        )

    def test_non_direct_market_update_requires_explicit_engine_binding(self):
        runtime, engine = self.runtime_with_engine()
        self.execute_fixed(runtime, {})
        self.assertEqual(runtime.market.profiles[engine.engine_id].trials, 0)

        runtime, engine = self.runtime_with_engine()
        self.execute_fixed(runtime, {"engine_attribution": engine.engine_id})
        self.assertEqual(runtime.market.profiles[engine.engine_id].trials, 1)


if __name__ == "__main__":
    unittest.main()
