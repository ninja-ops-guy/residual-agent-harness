"""Controlled fault trials against the canonical M4 deterministic integrator."""
from __future__ import annotations

import dataclasses
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from residual.core import digest
from .evidence_bus import EvidenceBus, FactoryStationIssuer, StationIdentity, VerificationDecision
from .evidence_receipts import EvidenceError
from .integrator import DeterministicIntegrator, HumanResolution, IntegrationError, VerificationCommand
from .runtime import RuntimeResult
from .runtime_workspace import CandidateTree
from .worker_contract import WorkerContract

M4_FAULTS = {
    "input_order_permutation": "deterministic_ordering",
    "missing_parent": "topological_admission",
    "true_overlap_conflict": "conflict_gate",
    "verification_failure": "accumulated_verification",
    "invalid_human_resolution": "hitl_resolution_gate",
    "integration_receipt_tamper": "integration_signature",
}


class _Fixture:
    def __init__(self, root: Path):
        self.root = root
        self.repo = root / "repo"
        self.repo.mkdir()
        subprocess.check_call(["git", "-C", str(self.repo), "init", "-q"])
        subprocess.check_call(["git", "-C", str(self.repo), "config", "user.email", "fault@example.com"])
        subprocess.check_call(["git", "-C", str(self.repo), "config", "user.name", "Fault Matrix"])
        (self.repo / "base.txt").write_text("base\n")
        subprocess.check_call(["git", "-C", str(self.repo), "add", "."])
        subprocess.check_call(["git", "-C", str(self.repo), "commit", "-qm", "base"])
        self.base = subprocess.check_output(["git", "-C", str(self.repo), "rev-parse", "HEAD"]).decode().strip()
        self.identity = StationIdentity.generate()
        self.bus = EvidenceBus(root / "bus.sqlite")
        self.issuer = FactoryStationIssuer(self.identity, self.bus)
        self.plan_hash = "a" * 64
        self.events: list[dict[str, Any]] = []
        self.integrator = DeterministicIntegrator(self.repo, self.bus, self.identity, observe=self.events.append)

    def receipt(self, task: str, path: str, data: bytes, *, parents: tuple[str, ...] = ()):
        work = self.root / f"w-{task}"
        work.mkdir()
        target = work / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        sha = hashlib.sha256(data).hexdigest()
        contract = WorkerContract(
            task_id=task, worker_id=f"w{task}", swarm_id="s1",
            execution_plan_hash=self.plan_hash, attempt_id=f"a{task}", lease_id=f"l{task}",
            lease_generation=1, input_commit=self.base, workspace_root=str(work),
            inputs=("base.txt",), allowed_outputs=(path,), forbidden=(),
            requirements=(f"R{task}",), acceptance=("ok",),
            dependencies=tuple(self.bus.get(parent).task_id for parent in parents),
            allowed_tools=("write",), forbidden_tools=(), token_budget=0,
            wall_clock_budget_s=10, max_tool_calls=1, max_file_writes=1, memory_limit_mb=64)
        candidate = CandidateTree(self.base, "d" * 40, "e" * 40, ((path, sha),))
        runtime = RuntimeResult(contract.attempt_id, "CANDIDATE", contract.contract_hash,
                                self.plan_hash, 0, True, {}, candidate,
                                "awaiting_station_verification")
        decision = VerificationDecision(((f"R{task}", True),), (("ok", "pass"),),
                                        "pass", "station:fault-matrix", digest({"v": 1}))
        return self.issuer.issue(contract=contract, result=runtime, workspace_root=work,
                                 decision=decision, parent_receipts=parents)


