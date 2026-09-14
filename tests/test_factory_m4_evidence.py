from __future__ import annotations

import hashlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from residual.core import digest
from residual.factory.evidence_bus import EvidenceBus, EvidenceError
from residual.factory.evidence_receipts import StationIdentity, VerificationDecision
from residual.factory.m4_evidence import M4EvidenceError, ReceiptBackedM4
from residual.factory.models import ExecutionPlan, FactoryTask, Requirement
from residual.factory.runtime import RuntimeResult
from residual.factory.runtime_workspace import CandidateTree
from residual.factory.station_issuer import FactoryStationIssuer
from residual.factory.worker_contract import WorkerContract


class M4EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plan = ExecutionPlan(
            "m4 evidence test",
            (
                Requirement("R1", "first", ("unit",)),
                Requirement("R2", "second", ("unit",), depends_on=("R1",)),
                Requirement("R3", "parallel", ("unit",)),
            ),
            (
                FactoryTask("task1", "first", ("R1",)),
                FactoryTask("task2", "second", ("R2",), depends_on=("task1",)),
                FactoryTask("task3", "parallel", ("R3",)),
            ),
        )
        self.identity = StationIdentity.generate()
        self.bus = EvidenceBus(self.root / "bus.sqlite")
        self.issuer = FactoryStationIssuer(self.identity, self.bus)
        self.events = []
        self.m4 = ReceiptBackedM4(
            self.plan,
            self.bus,
            station_public_key=self.identity.public_bytes(),
            observe=self.events.append,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def pair(self, task_id: str, requirement: str, *, path: str, data: bytes, index: int):
        workspace = self.root / f"ws-{task_id}-{index}"
        workspace.mkdir()
        (workspace / path).parent.mkdir(parents=True, exist_ok=True)
        (workspace / path).write_bytes(data)
        contract = WorkerContract(
            task_id=task_id,
            worker_id=f"worker{index}",
            swarm_id="swarm1",
            execution_plan_hash=self.plan.graph_hash,
            attempt_id=f"attempt{index}",
            lease_id=f"lease{index}",
            lease_generation=index,
            input_commit="a" * 40,
            workspace_root=str(workspace),
            inputs=(),
            allowed_outputs=(path,),
            forbidden=(),
            requirements=(requirement,),
            acceptance=("unit",),
            dependencies=tuple(self.plan.tasks[[t.id for t in self.plan.tasks].index(task_id)].depends_on),
            allowed_tools=("write_file",),
            forbidden_tools=(),
            token_budget=10,
            wall_clock_budget_s=5,
            max_tool_calls=2,
            max_file_writes=1,
            memory_limit_mb=64,
        )
        sha = hashlib.sha256(data).hexdigest()
        candidate = CandidateTree(contract.input_commit, "b" * 40, "c" * 40, ((path, sha),))
        result = RuntimeResult(
            contract.attempt_id,
            "CANDIDATE",
            contract.contract_hash,
            self.plan.graph_hash,
            0,
            True,
            {},
            candidate,
            "awaiting_station_verification",
        )
        decision = VerificationDecision(
            ((requirement, True),),
            (("unit", "pass"),),
            "pass",
            "station:test",
            digest({"verifier": 1}),
        )
        return contract, result, workspace, decision

    def issue(self, task_id, requirement, *, path, data, index, parents=()):
        contract, result, workspace, decision = self.pair(
            task_id, requirement, path=path, data=data, index=index,
        )
        return self.issuer.issue(
            contract=contract,
            result=result,
            workspace_root=workspace,
            decision=decision,
            parent_receipts=tuple(parents),
        )

    def test_ready_dag_consumes_only_signed_receipts(self):
        r1 = self.issue("task1", "R1", path="one.txt", data=b"one", index=1)
        snapshot = self.m4.ready_dag((r1.receipt_hash,))
        self.assertEqual(snapshot.completed_tasks, ("task1",))
        self.assertEqual(snapshot.ready_tasks, ("task2", "task3"))
        self.assertEqual(snapshot.blocked_tasks, ())
        self.assertEqual(snapshot.independence_fraction, 1.0)
        self.assertTrue(any(e["event"] == "M4SchedulerSnapshot" for e in self.events))

        other = StationIdentity.generate()
        bad = ReceiptBackedM4(self.plan, self.bus, station_public_key=other.public_bytes())
        with self.assertRaises(EvidenceError):
            bad.ready_dag((r1.receipt_hash,))

    def test_dependency_order_and_parent_bindings_are_enforced(self):
        r1 = self.issue("task1", "R1", path="one.txt", data=b"one", index=1)
        r2 = self.issue("task2", "R2", path="two.txt", data=b"two", index=2, parents=(r1.receipt_hash,))
        plan = self.m4.integration_plan((r2.receipt_hash, r1.receipt_hash))
        self.assertEqual(plan.ordered_task_ids, ("task1", "task2"))
        self.assertTrue(plan.integration_eligible)

        r3 = self.issue("task3", "R3", path="three.txt", data=b"three", index=3)
        with self.assertRaisesRegex(M4EvidenceError, "parent bindings"):
            # task2 depends on task1; task3 cannot stand in for that dependency.
            self.m4.integration_plan((r1.receipt_hash, r3.receipt_hash, r2.receipt_hash))

    def test_missing_dependency_receipt_is_rejected(self):
        r1 = self.issue("task1", "R1", path="one.txt", data=b"one", index=1)
        r2 = self.issue("task2", "R2", path="two.txt", data=b"two", index=2, parents=(r1.receipt_hash,))
        with self.assertRaisesRegex(M4EvidenceError, "omits task dependencies"):
            self.m4.integration_plan((r2.receipt_hash,))

    def test_identical_overlap_is_deduplicated_deterministically(self):
        r1 = self.issue("task1", "R1", path="shared.txt", data=b"same", index=1)
        r3 = self.issue("task3", "R3", path="shared.txt", data=b"same", index=3)
        a = self.m4.integration_plan((r1.receipt_hash, r3.receipt_hash))
        b = self.m4.integration_plan((r3.receipt_hash, r1.receipt_hash))
        self.assertTrue(a.integration_eligible)
        self.assertEqual(a.plan_hash, b.plan_hash)
        self.assertEqual(len(a.artifacts), 1)
        self.assertEqual(a.artifacts[0].source_receipt_hashes, (r1.receipt_hash, r3.receipt_hash))

    def test_nonidentical_overlap_becomes_hitl_conflict(self):
        r1 = self.issue("task1", "R1", path="shared.txt", data=b"left", index=1)
        r3 = self.issue("task3", "R3", path="shared.txt", data=b"right", index=3)
        plan = self.m4.integration_plan((r3.receipt_hash, r1.receipt_hash))
        self.assertFalse(plan.integration_eligible)
        self.assertEqual([c.path for c in plan.conflicts], ["shared.txt"])
        conflict_events = [e for e in self.events if e["event"] == "M4IntegrationConflict"]
        self.assertEqual(conflict_events[-1]["action"], "hitl_required")

    def test_stale_receipt_rejected_without_human_approval(self):
        r1 = self.issue("task1", "R1", path="one.txt", data=b"one", index=1)
        contract, result, workspace, decision = self.pair(
            "task1", "R1", path="one.txt", data=b"new", index=4,
        )
        replacement = self.issuer.issue(
            contract=contract,
            result=result,
            workspace_root=workspace,
            decision=decision,
            supersedes=r1.receipt_hash,
        )
        self.assertNotEqual(replacement.receipt_hash, r1.receipt_hash)
        with self.assertRaises(EvidenceError):
            self.m4.ready_dag((r1.receipt_hash,))
        self.bus.approve_stale(r1.receipt_hash, approved_by="human", reason="audit integration")
        self.assertEqual(self.m4.ready_dag((r1.receipt_hash,)).completed_tasks, ("task1",))


if __name__ == "__main__":
    unittest.main()
