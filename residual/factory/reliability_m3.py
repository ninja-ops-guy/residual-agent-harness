"""Controlled reliability trials for M3 signed WorkerReceipt integrity.

These experiments exercise the cryptographic receipt primitive only. They do not
claim atomic artifact-store containment until that M3 store exists in code.
"""
from __future__ import annotations

import dataclasses
import time
from typing import Any

from residual.core import canonical, strict_json
from .evidence_receipts import ArtifactBinding, EvidenceError, StationIdentity, WorkerReceipt


M3_FAULTS = {
    "receipt_payload_tamper": "receipt_signature",
    "verifier_revision_tamper": "verifier_revision",
    "artifact_hash_tamper": "artifact_binding",
    "wrong_station_key": "station_identity",
}


def _base_receipt(identity: StationIdentity) -> WorkerReceipt:
    placeholder = WorkerReceipt(
        receipt_id="receipt-1",
        execution_plan_hash="1" * 64,
        task_id="task1",
        worker_id="worker1",
        swarm_id="swarm1",
        attempt_id="attempt1",
        engine_name="brokered-python",
        engine_version="linux-seccomp-broker-v1",
        input_commit="2" * 40,
        output_commit="3" * 40,
        contract_hash="4" * 64,
        artifacts=(ArtifactBinding("output.txt", "5" * 64, 5),),
        requirements_met=(("R1", True),),
        verification_results=(("unit", "pass"),),
        overall_verdict="pass",
        verifier_identity="station-verifier",
        verifier_revision="6" * 64,
        issued_at_ns=time.time_ns(),
        station_key_id=identity.key_id,
        station_signature="00",
    )
    return dataclasses.replace(placeholder, station_signature=identity.sign(placeholder.receipt_hash))


def _recompute_hash(document: dict[str, Any]) -> dict[str, Any]:
    """Reparse after mutation so the attacker updates the public hash but not signature."""
    from hashlib import sha256
    unsigned = {k: v for k, v in document.items() if k not in {"receipt_hash", "station_signature"}}
    document["receipt_hash"] = sha256(canonical(unsigned).encode("utf-8")).hexdigest()
    return document


def run_m3_fault(fault: str) -> dict[str, Any]:
    if fault not in M3_FAULTS:
        raise EvidenceError(f"unknown M3 fault: {fault}")
    identity = StationIdentity.generate()
    original = _base_receipt(identity)
    document = strict_json(canonical(original.to_dict()))
    observed = False
    parse_rejected = False
    verified = False

    if fault == "receipt_payload_tamper":
        document["task_id"] = "task2"
        _recompute_hash(document)
        observed = True
    elif fault == "verifier_revision_tamper":
        document["verifier_revision"] = "7" * 64
        _recompute_hash(document)
        observed = True
    elif fault == "artifact_hash_tamper":
        document["artifacts"][0]["sha256"] = "8" * 64
        _recompute_hash(document)
        observed = True
    elif fault == "wrong_station_key":
        observed = True

    try:
        candidate = WorkerReceipt.from_dict(document)
        public_key = StationIdentity.generate().public_bytes() if fault == "wrong_station_key" else identity.public_bytes()
        verified = StationIdentity.verify(candidate, public_key)
    except EvidenceError:
        parse_rejected = True

    contained = observed and not verified
    return {
        "schema_version": "residual.m3-fault-trial.v1",
        "fault": fault,
        "expected_boundary": M3_FAULTS[fault],
        "injection_observed": observed,
        "parse_rejected": parse_rejected,
        "signature_verified": verified,
        "trusted_handoff": verified,
        "contained": contained,
        "receipt_hash_before": original.receipt_hash,
        "receipt_hash_after": document.get("receipt_hash"),
        "station_key_id": original.station_key_id,
    }


def aggregate_m3_faults(faults: tuple[str, ...] | None = None) -> dict[str, Any]:
    selected = tuple(M3_FAULTS) if faults is None else tuple(faults)
    trials = [run_m3_fault(fault) for fault in selected]
    if any(not trial["injection_observed"] for trial in trials):
        raise EvidenceError("M3 experiment contained an unobserved injection")
    return {
        "schema_version": "residual.m3-fault-report.v1",
        "faults": len(trials),
        "contained": sum(bool(x["contained"]) for x in trials),
        "fcr": (sum(bool(x["contained"]) for x in trials) / len(trials)) if trials else 0.0,
        "trials": trials,
        "claim_scope": "signed WorkerReceipt integrity only; atomic artifact-store behavior not measured",
    }
