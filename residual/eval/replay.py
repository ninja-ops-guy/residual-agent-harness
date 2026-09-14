"""Observation-only replay for SPEC-EVAL-001 signed reports."""
from __future__ import annotations

from typing import Iterable

from observation_layer import Observation
from residual.factory.evidence_receipts import StationIdentity

from .spec_eval import (
    EvaluationRunEvidence,
    REPORT_EVENT,
    RUN_EVENT,
    SignedComparisonReport,
    SpecEvalError,
    SpecEvaluationEvidence,
)
from .workload import FrozenWorkload


def signed_report_from_observations(
    workload: FrozenWorkload,
    observations: Iterable[Observation],
    *,
    minimum_runs: int = 3,
    significance_test: str = "mann_whitney_u",
    alpha: float = 0.05,
) -> SignedComparisonReport:
    """Rebuild a signed ComparisonReport without the original private key.

    Run observations contain all report inputs. The terminal observation contains the
    Station key ID and signature over the deterministic report hash. Replay computes
    the payload using an ephemeral local signer, discards that temporary signature,
    checks the payload hash against the terminal event, then reattaches the original
    Station signature from the observation log.
    """
    runs: list[EvaluationRunEvidence] = []
    terminal = None
    for observation in observations:
        payload = observation.payload
        if payload.get("event") == RUN_EVENT:
            run = EvaluationRunEvidence.from_dict(payload["run"])
            if payload.get("run_hash") != run.run_hash:
                raise SpecEvalError("observation run hash mismatch")
            runs.append(run)
        elif payload.get("event") == REPORT_EVENT:
            if terminal is not None:
                raise SpecEvalError("multiple terminal evaluation report observations")
            terminal = payload
    if terminal is None:
        raise SpecEvalError("evaluation trace has no terminal report observation")

    temporary = StationIdentity.generate()
    builder = SpecEvaluationEvidence(workload, temporary, minimum_runs=minimum_runs)
    candidate = builder.build_report(
        runs,
        significance_test=significance_test,
        alpha=alpha,
    )
    if terminal.get("report_hash") != candidate.report_hash:
        raise SpecEvalError("terminal observation report hash mismatch")
    source_hashes = terminal.get("source_run_hashes")
    if tuple(source_hashes) != tuple(candidate.payload["run_hashes"]):
        raise SpecEvalError("terminal observation run binding mismatch")
    key_id = terminal.get("station_key_id")
    signature = terminal.get("station_signature")
    if not isinstance(key_id, str) or not isinstance(signature, str):
        raise SpecEvalError("terminal observation lacks Station signature metadata")
    return SignedComparisonReport(
        payload=candidate.payload,
        station_key_id=key_id,
        station_signature=signature,
    )
