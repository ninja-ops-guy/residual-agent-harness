"""Station/M3 admission for quarantined Factory assurance candidates."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from ..factory.evidence_receipts import VerificationDecision, WorkerReceipt
from ..factory.runtime import FactoryRuntime, RuntimeResult
from ..factory.station_issuer import FactoryStationIssuer
from ..factory.worker_contract import WorkerContract
from .factory_adapter import FactoryAssuranceError


DecisionProvider = Callable[[WorkerContract, RuntimeResult], VerificationDecision]
ParentReceiptProvider = Callable[[WorkerContract], tuple[str, ...]]


@dataclass(frozen=True)
class FactoryAdmissionResult:
    receipts: tuple[WorkerReceipt, ...]
    receipt_hashes: tuple[str, ...]


@dataclass
class FactoryM3Admission:
    """Admit verified Factory candidates into the signed Evidence Bus.

    VerificationDecision is supplied by the trusted Station side. This bridge does
    not infer a pass from the assurance verifier and never manufactures receipts.
    After successful append, the quarantined worktree may be purged because the
    Evidence Bus has already stored content-addressed artifact bytes.
    """

    runtime: FactoryRuntime
    issuer: FactoryStationIssuer
    decision_for: DecisionProvider
    parent_receipts_for: ParentReceiptProvider | None = None
    purge_after_admission: bool = True

    def admit(
        self,
        contracts: Sequence[WorkerContract],
        results: Sequence[RuntimeResult],
    ) -> FactoryAdmissionResult:
        by_attempt = {result.attempt_id: result for result in results}
        if len(by_attempt) != len(results):
            raise FactoryAssuranceError("duplicate Factory runtime attempt result")
        expected = {contract.attempt_id for contract in contracts}
        if set(by_attempt) != expected:
            raise FactoryAssuranceError("Factory admission result set differs from WorkerContracts")

        receipts: list[WorkerReceipt] = []
        admitted_contracts: list[WorkerContract] = []
        for contract in sorted(contracts, key=lambda value: value.attempt_id):
            result = by_attempt[contract.attempt_id]
            decision = self.decision_for(contract, result)
            if not isinstance(decision, VerificationDecision):
                raise FactoryAssuranceError("Station decision provider returned invalid decision")
            parent_receipts = () if self.parent_receipts_for is None else self.parent_receipts_for(contract)
            receipt = self.issuer.issue(
                contract=contract,
                result=result,
                workspace_root=contract.workspace_root,
                decision=decision,
                parent_receipts=parent_receipts,
            )
            receipts.append(receipt)
            admitted_contracts.append(contract)

        if self.purge_after_admission:
            for contract in admitted_contracts:
                self.runtime.purge(contract)

        return FactoryAdmissionResult(
            receipts=tuple(receipts),
            receipt_hashes=tuple(receipt.receipt_hash for receipt in receipts),
        )
