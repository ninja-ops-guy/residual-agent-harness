from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

from residual.core import digest
from residual.factory.evidence_bus import EvidenceBus
from residual.factory.evidence_receipts import StationIdentity, VerificationDecision
from residual.factory.m4_evidence import ReceiptBackedM4
from residual.factory.m4_integrator import (
    ConflictResolution,
    DeterministicIntegrator,
    IntegrationConflictError,
    ProjectVerificationError,
    ProjectVerificationPolicy,
    VerificationCommand,
)
from residual.factory.models import ExecutionPlan, FactoryTask, Requirement
from residual.factory.runtime import RuntimeResult
from residual.factory.runtime_workspace import CandidateTree, git
from residual.factory.station_issuer import FactoryStationIssuer
from residual.factory.worker_contract import WorkerContract


class M4IntegratorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init")
        (self.repo / "shared.txt").write_text("a\nb\nc\")
        (self.repo / "base.txt").write_text("base\n")
        git(self.repo, "add", ".")
        git(self.repo, "-c", "user.name=test", "-c", "user.email=test@localhost",
            "commit", "-m", "base")
        self.base = git(self.repo, "rev-parse", "HEAD").decode().strip()
        self.plan = ExecutionPlan(
            "m4 integration",
            (
                Requirement("R1", "first", ("unit",)),
                Requirement("R2", "second", ("unit",)),
                Requirement("R3", "third", ("unit",)),
            ),
            (
                FactoryTask("task1", "first", ("R1",)),
                FactoryTask("task2", "second", ("R2",)),
                FactoryTask("task3", "third", ("R3",)),
            ),
        )
        self.identity = StationIdentity.generate()
        self.bus = EvidenceBus(self.root / "bus.sqlite")
        self.issuer = FactoryStationIssuer(self.identity, self.bus)
        self.m4 = ReceiptBackedM4(
            self.plan, self.bus, station_public_key=self.identity.public_bytes()
        )
        self.events: list[dict] = []
        self.integrator = DeterministicIntegrator(
            self.repo,
            self.root / "integration",
            self.bus,
            station_public_key=self.identity.public_bytes(),
            observe=self.events.append,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def issue(self, task_id: str, requirement: str, *, artifacts: dict[str, bytes | None], index: int,
              parents=()):
        workspace = self.root / f"candidate-{index}"
        workspace.mkdir()
        candidate_artifacts = []
        allowed = []
        for path, data in artifacts.items():
            allowed.append(path)
            target = workspace / path
            if data is None:
                candidate_artifacts.append((path, None))
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            candidate_artifacts.append((path, hashlib.sha256(data).hexdigest()))
        contract = WorkerContract(
            task_id=task_id,
            worker_id=f"worker{index}",
            swarm_id="swarm1",
            execution_plan_hash=self.plan.graph_hash,
            attempt_id=f"attempt{index}",
            lease_id=f"lease{index}",
            lease_generation=index,
            input_commit=self.base,
            workspace_root=str(workspace),
            inputs=(),
            allowed_outputs=tuple(allowed),
            forbidden=(),
            requirements=(requirement,),
            acceptance=("unit",),
            dependencies=(),
            allowed_tools=("write_file",),
            forbidden_tools=(),
            token_budget=10,
            wall_clock_budget_s=5,
            max_tool_calls=5,
            max_file_writes=5,
            memory_limit_mb=64,
        )
        candidate = CandidateTree(
            self.base,
            hashlib.sha1(f"output-{index}".encode()).hexdigest(),
            hashlib.sha1(f"tree-{index}".encode()).hexdigest(),
            tuple(candidate_artifacts),
        )
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
            digest({"verifier": index}),
        )
        return self.issuer.issue(
            contract=contract,
            result=result,
            workspace_root=workspace,
            decision=decision,
            parent_receipts=tuple(parents),
        )

    def policy(self, *, fail_on_bad: bool = False) -> ProjectVerificationPolicy:
        exe = sys.executable
        test_code = (
            "import pathlib,sys; sys.exit(1 if pathlib.Path('bad.txt').exists() else 0)"
            if fail_on_bad else "raise SystemExit(0)"
        )
        return ProjectVerificationPolicy((
            VerificationCommand("tests", "full_test_suite", (exe, "-c", test_code)),
            VerificationCommand("types", "type_check", (exe, "-c", "raise SystemExit(0)")),
            VerificationCommand("contracts", "contract_validation", (exe, "-c", "raise SystemExit(0)")),
        ))

    def test_deterministic_commit_and_signed_receipt(self):
        r1 = self.issue("task1", "R1", artifacts={"one.txt": b"one\n"}, index=1)
        r2 = self.issue("task2", "R2", artifacts={"two.txt": b"two\n"}, index=2)
        plan_a = self.m4.integration_plan((r2.receipt_hash, r1.receipt_hash))
        plan_b = self.m4.integration_plan((r1.receipt_hash, r2.receipt_hash))
        self.assertEqual(plan_a.plan_hash, plan_b.plan_hash)

        first = self.integrator.integrate(plan_a, policy=self.policy(), station_identity=self.identity)
        second = self.integrator.integrate(plan_b, policy=self.policy(), station_identity=self.identity)
        self.assertEqual(first.receipt.output_commit, second.receipt.output_commit)
        self.assertEqual(first.output_tree, second.output_tree)
        self.assertTrue(first.receipt.verify_signature(self.identity.public_bytes()))
        self.assertEqual(first.receipt.input_receipt_hashes, plan_a.ordered_receipt_hashes)
        self.assertTrue(any(e["event"] == "IntegrationReceiptIssued" for e in self.events))

    def test_subset_overlap_keeps_superset_without_hitl(self):
        smaller = self.issue(
            "task1", "R1", artifacts={"shared.txt": b"A\nb\nc\n"}, index=1
        )
        larger = self.issue(
            "task3", "R3", artifacts={"shared.txt": b"A\nb\nC\n"}, index=3
        )
        plan = self.m4.integration_plan((smaller.receipt_hash, larger.receipt_hash))
        outcome = self.integrator.integrate(plan, policy=self.policy(), station_identity=self.identity)
        blob = git(self.repo, "show", f"{outcome.receipt.output_commit}:shared.txt")
        self.assertEqual(blob, b"A\nb\nC\n")
        self.assertEqual(outcome.receipt.conflict_resolutions, ())

    def test_true_conflict_requires_and_binds_hitl_resolution(self):
        left = self.issue("task1", "R1", artifacts={"shared.txt": b"LEFT\nb\nc\n"}, index=1)
        right = self.issue("task3", "R3", artifacts={"shared.txt": b"RIGHT\nb\nc\n"}, index=3)
        plan = self.m4.integration_plan((left.receipt_hash, right.receipt_hash))
        with self.assertRaises(IntegrationConflictError):
            self.integrator.integrate(plan, policy=self.policy(), station_identity=self.identity)
        resolution = ConflictResolution("shared.txt", right.receipt_hash, "operator", "choose reviewed branch")
        outcome = self.integrator.integrate(
            plan, policy=self.policy(), station_identity=self.identity, resolutions=(resolution,)
        )
        self.assertEqual(outcome.receipt.conflict_resolutions, (resolution,))
        self.assertEqual(git(self.repo, "show", f"{outcome.receipt.output_commit}:shared.txt"),
                         b"RIGHT\nb\nc\n")
        self.assertTrue(any(e["event"] == "M4ConflictResolved" for e in self.events))

    def test_failed_project_verification_attributes_receipt_and_replans(self):
        good1 = self.issue("task1", "R1", artifacts={"one.txt": b"one\n"}, index=1)
        bad = self.issue("task2", "R2", artifacts={"bad.txt": b"bad\n"}, index=2)
        good3 = self.issue("task3", "R3", artifacts={"three.txt": b"three\n"}, index=3)
        plan = self.m4.integration_plan((good1.receipt_hash, bad.receipt_hash, good3.receipt_hash))
        with self.assertRaises(ProjectVerificationError) as caught:
            self.integrator.integrate(plan, policy=self.policy(fail_on_bad=True), station_identity=self.identity)
        self.assertEqual(caught.exception.offending_receipt_hash, bad.receipt_hash)
        revision = [e for e in self.events if e["event"] == "M4ReceiptRevisionRequired"]
        self.assertEqual(revision[-1]["receipt_hash"], bad.receipt_hash)
        self.assertEqual(revision[-1]["action"], "replan")

    def test_secops_policy_requires_security_scan(self):
        exe = sys.executable
        with self.assertRaisesRegex(Exception, "security_scan"):
            ProjectVerificationPolicy((
                VerificationCommand("tests", "full_test_suite", (exe, "-c", "pass")),
                VerificationCommand("types", "type_check", (exe, "-c", "pass")),
                VerificationCommand("contracts", "contract_validation", (exe, "-c", "pass")),
            ), secops_active=True)


if __name__ == "__main__":
    unittest.main()
