"""Paper-facing containment receipts against the real Linux M2 runtime."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from residual.factory import ExecutionPlan, FactoryTask, FrozenPlan, Requirement
from residual.factory.reliability_experiments import (
    M2_FAULTS,
    M2FaultSpec,
    run_m2_fault_trial,
    summarize_m2_fault_trials,
)
from residual.factory.runtime import FactoryRuntime
from residual.factory.runtime_journal import RuntimeJournal
from residual.factory.runtime_workspace import git
from residual.factory.worker_contract import WorkerContract, WorkerContractError

ROOT = Path(__file__).resolve().parents[1]


class M2ReliabilityExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform != "linux":
            raise unittest.SkipTest("real M2 runtime requires Linux")
        probe_input = json.dumps({"source": "pass"}) + "\n" + '{"sequence":1,"ok":true}\n'
        probe = subprocess.run(
            [sys.executable, "-I", "-S", str(ROOT / "residual/factory/_sandbox_child.py"),
             "128", "3", str(os.getpid())],
            input=probe_input.encode(), capture_output=True, timeout=5,
            env={"PATH": "/usr/bin:/bin"},
        )
        if probe.returncode != 0 or b"SandboxReady" not in probe.stdout:
            if os.environ.get("RESIDUAL_REQUIRE_SECCOMP") == "1":
                raise AssertionError("required real seccomp backend unavailable")
            raise unittest.SkipTest("real seccomp backend unavailable")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init")
        (self.repo / "input.txt").write_text("hello")
        (self.repo / "secret.txt").write_text("must remain unchanged")
        git(self.repo, "add", ".")
        git(self.repo, "-c", "user.name=fixture", "-c", "user.email=fixture@localhost",
            "commit", "-m", "base")
        self.commit = git(self.repo, "rev-parse", "HEAD").decode().strip()
        self.plan = ExecutionPlan(
            "controlled M2 containment",
            (Requirement("R1", "produce bounded candidate", ("unit",)),),
            (FactoryTask("task1", "bounded worker", ("R1",), swarm="swarm1"),),
        )
        self.approval = FrozenPlan.approve(self.plan, "reliability-test-operator")
        self.journal = RuntimeJournal(self.root / "state" / "run.db", trace_id="m2-reliability")
        self.runtime = FactoryRuntime(
            self.repo, self.root / "work", self.journal, allow_local_worker_code=True
        )
        self.counter = 0

    def contract(self, **overrides):
        self.counter += 1
        i = self.counter
        data = dict(
            task_id="task1", worker_id=f"worker{i}", swarm_id="swarm1",
            execution_plan_hash=self.plan.graph_hash, attempt_id=f"attempt{i}",
            lease_id=f"lease{i}", lease_generation=i, input_commit=self.commit,
            workspace_root=str(self.root / "work" / "swarm1" / f"attempt{i}"),
            inputs=("input.txt",), allowed_outputs=("output.txt",), forbidden=("secret.txt",),
            requirements=("R1",), acceptance=("unit",), dependencies=(),
            allowed_tools=("read_file", "write_file", "delete_file"), forbidden_tools=("shell",),
            token_budget=0, wall_clock_budget_s=5, max_tool_calls=10,
            max_file_writes=5, memory_limit_mb=128,
        )
        data.update(overrides)
        return WorkerContract(**data)

    def run_fault(self, kind):
        overrides = {"wall_clock_budget_s": 0.2} if kind == "wall_clock_exhaustion" else {}
        contract = self.contract(**overrides)
        receipt = run_m2_fault_trial(
            self.runtime, self.plan, self.approval, contract, M2FaultSpec(f"trial-{kind}", kind)
        )
        return contract, receipt

    def test_all_declared_m2_faults_hit_real_boundaries_and_are_contained(self):
        receipts = []
        for kind in sorted(M2_FAULTS):
            with self.subTest(kind=kind):
                contract, receipt = self.run_fault(kind)
                self.assertTrue(receipt["injection_observed"], receipt)
                self.assertTrue(receipt["fault_detected"], receipt)
                self.assertTrue(receipt["fault_contained"], receipt)
                self.assertFalse(receipt["candidate_published"], receipt)
                self.assertTrue(receipt["process_reaped"], receipt)
                self.assertEqual(receipt["runtime_status"], "VIOLATED", receipt)
                self.assertFalse(Path(contract.workspace_root).exists())
                receipts.append(receipt)
        self.assertEqual((self.repo / "secret.txt").read_text(), "must remain unchanged")
        report = summarize_m2_fault_trials(receipts)
        self.assertEqual(report["trials"], len(M2_FAULTS))
        self.assertEqual(report["failure_containment_rate"], 1.0)
        self.assertEqual(report["detection_rate"], 1.0)
        self.assertEqual(set(report["by_fault_kind"]), set(M2_FAULTS))

    def test_forbidden_write_preserves_source_repository(self):
        _, receipt = self.run_fault("forbidden_filesystem_write")
        self.assertTrue(receipt["fault_contained"])
        self.assertEqual((self.repo / "secret.txt").read_text(), "must remain unchanged")
        self.assertEqual(git(self.repo, "rev-parse", "HEAD").decode().strip(), self.commit)

    def test_kernel_syscall_fault_requires_sigsys_evidence(self):
        _, receipt = self.run_fault("raw_filesystem_syscall")
        self.assertEqual(receipt["runtime_reason"], "os_syscall_allowlist")
        self.assertLess(receipt["returncode"], 0)
        self.assertEqual(receipt["violation_boundary"], "tool")

    def test_unknown_fault_is_rejected(self):
        with self.assertRaises(WorkerContractError):
            M2FaultSpec("bad", "not-real")

    def test_aggregate_fails_closed_when_injection_not_observed(self):
        _, receipt = self.run_fault("forbidden_tool")
        bad = dict(receipt)
        bad["injection_observed"] = False
        with self.assertRaises(WorkerContractError):
            summarize_m2_fault_trials([bad])


if __name__ == "__main__":
    unittest.main()