def _trial(fault: str) -> dict[str, Any]:
    if fault not in M4_FAULTS:
        raise EvidenceError(f"unknown M4 fault: {fault}")
    with tempfile.TemporaryDirectory(prefix="residual-m4-fault-") as directory:
        fx = _Fixture(Path(directory))
        public_key = fx.identity.public_bytes()
        injected = detected = contained = False
        integration_receipt_issued = False
        offender = None
        detail = ""

        if fault == "input_order_permutation":
            a = fx.receipt("t1", "a.txt", b"A\n")
            b = fx.receipt("t2", "b.txt", b"B\n")
            first = fx.integrator.integrate((a.receipt_hash, b.receipt_hash),
                                            station_public_key=public_key, verification=())
            second = fx.integrator.integrate((b.receipt_hash, a.receipt_hash),
                                             station_public_key=public_key, verification=())
            injected = True
            detected = first.status == second.status == "PASS"
            integration_receipt_issued = first.receipt is not None and second.receipt is not None
            contained = detected and integration_receipt_issued and \
                first.receipt.output_commit == second.receipt.output_commit and \
                first.receipt.output_tree == second.receipt.output_tree
            detail = "permuted input order produced identical deterministic output"

        elif fault == "missing_parent":
            parent = fx.receipt("parent", "parent.txt", b"parent\n")
            child = fx.receipt("child", "child.txt", b"child\n", parents=(parent.receipt_hash,))
            injected = True
            try:
                fx.integrator.integrate((child.receipt_hash,), station_public_key=public_key, verification=())
            except IntegrationError:
                detected = contained = True
            detail = "child receipt rejected when parent absent from integration set"

        elif fault == "true_overlap_conflict":
            a = fx.receipt("t1", "x.txt", b"one\n")
            b = fx.receipt("t2", "x.txt", b"two\n")
            injected = True
            result = fx.integrator.integrate((a.receipt_hash, b.receipt_hash),
                                             station_public_key=public_key, verification=())
            detected = result.status == "CONFLICT" and bool(result.conflicts)
            integration_receipt_issued = result.receipt is not None
            contained = detected and not integration_receipt_issued
            detail = "true overlap stopped before IntegrationReceipt publication"

        elif fault == "verification_failure":
            good = fx.receipt("t1", "good.txt", b"ok\n")
            bad = fx.receipt("t2", "bad.txt", b"bad\n")
            command = (VerificationCommand("no-bad", (sys.executable, "-c",
                        "import pathlib,sys; sys.exit(pathlib.Path('bad.txt').exists())")),)
            injected = True
            result = fx.integrator.integrate((good.receipt_hash, bad.receipt_hash),
                                             station_public_key=public_key, verification=command)
            offender = result.offending_receipt
            detected = result.status == "VERIFY_FAILED" and offender == bad.receipt_hash
            integration_receipt_issued = result.receipt is not None
            contained = detected and not integration_receipt_issued
            detail = "accumulated verifier failed and binary search identified offending receipt"

        elif fault == "invalid_human_resolution":
            a = fx.receipt("t1", "x.txt", b"one\n")
            b = fx.receipt("t2", "x.txt", b"two\n")
            injected = True
            try:
                fx.integrator.integrate((a.receipt_hash, b.receipt_hash),
                                        station_public_key=public_key, verification=(),
                                        resolutions={"x.txt": b"not-a-human-resolution"})
            except IntegrationError:
                detected = contained = True
            detail = "unbound conflict content rejected without HumanResolution identity/decision"

        elif fault == "integration_receipt_tamper":
            a = fx.receipt("t1", "a.txt", b"A\n")
            result = fx.integrator.integrate((a.receipt_hash,), station_public_key=public_key, verification=())
            if result.receipt is None:
                raise EvidenceError("control integration did not produce receipt")
            integration_receipt_issued = True
            tampered = dataclasses.replace(result.receipt, output_commit="f" * 40)
            injected = True
            detected = not tampered.verify(public_key)
            contained = detected
            detail = "mutated final output commit invalidated Station signature"

        return {
            "schema_version": "residual.m4-fault-trial.v1",
            "fault": fault,
            "expected_boundary": M4_FAULTS[fault],
            "injection_observed": injected,
            "detected": detected,
            "contained": contained,
            "integration_receipt_issued": integration_receipt_issued,
            "offending_receipt": offender,
            "detail": detail,
        }


def run_m4_fault(fault: str) -> dict[str, Any]:
    return _trial(fault)


def aggregate_m4_faults() -> dict[str, Any]:
    trials = [_trial(name) for name in M4_FAULTS]
    if any(not trial["injection_observed"] for trial in trials):
        raise EvidenceError("M4 experiment contained an unobserved injection")
    contained = sum(bool(trial["contained"]) for trial in trials)
    return {
        "schema_version": "residual.m4-fault-report.v1",
        "faults": len(trials),
        "contained": contained,
        "fcr": contained / len(trials) if trials else 0.0,
        "trials": trials,
        "claim_scope": "canonical M4 deterministic integration and handoff boundaries",
    }
