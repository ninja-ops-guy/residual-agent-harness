"""Trusted Station-side issuance of signed M3 WorkerReceipts."""
from __future__ import annotations

import time
import uuid
from pathlib import Path

from .runtime import RuntimeResult
from .worker_contract import WorkerContract
from .evidence_receipts import ArtifactBinding, EvidenceError, RECEIPT_SCHEMA, WorkerReceipt, VerificationDecision, _hash, _sha256

class FactoryStationIssuer:
    """Trusted host component that turns a quarantined candidate into a signed receipt."""
    def __init__(self, identity, bus):
        self.identity, self.bus = identity, bus

    @staticmethod
    def _candidate_bytes(result: RuntimeResult, workspace_root: str | Path) -> tuple[tuple[ArtifactBinding, ...], dict[str, bytes]]:
        if result.status != "CANDIDATE" or result.candidate is None:
            raise EvidenceError("only quarantined candidates can be verified")
        root = Path(workspace_root).resolve()
        artifacts, content = [], {}
        for path, expected_hash in result.candidate.artifacts:
            target = root / path
            if not target.is_relative_to(root):
                raise EvidenceError("candidate artifact escapes workspace")
            if expected_hash is None:
                if target.exists(): raise EvidenceError("candidate deletion does not match workspace")
                artifacts.append(ArtifactBinding(path, None, 0, True)); continue
            if not target.is_file() or target.is_symlink():
                raise EvidenceError("candidate artifact is not a regular file")
            data = target.read_bytes(); actual = _sha256(data)
            if actual != expected_hash:
                raise EvidenceError("candidate artifact hash changed before Station verification")
            artifacts.append(ArtifactBinding(path, actual, len(data), False)); content[path] = data
        return tuple(artifacts), content

    def issue(self, *, contract: WorkerContract, result: RuntimeResult,
              workspace_root: str | Path, decision: VerificationDecision,
              parent_receipts: tuple[str, ...] = (), supersedes: str | None = None) -> WorkerReceipt:
        try:
            return self._issue(contract=contract, result=result, workspace_root=workspace_root,
                               decision=decision, parent_receipts=parent_receipts, supersedes=supersedes)
        except EvidenceError as exc:
            self.bus._emit("CandidateRejected", attempt_id=getattr(contract, "attempt_id", "unknown"),
                           task_id=getattr(contract, "task_id", "unknown"),
                           reason=type(exc).__name__)
            raise

    def _issue(self, *, contract: WorkerContract, result: RuntimeResult,
               workspace_root: str | Path, decision: VerificationDecision,
               parent_receipts: tuple[str, ...] = (), supersedes: str | None = None) -> WorkerReceipt:
        if result.contract_hash != contract.contract_hash or result.execution_plan_hash != contract.execution_plan_hash:
            raise EvidenceError("runtime candidate does not match WorkerContract")
        if result.attempt_id != contract.attempt_id:
            raise EvidenceError("runtime candidate attempt mismatch")
        if decision.verdict != "pass" or not all(v for _, v in decision.requirements_met):
            raise EvidenceError("Station verification did not pass")
        required_checks = set(contract.acceptance)
        passed = {name for name, status in decision.results if status == "pass"}
        if not required_checks <= passed:
            raise EvidenceError("Station decision does not satisfy WorkerContract acceptance criteria")
        required_requirements = set(contract.requirements)
        met = {name for name, ok in decision.requirements_met if ok}
        if not required_requirements <= met:
            raise EvidenceError("Station decision does not satisfy WorkerContract requirements")
        artifacts, content = self._candidate_bytes(result, workspace_root)
        fields = dict(
            receipt_id=str(uuid.uuid4()), execution_plan_hash=contract.execution_plan_hash,
            task_id=contract.task_id, worker_id=contract.worker_id, swarm_id=contract.swarm_id,
            attempt_id=contract.attempt_id, engine_name=result.engine_name,
            engine_version=result.engine_version, input_commit=result.candidate.input_commit,
            output_commit=result.candidate.output_commit, contract_hash=contract.contract_hash,
            artifacts=artifacts, requirements_met=decision.requirements_met,
            verification_results=decision.results, overall_verdict="pass",
            verifier_identity=decision.verifier_identity,
            verifier_revision=decision.verifier_revision, parent_receipts=parent_receipts,
            supersedes=supersedes, issued_at_ns=time.time_ns(), station_key_id=self.identity.key_id)
        unsigned = {
            "schema_version": RECEIPT_SCHEMA, "receipt_id": fields["receipt_id"],
            "execution_plan_hash": fields["execution_plan_hash"], "task_id": fields["task_id"],
            "worker_id": fields["worker_id"], "swarm_id": fields["swarm_id"],
            "attempt_id": fields["attempt_id"], "engine_name": fields["engine_name"],
            "engine_version": fields["engine_version"], "input_commit": fields["input_commit"],
            "output_commit": fields["output_commit"], "contract_hash": fields["contract_hash"],
            "artifacts": [x.to_dict() for x in sorted(artifacts, key=lambda x: x.path)],
            "requirements_met": [list(x) for x in sorted(decision.requirements_met)],
            "verification_results": [list(x) for x in sorted(decision.results)],
            "overall_verdict": "pass", "verifier_identity": decision.verifier_identity,
            "verifier_revision": decision.verifier_revision,
            "parent_receipts": list(sorted(parent_receipts)), "supersedes": supersedes,
            "issued_at_ns": fields["issued_at_ns"], "station_key_id": self.identity.key_id}
        signature = self.identity.sign(_hash(unsigned))
        receipt = WorkerReceipt(**fields, station_signature=signature)
        self.bus.append(receipt, content)
        return receipt
