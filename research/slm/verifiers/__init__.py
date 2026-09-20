"""SLM-00 Control Bench v0 category-specific deterministic verifier suite.

Lane D deliverable. Lane C's benchmark items reference verifiers by the IDs
in VERIFIER_REGISTRY / MANIFEST.json. All verifiers are pure deterministic
functions (item, candidate_output) -> PASS | FAIL | BENCHMARK_DEFECT with a
stable reason code. No network, no model calls.
"""
from __future__ import annotations

from .adversarial_malformed import AdversarialMalformedVerifier
from .base import (
    BaseVerifier,
    MalformedOutput,
    Verdict,
    VerifierResult,
)
from .budget_decisions import BudgetDecisionsVerifier
from .contract_compilation import ContractCompilationVerifier
from .evidence_sufficiency import EvidenceSufficiencyVerifier
from .failure_classification import FailureClassificationVerifier
from .retry_escalate_abort import RetryEscalateAbortVerifier
from .stale_state_authority import StaleStateAuthorityVerifier
from .worker_routing import WorkerRoutingVerifier

SUITE_VERSION = "1.0.0"

_VERIFIER_CLASSES = (
    WorkerRoutingVerifier,
    ContractCompilationVerifier,
    EvidenceSufficiencyVerifier,
    RetryEscalateAbortVerifier,
    BudgetDecisionsVerifier,
    FailureClassificationVerifier,
    AdversarialMalformedVerifier,
    StaleStateAuthorityVerifier,
)

VERIFIER_REGISTRY = {cls.VERIFIER_ID: cls for cls in _VERIFIER_CLASSES}


def get_verifier(verifier_id: str) -> BaseVerifier:
    """Instantiate a verifier by its manifest ID."""
    if verifier_id not in VERIFIER_REGISTRY:
        raise KeyError(
            f"unknown verifier id {verifier_id!r}; known: {sorted(VERIFIER_REGISTRY)}"
        )
    return VERIFIER_REGISTRY[verifier_id]()


def verify(item, candidate_output) -> VerifierResult:
    """Convenience dispatcher: route an item to its declared verifier."""
    verifier_ref = item.get("verifier_ref") if isinstance(item, dict) else None
    if not isinstance(verifier_ref, str):
        return VerifierResult(
            Verdict.BENCHMARK_DEFECT, "ITEM_MISSING_VERIFIER_REF"
        )
    try:
        verifier = get_verifier(verifier_ref)
    except KeyError:
        return VerifierResult(
            Verdict.BENCHMARK_DEFECT,
            "UNKNOWN_VERIFIER_REF",
            f"no verifier registered for {verifier_ref!r}",
        )
    return verifier.verify(item, candidate_output)


__all__ = [
    "AdversarialMalformedVerifier",
    "BaseVerifier",
    "BudgetDecisionsVerifier",
    "ContractCompilationVerifier",
    "EvidenceSufficiencyVerifier",
    "FailureClassificationVerifier",
    "MalformedOutput",
    "RetryEscalateAbortVerifier",
    "StaleStateAuthorityVerifier",
    "SUITE_VERSION",
    "VERIFIER_REGISTRY",
    "Verdict",
    "VerifierResult",
    "WorkerRoutingVerifier",
    "get_verifier",
    "verify",
]
