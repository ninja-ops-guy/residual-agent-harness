from __future__ import annotations

from typing import Mapping

from residual.core import Obligation, digest
from .state import FactoryResultSet, ObligationState, ProgressVector, ResidualWorkSet, VerificationStatus


class ResidualWorkAdapter:
    """Loop-local view over immutable Factory obligations; never copies/redefines them."""

    @staticmethod
    def view(
        obligations: tuple[Obligation, ...],
        attempt_counts: Mapping[str, int],
        failure_fingerprints: Mapping[str, str],
    ) -> ResidualWorkSet:
        return ResidualWorkSet(
            obligations=obligations,
            attempt_counts={o.id: int(attempt_counts.get(o.id, 0)) for o in obligations},
            failure_fingerprints={o.id: failure_fingerprints[o.id] for o in obligations if o.id in failure_fingerprints},
        )


def residual_mass(result: FactoryResultSet) -> float:
    failed = sum(1 for item in result.verification_results if item.status == VerificationStatus.FAIL)
    unknown = sum(1 for item in result.verification_results if item.status == VerificationStatus.UNKNOWN)
    unresolved = sum(
        1
        for state in result.obligation_states.values()
        if state in {ObligationState.UNRESOLVED, ObligationState.REJECTED, ObligationState.UNKNOWN}
    )
    return float(failed + unknown + unresolved)


def failure_fingerprint(result: FactoryResultSet) -> str:
    counterexamples = sorted(
        (item.verification_id, item.status.value, item.receipt_ref or "")
        for item in result.verification_results
        if item.status != VerificationStatus.PASS
    )
    return digest({
        "residual_ids": sorted(o.id for o in result.residual_obligations),
        "verification_failures": counterexamples,
        "accepted_tree_hash": result.accepted_tree_hash,
    })


def measure_progress(previous: FactoryResultSet | None, current: FactoryResultSet, fingerprint_seen: int) -> ProgressVector:
    current_mass = residual_mass(current)
    previous_mass = residual_mass(previous) if previous is not None else current_mass
    accepted = sum(1 for state in current.obligation_states.values() if state == ObligationState.ACCEPTED)
    previous_accepted = (
        sum(1 for state in previous.obligation_states.values() if state == ObligationState.ACCEPTED)
        if previous is not None else 0
    )
    resolved_delta = max(0, accepted - previous_accepted)
    tree_changed = previous is None or current.accepted_tree_hash != previous.accepted_tree_hash
    mass_decreased = current_mass < previous_mass
    churn = previous is not None and tree_changed and resolved_delta == 0 and not mass_decreased
    return ProgressVector(
        residual_mass=current_mass,
        progress_delta=previous_mass - current_mass,
        accepted_obligations=accepted,
        obligation_resolved_delta=resolved_delta,
        tree_changed=tree_changed,
        churn=churn,
        repeated_failure=fingerprint_seen > 0,
    )
