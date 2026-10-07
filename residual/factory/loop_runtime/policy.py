from __future__ import annotations

from residual.core import Obligation, digest
from .state import (
    CapabilityFloor,
    DeduplicationMaterial,
    ExecutionIntent,
    ParallelismHint,
    ProgressVector,
    Urgency,
)


def deduplication_key(obligation: Obligation, material: DeduplicationMaterial) -> str:
    return digest({
        "schema": "residual.loop.dedup.v1",
        "obligation_id": obligation.id,
        "input_artifact_hashes": sorted(material.input_artifact_hashes),
        "worker_contract_hash": material.worker_contract_hash,
    })


def next_intent(
    progress: ProgressVector,
    *,
    cooldown: int,
    deduplication_keys: dict[str, str],
) -> tuple[ExecutionIntent, bool]:
    if progress.churn:
        if cooldown == 0:
            return (
                ExecutionIntent(
                    urgency=Urgency.LOW,
                    capability_floor=CapabilityFloor.HIGHER,
                    parallelism=ParallelismHint.ALLOW,
                    rationale="accepted_tree_churn_without_obligation_resolution",
                    deduplication_keys=deduplication_keys,
                ),
                True,
            )
        return ExecutionIntent(urgency=Urgency.LOW, rationale="churn_cooldown", deduplication_keys=deduplication_keys), False
    if progress.repeated_failure or progress.progress_delta <= 0:
        if cooldown == 0:
            return (
                ExecutionIntent(
                    urgency=Urgency.HIGH,
                    capability_floor=CapabilityFloor.HIGHER,
                    rationale="stagnation_or_repeated_failure",
                    deduplication_keys=deduplication_keys,
                ),
                True,
            )
        return ExecutionIntent(urgency=Urgency.NORMAL, rationale="stagnation_cooldown", deduplication_keys=deduplication_keys), False
    return ExecutionIntent(deduplication_keys=deduplication_keys), False
