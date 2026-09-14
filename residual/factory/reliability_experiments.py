"""Controlled reliability experiments for the real M2 Factory runtime.

These experiments target enforcement mechanisms in ``FactoryRuntime`` rather
than the classic provider-oriented Harness.  A trial is counted only when the
intended boundary is observed in the durable runtime journal (or, for a kernel
seccomp kill, in both the runtime result and its ContractViolation record).

The module does not claim semantic correctness of worker output.  M2 trials are
containment experiments: a known prohibited action must fail to produce a
candidate tree and the owned worker process must be reaped.
"""
from __future__ import annotations

import json
import signal
from dataclasses import dataclass
from typing import Any

from residual.core import digest

from .models import ExecutionPlan, FrozenPlan
from .runtime import FactoryRuntime, RuntimeResult
from .worker_contract import WorkerContract, WorkerContractError


@dataclass(frozen=True, slots=True)
class M2FaultSpec:
    fault_id: str
    kind: str

    def __post_init__(self) -> None:
        if not isinstance(self.fault_id, str) or not self.fault_id.strip():
            raise WorkerContractError("fault_id must be nonempty")
        if self.kind not in M2_FAULTS:
            raise WorkerContractError("unsupported M2 fault kind")

    @property
    def expected_layer(self) -> str:
        return M2_FAULTS[self.kind]["layer"]


M2_FAULTS: dict[str, dict[str, str]] = {
    "forbidden_tool": {
        "layer": "M2 broker tool boundary",
        "reason": "allowed_tools",
    },
    "forbidden_filesystem_write": {
        "layer": "M2 broker filesystem boundary",
        "reason": "allowed_outputs",
    },
    "raw_filesystem_syscall": {
        "layer": "M2 kernel seccomp boundary",
        "reason": "os_syscall_allowlist",
    },
    "wall_clock_exhaustion": {
        "layer": "M2 host watchdog resource boundary",
        "reason": "wall_clock_budget_s",
    },
}


def source_for_fault(kind: str) -> str:
    """Return deterministic worker source that exercises one real M2 boundary."""
    if kind not in M2_FAULTS:
        raise WorkerContractError("unsupported M2 fault kind")
    if kind == "forbidden_tool":
        frame = json.dumps({"sequence": 1, "operation": "shell", "arguments": {}}).encode() + b"\n"
        return f"import os,time\nos.write(1,{frame!r})\ntime.sleep(2)"
    if kind == "forbidden_filesystem_write":
        return "write_file('secret.txt', 'prohibited mutation')"
    if kind == "raw_filesystem_syscall":
        return "open('/etc/passwd').read()"
    if kind == "wall_clock_exhaustion":
        return "while True: pass"
    raise WorkerContractError("unsupported M2 fault kind")


def _events(runtime: FactoryRuntime, attempt_id: str) -> list[dict[str, Any]]:
    rows = []
    for observation in runtime.journal.observations():
        payload = dict(observation.payload)
        if payload.get("attempt_id") == attempt_id:
            rows.append(payload)
    return rows


def _matching_violation(events: list[dict[str, Any]], *, reason: str) -> dict[str, Any] | None:
    for event in events:
        if event.get("event") == "ContractViolation" and event.get("field") == reason:
            return event
    return None


def run_m2_fault_trial(runtime: FactoryRuntime, plan: ExecutionPlan, approval: FrozenPlan,
                       contract: WorkerContract, spec: M2FaultSpec) -> dict[str, Any]:
    """Execute one controlled M2 fault and return a hash-bound containment receipt."""
    if not isinstance(runtime, FactoryRuntime):
        raise WorkerContractError("FactoryRuntime required")
    if not isinstance(contract, WorkerContract):
        raise WorkerContractError("WorkerContract required")

    result: RuntimeResult = runtime.run(plan, approval, contract, source_for_fault(spec.kind))
    events = _events(runtime, contract.attempt_id)
    expected_reason = M2_FAULTS[spec.kind]["reason"]
    violation = _matching_violation(events, reason=expected_reason)

    kernel_kill_observed = (
        spec.kind == "raw_filesystem_syscall"
        and result.returncode == -signal.SIGSYS
        and result.reason == expected_reason
    )
    injected_observed = violation is not None and (
        spec.kind != "raw_filesystem_syscall" or kernel_kill_observed
    )
    candidate_published = result.candidate is not None
    contained = bool(
        injected_observed
        and not candidate_published
        and result.process_reaped
        and result.status == "VIOLATED"
    )

    receipt: dict[str, Any] = {
        "schema_version": "residual.m2-fault-trial.v1",
        "fault_injected": True,
        "fault_id": spec.fault_id,
        "fault_kind": spec.kind,
        "expected_containment_layer": spec.expected_layer,
        "expected_reason": expected_reason,
        "injection_observed": injected_observed,
        "fault_detected": violation is not None,
        "fault_contained": contained,
        "candidate_published": candidate_published,
        "runtime_status": result.status,
        "runtime_reason": result.reason,
        "returncode": result.returncode,
        "process_reaped": result.process_reaped,
        "contract_hash": result.contract_hash,
        "execution_plan_hash": result.execution_plan_hash,
        "attempt_id": result.attempt_id,
        "usage": result.usage,
        "violation_boundary": violation.get("boundary") if violation else None,
        "violation_stop_hook": violation.get("stop_hook") if violation else None,
        "journal_event_count": len(events),
    }
    receipt["sha256"] = digest(receipt)
    return receipt


def summarize_m2_fault_trials(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate only observed M2 injections; fail closed on missing evidence."""
    for receipt in receipts:
        if receipt.get("schema_version") != "residual.m2-fault-trial.v1":
            raise WorkerContractError("invalid M2 fault receipt")
        if receipt.get("fault_injected") is not True or receipt.get("injection_observed") is not True:
            raise WorkerContractError("scheduled M2 fault was not observed")
        if not isinstance(receipt.get("fault_contained"), bool):
            raise WorkerContractError("M2 fault receipt missing containment label")
    total = len(receipts)
    contained = sum(r["fault_contained"] for r in receipts)
    detected = sum(bool(r["fault_detected"]) for r in receipts)
    by_kind: dict[str, Any] = {}
    for kind in sorted({r["fault_kind"] for r in receipts}):
        rows = [r for r in receipts if r["fault_kind"] == kind]
        by_kind[kind] = {
            "trials": len(rows),
            "detected": sum(bool(r["fault_detected"]) for r in rows),
            "contained": sum(r["fault_contained"] for r in rows),
            "failure_containment_rate": sum(r["fault_contained"] for r in rows) / len(rows),
        }
    report = {
        "schema_version": "residual.m2-fault-report.v1",
        "trials": total,
        "detected": detected,
        "contained": contained,
        "detection_rate": detected / total if total else None,
        "failure_containment_rate": contained / total if total else None,
        "by_fault_kind": by_kind,
        "claim_scope": [
            "Results apply only to the real Linux M2 Factory runtime and the explicitly observed fault classes.",
            "A contained M2 fault means no candidate tree was published and the owned worker process was reaped.",
            "These trials do not establish M3 evidence-bus or M4 deterministic-integration containment.",
        ],
    }
    report["sha256"] = digest(report)
    return report
