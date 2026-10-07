from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from residual.assurance.factory_adapter import (
    FactoryAssuranceError,
    FactoryFixedSwarmJob,
    FactoryWorkerTemplate,
)
from residual.assurance.factory_admission import FactoryM3Admission
from residual.assurance.factory_dynamic import (
    DynamicWaveDecision,
    FactoryDynamicSwarmExecutor,
    FactoryDynamicSwarmJob,
)
from residual.core import digest
from residual.engines.protocol import ContextAssembly, EngineHealth, EngineResult, TaskSpec
from residual.factory.evidence_bus import EvidenceBus
from residual.factory.evidence_receipts import StationIdentity, VerificationDecision
from residual.factory.models import ExecutionPlan, FactoryTask, FrozenPlan, Requirement
from residual.factory.runtime import FactoryRuntime, RuntimeResult
from residual.factory.runtime_workspace import CandidateTree
from residual.factory.station_issuer import FactoryStationIssuer
from residual.factory.worker_contract import WorkerContract


class AuthorEngine:
    name = "author"
    version = "v1"
    capability_class = "test"
    locality = "local"

    def __init__(self):
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
        return EngineResult(candidate=f"write_file('out-{worker}.txt', 'ok')", token_usage=3)

    def normalize(self, raw_output):
        return raw_output if isinstance(raw_output, EngineResult) else EngineResult(candidate=raw_output)


class FakeFactoryRuntime(FactoryRuntime):
    def __init__(self):
        self.waves = []

    def run_many(self, plan, approval, workers, *, capacity=2):
        self.waves.append((tuple(c.attempt_id for c, _ in workers), capacity))
        rows = []
        for contract, _source in workers:
            candidate = CandidateTree(
                contract.input_commit,
                "b" * 40,
                "c" * 40,
                ((f"out-{contract.worker_id}.txt", "d" * 64),),
            )
            rows.append(RuntimeResult(
                contract.attempt_id,
                "CANDIDATE",
                contract.contract_hash,
                plan.graph_hash,
                0,
                True,
                {"tool_calls": 1, "file_writes": 1, "tokens": 0},
                candidate,
                "awaiting_station_verification",
            ))
        return rows


class FakeAdmission:
    def __init__(self):
        self.calls = []

    def admit(self, contracts, results):
        self.calls.append((tuple(contracts), tuple(results)))
        return type("Admission", (), {"receipt_hashes": tuple("e" * 64 for _ in contracts)})()


class DynamicFactoryTests(unittest.TestCase):
    def make_job(self):
        requirements = tuple(Requirement(f"R{i}", f"req {i}", ("unit",)) for i in range(1, 4))
        tasks = tuple(FactoryTask(f"task{i}", f"task {i}", (f"R{i}",), swarm="swarm1") for i in range(1, 4))
        plan = ExecutionPlan("adaptive waves", requirements, tasks)
        approval = FrozenPlan.approve(plan, "test-operator")
        workers = []
        for i in range(1, 4):
            contract = WorkerContract(
                task_id=f"task{i}", worker_id=f"worker{i}", swarm_id="swarm1",
                execution_plan_hash=plan.graph_hash, attempt_id=f"attempt{i}",
                lease_id=f"lease{i}", lease_generation=i, input_commit="a" * 40,
                workspace_root=f"/runtime/swarm1/attempt{i}", inputs=(),
                allowed_outputs=(f"out-worker{i}.txt",), forbidden=("secret.txt",),
                requirements=(f"R{i}",), acceptance=("unit",), dependencies=(),
                allowed_tools=("write_file",), forbidden_tools=("shell",), token_budget=10,
                wall_clock_budget_s=5, max_tool_calls=3, max_file_writes=2, memory_limit_mb=128,
                engine_hint="author@v1",
            )
            workers.append(FactoryWorkerTemplate(contract, f"write output {i}"))
        base = FactoryFixedSwarmJob(plan, approval, tuple(workers), capacity=3)

        def policy(remaining, completed):
            if not completed:
                return DynamicWaveDecision(1, 1)
            return DynamicWaveDecision(len(remaining), min(2, len(remaining)))

        return FactoryDynamicSwarmJob(base, policy)

    def test_dynamic_swarm_changes_wave_size_and_capacity_after_feedback(self):
        engine = AuthorEngine()
        runtime = FakeFactoryRuntime()
        job = self.make_job()
        executor = FactoryDynamicSwarmExecutor(runtime, lambda *_: job)
        result = executor(engine, TaskSpec("parent", "code", "make changes"), ContextAssembly())

        self.assertEqual(runtime.waves, [(('attempt1',), 1), (('attempt2', 'attempt3'), 2)])
        self.assertEqual(result.token_usage, 9)
        self.assertEqual(result.raw_metadata["factory_profile"], "dynamic-swarm-v1")
        self.assertEqual([w["capacity"] for w in result.raw_metadata["factory_waves"]], [1, 2])
        self.assertEqual(result.raw_metadata["candidate_state"], "quarantined")
        self.assertFalse(result.raw_metadata["station_receipt_issued"])

    def test_dynamic_swarm_can_admit_all_workers_to_m3(self):
        engine = AuthorEngine()
        runtime = FakeFactoryRuntime()
        admission = FakeAdmission()
        job = self.make_job()
        executor = FactoryDynamicSwarmExecutor(runtime, lambda *_: job, admission=admission)
        result = executor(engine, TaskSpec("parent", "code", "make changes"), ContextAssembly())

        self.assertEqual(len(admission.calls), 1)
        self.assertEqual(len(admission.calls[0][0]), 3)
        self.assertTrue(result.raw_metadata["station_receipt_issued"])
        self.assertEqual(result.raw_metadata["candidate_state"], "m3-admitted")
        self.assertEqual(len(result.raw_metadata["station_receipt_hashes"]), 3)

    def test_invalid_dynamic_decision_fails_before_next_wave(self):
        engine = AuthorEngine()
        runtime = FakeFactoryRuntime()
        base = self.make_job().base
        job = FactoryDynamicSwarmJob(base, lambda remaining, completed: DynamicWaveDecision(len(remaining) + 1, 1))
        executor = FactoryDynamicSwarmExecutor(runtime, lambda *_: job)
        with self.assertRaisesRegex(FactoryAssuranceError, "batch_size exceeds"):
            executor(engine, TaskSpec("parent", "code", "x"), ContextAssembly())
        self.assertEqual(runtime.waves, [])


