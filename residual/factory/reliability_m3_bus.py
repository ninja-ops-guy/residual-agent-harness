"""Controlled M3 Evidence Bus fault trials for paper-facing containment metrics."""
from __future__ import annotations

import dataclasses
import sqlite3
import tempfile
import time
from hashlib import sha256
from pathlib import Path
from typing import Any

from residual.core import canonical, strict_json
from .evidence_bus import EvidenceBus
from .evidence_receipts import ArtifactBinding, EvidenceError, StationIdentity, WorkerReceipt
from .worker_contract import WorkerContract

M3_BUS_FAULTS = {
    "receipt_signature_tamper": "consumption_signature_gate",
    "artifact_store_corruption": "artifact_integrity_gate",
    "receipt_queue_mutation": "append_only_sqlite_trigger",
    "dependency_receipt_mismatch": "dependency_admission_gate",
}


def _signed(identity: StationIdentity, *, task_id: str = "parent", artifact: bytes = b"hello") -> WorkerReceipt:
    binding = ArtifactBinding("output.txt", sha256(artifact).hexdigest(), len(artifact))
    base = WorkerReceipt(
        receipt_id=f"receipt-{task_id}", execution_plan_hash="1" * 64,
        task_id=task_id, worker_id="worker1", swarm_id="swarm1", attempt_id="attempt1",
        engine_name="brokered-python", engine_version="linux-seccomp-broker-v1",
        input_commit="2" * 40, output_commit="3" * 40, contract_hash="4" * 64,
        artifacts=(binding,), requirements_met=(("R1", True),),
        verification_results=(("unit", "pass"),), overall_verdict="pass",
        verifier_identity="station-verifier", verifier_revision="6" * 64,
        issued_at_ns=time.time_ns(), station_key_id=identity.key_id, station_signature="00")
    return dataclasses.replace(base, station_signature=identity.sign(base.receipt_hash))


def _contract() -> WorkerContract:
    return WorkerContract(
        task_id="child", worker_id="worker-child", swarm_id="swarm1",
        execution_plan_hash="1" * 64, attempt_id="attempt-child", lease_id="lease-child",
        lease_generation=1, input_commit="2" * 40, workspace_root="/tmp/residual-m3-child",
        inputs=("input.txt",), allowed_outputs=("output.txt",), forbidden=(),
        requirements=("R1",), acceptance=("unit",), dependencies=("parent",),
        allowed_tools=("read_file", "write_file"), forbidden_tools=("shell",),
        token_budget=0, wall_clock_budget_s=5.0, max_tool_calls=5,
        max_file_writes=2, memory_limit_mb=128)


def _tamper_receipt(receipt: WorkerReceipt) -> WorkerReceipt:
    value = strict_json(canonical(receipt.to_dict()))
    value["task_id"] = "tampered-parent"
    unsigned = {k: v for k, v in value.items() if k not in {"receipt_hash", "station_signature"}}
    value["receipt_hash"] = sha256(canonical(unsigned).encode()).hexdigest()
    return WorkerReceipt.from_dict(value)


def run_m3_bus_fault(fault: str) -> dict[str, Any]:
    if fault not in M3_BUS_FAULTS:
        raise EvidenceError(f"unknown M3 bus fault: {fault}")
    with tempfile.TemporaryDirectory() as directory:
        identity = StationIdentity.generate()
        bus = EvidenceBus(Path(directory) / "evidence.db")
        receipt = _signed(identity)
        artifact = b"hello"
        injected = detected = trusted_handoff = False
        stored_unverified = False
        detail = ""

        if fault == "receipt_signature_tamper":
            tampered = _tamper_receipt(receipt)
            bus.append(tampered, {"output.txt": artifact})
            stored_unverified = True
            injected = True
            try:
                bus.consumable(tampered.receipt_hash, station_public_key=identity.public_bytes())
                trusted_handoff = True
            except EvidenceError:
                detected = True
                detail = "tampered signed receipt stored but rejected at consumption"

        elif fault == "artifact_store_corruption":
            bus.append(receipt, {"output.txt": artifact})
            with sqlite3.connect(bus.path) as db:
                db.execute("UPDATE artifacts SET bytes=? WHERE sha256=?", (b"evil!", receipt.artifacts[0].sha256))
            injected = True
            try:
                bus.consumable(receipt.receipt_hash, station_public_key=identity.public_bytes())
                trusted_handoff = True
            except EvidenceError:
                detected = True
                detail = "artifact corruption rejected by content-address verification"

        elif fault == "receipt_queue_mutation":
            bus.append(receipt, {"output.txt": artifact})
            try:
                with sqlite3.connect(bus.path) as db:
                    db.execute("UPDATE receipts SET queue_hash=? WHERE receipt_hash=?", ("9" * 64, receipt.receipt_hash))
            except sqlite3.IntegrityError:
                injected = True
                detected = True
                detail = "append-only trigger blocked receipt mutation"
            trusted_handoff = not detected

        elif fault == "dependency_receipt_mismatch":
            wrong = _signed(identity, task_id="other")
            bus.append(wrong, {"output.txt": artifact})
            injected = True
            try:
                bus.admit_dependencies(_contract(), (wrong.receipt_hash,), station_public_key=identity.public_bytes())
                trusted_handoff = True
            except EvidenceError:
                detected = True
                detail = "dependency task set rejected"

        contained = injected and detected and not trusted_handoff
        return {
            "schema_version": "residual.m3-bus-fault-trial.v1",
            "fault": fault,
            "expected_boundary": M3_BUS_FAULTS[fault],
            "injection_observed": injected,
            "detected": detected,
            "trusted_handoff": trusted_handoff,
            "stored_unverified_receipt": stored_unverified,
            "contained": contained,
            "detail": detail,
        }


def aggregate_m3_bus_faults() -> dict[str, Any]:
    trials = [run_m3_bus_fault(name) for name in M3_BUS_FAULTS]
    if any(not trial["injection_observed"] for trial in trials):
        raise EvidenceError("M3 experiment contained an unobserved injection")
    contained = sum(bool(trial["contained"]) for trial in trials)
    return {
        "schema_version": "residual.m3-bus-fault-report.v1",
        "faults": len(trials), "contained": contained,
        "fcr": contained / len(trials) if trials else 0.0,
        "trials": trials,
        "finding": "EvidenceBus.append accepts an invalidly signed receipt; trust is enforced by consumable().",
    }
