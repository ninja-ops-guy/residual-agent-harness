"""EVAL-R4/R5/R7/R8: deterministic study runner producing paired run records.

The development fixture uses a scripted engine whose outcomes are a pure
function of (workload hash, task id, config id, repeat, seed), so CI runs are
fully reproducible without model credentials. Correctness X is graded
independently of acceptance A: X comes from the exact-match grader on the
worker artifact; A comes from the control-layer pipeline. UNKNOWN (aborted)
and FAIL runs are retained in every aggregate denominator.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from enum import Enum

from ..core import ContractError, digest
from .configs import CONFIGURATIONS, ExperimentConfig
from .workload import FrozenTask, FrozenWorkload

MIN_REPEATS = 3  # EVAL-R4


class RunState(str, Enum):
    """Terminal states stay distinct (shared rule 6)."""

    PASS = "PASS"            # artifact correct AND accepted
    FAIL = "FAIL"            # run completed; artifact incorrect AND accepted (false accept)
    REJECTED = "REJECTED"    # pipeline/verifier declined the artifact
    UNKNOWN = "UNKNOWN"      # aborted / incomplete evidence; stays in denominators


def _draw(*parts: str) -> float:
    """Deterministic pseudo-random value in [0, 1) from string parts."""
    material = "|".join(parts).encode("utf-8")
    value = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    return value / 2**64


@dataclass(frozen=True)
class RunRecord:
    """One paired observation: (task, config, repeat) -> outcomes (EVAL-R7)."""

    record_id: str
    workload_sha256: str
    task_id: str
    slice: str
    config_id: str
    repeat: int
    state: str
    correct: bool | None        # X: independent grader verdict (None when aborted)
    accepted: bool              # A: pipeline acceptance verdict
    fault_label: str | None
    fault_caught: bool | None   # FCR support: fault detected when labeled
    verifier_rejected: bool
    rework_attempts: int
    conflicts: int
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    evidence_level: str         # scripted runner is always "development_fixture" (EVAL-R10)
    aborted: bool = False
    abort_reason: str | None = None

    def payload(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "workload_sha256": self.workload_sha256,
            "task_id": self.task_id,
            "slice": self.slice,
            "config_id": self.config_id,
            "repeat": self.repeat,
            "state": self.state,
            "correct": self.correct,
            "accepted": self.accepted,
            "fault_label": self.fault_label,
            "fault_caught": self.fault_caught,
            "verifier_rejected": self.verifier_rejected,
            "rework_attempts": self.rework_attempts,
            "conflicts": self.conflicts,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "evidence_level": self.evidence_level,
            "aborted": self.aborted,
            "abort_reason": self.abort_reason,
        }

    @property
    def sha256(self) -> str:
        return digest(self.payload())


# --- scripted engine -------------------------------------------------------

def _worker_correct(config: ExperimentConfig, task: FrozenTask, repeat: int,
                    workload_sha: str) -> bool:
    """Scripted worker outcome. Control layers cannot change worker skill
    (EVAL-R3): the raw correctness draw ignores control layers entirely; only
    fault-labeled tasks are scripted wrong."""
    if task.fault_label is not None:
        return False
    p_correct = 0.75
    return _draw("worker", workload_sha, task.task_id, str(repeat)) < p_correct


def _aborted(config: ExperimentConfig, task: FrozenTask, repeat: int,
             workload_sha: str) -> bool:
    p_abort = 0.05 if config.config_id != "R0" else 0.02
    return _draw("abort", workload_sha, task.task_id, config.config_id, str(repeat)) < p_abort


def _verifier_accepts(config: ExperimentConfig, task: FrozenTask, repeat: int,
                      correct: bool, workload_sha: str) -> bool:
    """Acceptance A as a function of the control-layer stack.

    R0/R1 accept everything (no acceptance boundary). R2 contracts reject
    some malformed (incorrect) artifacts. R3 adds an imperfect verifier
    (recall ~0.9, false-reject ~0.05). R4 deterministic integration removes
    remaining integration-level false accepts. R5 dynamic swarm adds a
    cross-check that lowers false rejection.
    """
    layers = set(config.control_layers)
    if "verification" not in layers:
        if "contracts" not in layers:
            return True  # R0/R1: no boundary at all
        if correct:
            return True
        return _draw("contract", workload_sha, task.task_id, str(repeat)) < 0.4
    # verification present (R3+)
    if correct:
        p_reject_correct = 0.05 if "dynamic_swarm" not in layers else 0.02
        return _draw("verifier", workload_sha, task.task_id, str(repeat)) >= p_reject_correct
    recall = 0.90
    if "deterministic_integration" in layers:
        recall = 0.97
    # recall = P(verifier catches an incorrect artifact); accept the rest.
    return _draw("verifier", workload_sha, task.task_id, str(repeat)) >= recall


def run_task(config: ExperimentConfig, task: FrozenTask, repeat: int,
             workload_sha: str, evidence_level: str = "development_fixture") -> RunRecord:
    if evidence_level != "development_fixture":
        raise ContractError(
            "scripted eval_frozen runner cannot emit live-model evidence"
        )
    aborted = _aborted(config, task, repeat, workload_sha)
    record_id = f"{workload_sha[:12]}:{task.task_id}:{config.config_id}:{repeat}"
    base_latency = 120.0 + 100.0 * len(config.control_layers)
    latency_jitter = _draw("latency", workload_sha, task.task_id, config.config_id,
                           str(repeat)) * 40.0
    input_tokens = 200 + len(task.prompt) // 2
    output_tokens = 64
    rework = 0
    conflicts = 0
    verifier_rejected = False
    fault_caught: bool | None = None

    if aborted:
        state = RunState.UNKNOWN
        correct: bool | None = None
        accepted = False
        if task.fault_label is not None:
            fault_caught = None  # no evidence; not counted as caught
        latency = base_latency * 0.5 + latency_jitter
        output_tokens = 0
    else:
        correct = _worker_correct(config, task, repeat, workload_sha)
        accepted = _verifier_accepts(config, task, repeat, correct, workload_sha)
        layers = set(config.control_layers)
        verifier_rejected = ("verification" in layers or "contracts" in layers) and not accepted
        if verifier_rejected:
            # rejected artifacts trigger bounded rework in constrained configs
            rework = 1 if "constraints" in layers else 0
        if "deterministic_integration" in layers:
            conflicts = 0  # deterministic merge removes integration conflicts
        elif "orchestration" in layers:
            conflicts = int(_draw("conflict", workload_sha, task.task_id,
                                  str(repeat)) < 0.15)
        if task.fault_label is not None:
            fault_caught = not accepted
        if accepted and correct:
            state = RunState.PASS
        elif accepted and not correct:
            state = RunState.FAIL
        else:
            state = RunState.REJECTED
        latency = base_latency + latency_jitter + 80.0 * rework
        output_tokens = 64 + 32 * rework

    cost_usd = (input_tokens * 0.000002 + output_tokens * 0.000008) * (
        1.0 + 0.1 * len(config.control_layers))
    return RunRecord(
        record_id=record_id,
        workload_sha256=workload_sha,
        task_id=task.task_id,
        slice=task.slice,
        config_id=config.config_id,
        repeat=repeat,
        state=state.value,
        correct=correct,
        accepted=accepted,
        fault_label=task.fault_label,
        fault_caught=fault_caught,
        verifier_rejected=verifier_rejected,
        rework_attempts=rework,
        conflicts=conflicts,
        latency_ms=round(latency, 3),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=round(cost_usd, 8),
        evidence_level=evidence_level,
        aborted=aborted,
        abort_reason="scripted_engine_abort" if aborted else None,
    )


def run_study(workload: FrozenWorkload, *, repeats: int = MIN_REPEATS,
              slice_name: str = "evaluation",
              configs: tuple[ExperimentConfig, ...] = CONFIGURATIONS,
              evidence_level: str = "development_fixture") -> list[RunRecord]:
    """Run every configuration ``repeats`` times per workload slice (EVAL-R4)."""
    if repeats < MIN_REPEATS:
        raise ContractError("each configuration requires at least 3 runs per slice")
    tasks = workload.slice_tasks(slice_name)
    if not tasks:
        raise ContractError("workload slice is empty")
    records: list[RunRecord] = []
    for config in configs:
        for task in tasks:
            for repeat in range(repeats):
                records.append(run_task(config, task, repeat, workload.sha256,
                                        evidence_level))
    return records


# --- Gate C: independent recomputation --------------------------------------

def recompute_from_records(records: list[RunRecord | dict]) -> dict[str, dict[str, float]]:
    """Recompute P(X), P(A), P(X|A) per configuration from raw run records.

    Aborted/UNKNOWN runs stay in every denominator (shared rule 5); P(X)
    counts only independently graded correct artifacts. This function is the
    reproduction path for Gate C and accepts record payloads as well as
    RunRecord instances.
    """
    def field_of(record, name):
        return record[name] if isinstance(record, dict) else getattr(record, name)

    per_config: dict[str, list] = {}
    for record in records:
        per_config.setdefault(field_of(record, "config_id"), []).append(record)
    out: dict[str, dict[str, float]] = {}
    for config_id, rows in per_config.items():
        total = len(rows)
        correct = sum(1 for r in rows if field_of(r, "correct") is True)
        accepted = sum(1 for r in rows if field_of(r, "accepted") is True)
        correct_and_accepted = sum(
            1 for r in rows
            if field_of(r, "correct") is True and field_of(r, "accepted") is True)
        out[config_id] = {
            "n": total,
            # Round to a fixed precision (9 dp) so reproduction matches the
            # normalized aggregate report bit-for-bit (Gate C, EVAL-R9).
            "P_X": round(correct / total, 9) if total else math.nan,
            "P_A": round(accepted / total, 9) if total else math.nan,
            "P_X_given_A": (round(correct_and_accepted / accepted, 9)
                            if accepted else math.nan),
        }
    return out