class PurgeRecorder:
    def __init__(self):
        self.purged = []

    def purge(self, contract):
        self.purged.append(contract.attempt_id)


class M3AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.identity = StationIdentity.generate()
        self.bus = EvidenceBus(self.root / "bus.sqlite")
        self.issuer = FactoryStationIssuer(self.identity, self.bus)
        self.runtime = PurgeRecorder()

    def tearDown(self):
        self.tmp.cleanup()

    def make_pair(self, index):
        workspace = self.root / f"workspace{index}"
        workspace.mkdir()
        output = f"out{index}.txt"
        data = f"hello-{index}".encode()
        (workspace / output).write_bytes(data)
        contract = WorkerContract(
            task_id=f"task{index}", worker_id=f"worker{index}", swarm_id="swarm1",
            execution_plan_hash="f" * 64, attempt_id=f"attempt{index}", lease_id=f"lease{index}",
            lease_generation=index, input_commit="a" * 40, workspace_root=str(workspace), inputs=(),
            allowed_outputs=(output,), forbidden=(), requirements=(f"REQ{index}",),
            acceptance=("unit",), dependencies=(), allowed_tools=("write_file",), forbidden_tools=(),
            token_budget=10, wall_clock_budget_s=5, max_tool_calls=2, max_file_writes=1, memory_limit_mb=64,
        )
        candidate = CandidateTree(
            contract.input_commit, "b" * 40, "c" * 40,
            ((output, hashlib.sha256(data).hexdigest()),),
        )
        result = RuntimeResult(
            contract.attempt_id, "CANDIDATE", contract.contract_hash, contract.execution_plan_hash,
            0, True, {}, candidate, "awaiting_station_verification",
        )
        return contract, result

    def decision(self, contract, result):
        return VerificationDecision(
            ((contract.requirements[0], True),),
            (("unit", "pass"),),
            "pass",
            "station:test",
            digest({"verifier": 1}),
        )

    def test_m3_admission_issues_signed_receipts_then_purges(self):
        pairs = [self.make_pair(1), self.make_pair(2)]
        contracts = tuple(pair[0] for pair in pairs)
        results = tuple(pair[1] for pair in pairs)
        admission = FactoryM3Admission(self.runtime, self.issuer, self.decision)
        admitted = admission.admit(contracts, results)

        self.assertEqual(len(admitted.receipts), 2)
        self.assertEqual(self.runtime.purged, ["attempt1", "attempt2"])
        for receipt in admitted.receipts:
            self.assertTrue(StationIdentity.verify(receipt, self.identity.public_bytes()))
            self.assertEqual(self.bus.consumable(
                receipt.receipt_hash,
                station_public_key=self.identity.public_bytes(),
            ).receipt_hash, receipt.receipt_hash)
        self.assertEqual(self.bus.verify_queue()["receipts"], 2)

    def test_m3_rejects_incomplete_result_set_before_issuing(self):
        c1, r1 = self.make_pair(1)
        c2, _ = self.make_pair(2)
        admission = FactoryM3Admission(self.runtime, self.issuer, self.decision)
        with self.assertRaisesRegex(FactoryAssuranceError, "result set differs"):
            admission.admit((c1, c2), (r1,))
        self.assertEqual(self.bus.verify_queue()["receipts"], 0)
        self.assertEqual(self.runtime.purged, [])


if __name__ == "__main__":
    unittest.main()
