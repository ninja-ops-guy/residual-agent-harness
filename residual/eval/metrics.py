"""EVAL-R5/R6: reliability metrics over paired run records.

Definitions (X = independent correctness, A = acceptance; UNKNOWN runs stay
in denominators):

- AER  acceptance error rate       P(not X | A)   == FAR (false acceptance rate)
- ISR  incorrect suppression rate  P(not A | not X)
- ASSR accepted-and-sound rate     P(X and A)
- acceptance coverage              P(A)
- false rejection rate             P(not A | X)
- FCR  fault capture rate          P(caught | fault-labeled), only when labels exist
- throughput                       completed runs / total wall latency (runs per second)
- latency                          mean / p50 / p95 over all retained runs
- rework                           mean rework attempts per run
- conflicts                        integration conflict count/rate
- verifier rejection               verifier rejection rate
- token/compute cost               tokens and USD totals and per accepted-correct run
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

from ..core import ContractError
from .runner import RunRecord, RunState


def _rate(num: int, den: int) -> float | None:
    """Rate with explicit None for undefined (zero denominator), never 0.0."""
    return num / den if den else None


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
    return ordered[index]


@dataclass(frozen=True)
class SliceMetrics:
    config_id: str
    slice: str
    runs: int
    state_counts: dict[str, int]
    P_X: float
    P_A: float
    P_X_given_A: float | None
    aer_far: float | None
    isr: float | None
    assr: float
    acceptance_coverage: float
    false_rejection_rate: float | None
    fcr: float | None
    throughput_runs_per_sec: float | None
    latency_ms_mean: float
    latency_ms_p50: float
    latency_ms_p95: float | None
    rework_per_run: float
    conflicts_total: int
    conflict_rate: float
    verifier_rejection_rate: float
    input_tokens: int
    output_tokens: int
    cost_usd_total: float
    cost_per_accepted_correct_usd: float | None
    missing_grades: int  # UNKNOWN/aborted runs retained in denominators

    def payload(self) -> dict[str, object]:
        return {k: v for k, v in self.__dict__.items()}


def compute_slice_metrics(config_id: str, slice_name: str,
                          records: list[RunRecord]) -> SliceMetrics:
    if not records:
        raise ContractError("metrics require at least one run record")
    for record in records:
        if record.config_id != config_id or record.slice != slice_name:
            raise ContractError("record does not belong to this config/slice")
    n = len(records)
    state_counts = {state.value: 0 for state in RunState}
    for record in records:
        if record.state not in state_counts:
            raise ContractError(f"unknown run state {record.state}")
        state_counts[record.state] += 1

    accepted = [r for r in records if r.accepted]
    graded = [r for r in records if r.correct is not None]
    correct = [r for r in records if r.correct is True]
    incorrect = [r for r in records if r.correct is False]
    accepted_correct = [r for r in accepted if r.correct is True]
    accepted_incorrect = [r for r in accepted if r.correct is False]
    fault_labeled = [r for r in records if r.fault_label is not None]
    fault_caught = [r for r in fault_labeled if r.fault_caught is True]

    total_latency = sum(r.latency_ms for r in records)
    total_input = sum(r.input_tokens for r in records)
    total_output = sum(r.output_tokens for r in records)
    total_cost = round(sum(r.cost_usd for r in records), 8)

    return SliceMetrics(
        config_id=config_id,
        slice=slice_name,
        runs=n,
        state_counts=state_counts,
        P_X=len(correct) / n,
        P_A=len(accepted) / n,
        P_X_given_A=_rate(len(accepted_correct), len(accepted)),
        aer_far=_rate(len(accepted_incorrect), len(accepted)),
        isr=_rate(sum(1 for r in incorrect if not r.accepted), len(incorrect)),
        assr=len(accepted_correct) / n,
        acceptance_coverage=len(accepted) / n,
        false_rejection_rate=_rate(sum(1 for r in correct if not r.accepted), len(correct)),
        fcr=_rate(len(fault_caught), len(fault_labeled)) if fault_labeled else None,
        throughput_runs_per_sec=(n / (total_latency / 1000.0)) if total_latency else None,
        latency_ms_mean=total_latency / n,
        latency_ms_p50=statistics.median(r.latency_ms for r in records),
        latency_ms_p95=_percentile([r.latency_ms for r in records], 0.95),
        rework_per_run=sum(r.rework_attempts for r in records) / n,
        conflicts_total=sum(r.conflicts for r in records),
        conflict_rate=sum(r.conflicts for r in records) / n,
        verifier_rejection_rate=sum(1 for r in records if r.verifier_rejected) / n,
        input_tokens=total_input,
        output_tokens=total_output,
        cost_usd_total=total_cost,
        cost_per_accepted_correct_usd=(
            total_cost / len(accepted_correct)) if accepted_correct else None,
        missing_grades=n - len(graded),
    )
