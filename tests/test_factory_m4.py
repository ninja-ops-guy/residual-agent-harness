from __future__ import annotations
import hashlib, subprocess, sys, tempfile, unittest
from pathlib import Path

from residual.core import digest
from residual.factory.evidence_bus import EvidenceBus, FactoryStationIssuer, StationIdentity, VerificationDecision
from residual.factory.integrator import DeterministicIntegrator, HumanResolution, VerificationCommand
from residual.factory.runtime import RuntimeResult
from residual.factory.runtime_workspace import CandidateTree
from residual.factory.scheduler import EngineCapability, FactoryScheduler, SchedulerSnapshot
from residual.factory.worker_contract import WorkerContract
from residual.factory.models import ExecutionPlan, FactoryTask, Requirement


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args]).decode().strip()


class M4Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.check_call(["git", "-C", str(self.repo), "init", "-q"])
        subprocess.check_call(["git", "-C", str(self.repo), "config", "user.email", "t@example.com"])
        subprocess.check_call(["git", "-C", str(self.repo), "config", "user.name", "T"])
        (self.repo / "base.txt").write_text("base\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")
        self.identity = StationIdentity.generate()
        self.bus = EvidenceBus(self.root / "bus.sqlite")
        self.issuer = FactoryStationIssuer(self.identity, self.bus)
        self.plan_hash = "a" * 64

    def tearDown(self):
        self.tmp.cleanup()

    def make_receipt(self, task, path, data, *, parents=()):
        work = self.root / f"w-{task}"
        work.mkdir()
        (work / path).parent.mkdir(parents=True, exist_ok=True)
        (work / path).write_bytes(data)
        sha = hashlib.sha256(data).hexdigest()
        contract = WorkerContract(
            task_id=task, worker_id=f"w{task}", swarm_id="s1",
            execution_plan_hash=self.plan_hash, attempt_id=f"a{task}",
            lease_id=f"l{task}", lease_generation=1, input_commit=self.base,
            workspace_root=str(work), inputs=("base.txt",), allowed_outputs=(path,),
            forbidden=(), requirements=(f"R{task}",), acceptance=("ok",),
            dependencies=tuple(self.bus.get(p).task_id for p in parents),
            allowed_tools=("write",), forbidden_tools=(), token_budget=0,
            wall_clock_budget_s=10, max_tool_calls=1, max_file_writes=1,
            memory_limit_mb=64)
        candidate = CandidateTree(self.base, "d" * 40, "e" * 40, ((path, sha),))
        runtime = RuntimeResult(contract.attempt_id, "CANDIDATE", contract.contract_hash,
                                self.plan_hash, 0, True, {}, candidate,
                                "awaiting_station_verification")
        decision = VerificationDecision(((f"R{task}", True),), (("ok", "pass"),),
                                        "pass", "station:test", digest({"v": 1}))
        return self.issuer.issue(contract=contract, result=runtime, workspace_root=work,
                                 decision=decision, parent_receipts=parents)

    def test_deterministic_integration_and_signature(self):
        r1 = self.make_receipt("t1", "a.txt", b"A\n")
        r2 = self.make_receipt("t2", "b.txt", b"B\n")
        integrator = DeterministicIntegrator(self.repo, self.bus, self.identity)
        command = (VerificationCommand("smoke", (sys.executable, "-c",
                    "import pathlib; assert pathlib.Path('a.txt').read_text()=='A\\n'")),)
        first = integrator.integrate((r2.receipt_hash, r1.receipt_hash),
                                     station_public_key=self.identity.public_bytes(),
                                     verification=command)
        second = integrator.integrate((r1.receipt_hash, r2.receipt_hash),
                                      station_public_key=self.identity.public_bytes(),
                                      verification=command)
        self.assertEqual(first.status, "PASS")
        self.assertEqual(first.receipt.output_commit, second.receipt.output_commit)
        self.assertEqual(first.receipt.output_tree, second.receipt.output_tree)
        self.assertTrue(first.receipt.verify(self.identity.public_bytes()))

    def test_true_overlap_conflict(self):
        r1 = self.make_receipt("t1", "x.txt", b"one\n")
        r2 = self.make_receipt("t2", "x.txt", b"two\n")
        result = DeterministicIntegrator(self.repo, self.bus, self.identity).integrate(
            (r1.receipt_hash, r2.receipt_hash),
            station_public_key=self.identity.public_bytes(), verification=())
        self.assertEqual(result.status, "CONFLICT")
        self.assertEqual(result.conflicts[0].path, "x.txt")

    def test_human_resolution_binds_identity_decision_and_content(self):
        r1 = self.make_receipt("t1", "x.txt", b"one\n")
        r2 = self.make_receipt("t2", "x.txt", b"two\n")
        resolution = HumanResolution(b"human\n", "operator@example", "decision-1")
        result = DeterministicIntegrator(self.repo, self.bus, self.identity).integrate(
            (r1.receipt_hash, r2.receipt_hash), station_public_key=self.identity.public_bytes(),
            verification=(), resolutions={"x.txt": resolution})
        self.assertEqual(result.status, "PASS")
        self.assertIn(("x.txt", hashlib.sha256(b"human\n").hexdigest(),
                       "operator@example", "decision-1"), result.receipt.resolutions)

    def test_verification_failure_identifies_prefix_offender(self):
        r1 = self.make_receipt("t1", "good.txt", b"ok\n")
        r2 = self.make_receipt("t2", "bad.txt", b"bad\n")
        command = (VerificationCommand("no-bad", (sys.executable, "-c",
                    "import pathlib,sys; sys.exit(pathlib.Path('bad.txt').exists())")),)
        result = DeterministicIntegrator(self.repo, self.bus, self.identity).integrate(
            (r1.receipt_hash, r2.receipt_hash), station_public_key=self.identity.public_bytes(),
            verification=command)
        self.assertEqual(result.status, "VERIFY_FAILED")
        self.assertEqual(result.offending_receipt, r2.receipt_hash)

    def test_scheduler_ready_resize_engine_and_replan(self):
        reqs = tuple(Requirement(f"R{i}", f"r{i}", (f"c{i}",), ()) for i in range(12))
        tasks = [FactoryTask("root", "root", ("R0",), ())]
        tasks += [FactoryTask(f"t{i}", f"t{i}", (f"R{i}",), ("root",)) for i in range(1, 12)]
        plan = ExecutionPlan("x", reqs, tuple(tasks))
        events = []
        scheduler = FactoryScheduler(observe=events.append)
        self.assertEqual(scheduler.ready(plan, set()), ("root",))
        self.assertGreater(scheduler.independence_fraction(plan, set()), 0)
        engine = scheduler.select_engine(
            {"code"},
            (EngineCapability("cloud", "c", "cloud", frozenset({"code"}), 1),
             EngineCapability("local", "l", "local", frozenset({"code"}), 5)))
        self.assertEqual(engine.name, "local")
        decision = scheduler.resize(SchedulerSnapshot(10, 8, 1, 2, 2, 0, 0))
        self.assertEqual(decision.action, "add_worker")
        self.assertIsNotNone(scheduler.structural_replan(plan, "root", 3))
        self.assertTrue(events)


if __name__ == "__main__":
    unittest.main()
