"""Measured R0-R5 experiment contract for RESIDUAL-ABLATION-001.

This module is deliberately separate from residual.eval_frozen: the frozen
package remains a deterministic development fixture.  This lane only accepts
measurements returned by an explicit execution adapter and labels them
measured_live.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from residual.core import ContractError, digest
from residual.eval_frozen.configs import CONFIGURATIONS, ExperimentConfig
from residual.eval_frozen.workload import FrozenTask, FrozenWorkload

PROTOCOL_SCHEMA = "residual.research.ablation001.protocol.v1"
EXECUTION_SCHEMA = "residual.research.ablation001.execution.v1"
BUNDLE_SCHEMA = "residual.research.ablation001.bundle.v1"
MIN_REPEATS = 3
TERMINAL_STATES = frozenset({"PASS", "FAIL", "REJECTED", "UNKNOWN"})


def _hash(value: str, name: str, length: int = 64) -> str:
    if not isinstance(value, str) or len(value) != length:
        raise ContractError(f"invalid {name}")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ContractError(f"invalid {name}") from exc
    return value


def _nonnegative_int(value: int, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ContractError(f"{name} must be a nonnegative integer")
    return value


def _nonnegative_float(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ContractError(f"{name} must be nonnegative")
    return float(value)


@dataclass(frozen=True, slots=True)
class AblationProtocol:
    workload_sha256: str
    protocol_id: str = "RESIDUAL-ABLATION-001"
    protocol_version: int = 1
    config_ids: tuple[str, ...] = tuple(c.config_id for c in CONFIGURATIONS)
    primary_endpoint: str = "accepted_and_sound_rate"
    safety_endpoint: str = "unsafe_acceptance_rate"
    minimum_repeats: int = MIN_REPEATS
    alpha: float = 0.05
    missingness_rule: str = "UNKNOWN retained in all unconditional denominators"
    stopping_rule: str = "no outcome-dependent early stopping"
    contamination_guard: tuple[str, ...] = (
        "do not read or modify sealed AX/SLM outcomes during execution",
        "do not tune workload verifier thresholds or endpoints after outcome access",
        "do not relabel development_fixture evidence as measured evidence",
    )

    def __post_init__(self) -> None:
        _hash(self.workload_sha256, "workload_sha256")
        if not self.protocol_id.strip():
            raise ContractError("protocol_id required")
        if type(self.protocol_version) is not int or self.protocol_version < 1:
            raise ContractError("protocol_version must be positive")
        if self.config_ids != tuple(c.config_id for c in CONFIGURATIONS):
            raise ContractError("canonical ordered R0-R5 arms required")
        if type(self.minimum_repeats) is not int or self.minimum_repeats < MIN_REPEATS:
            raise ContractError("minimum_repeats must be at least three")
        if not 0.0 < float(self.alpha) < 1.0:
            raise ContractError("alpha must be between zero and one")

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": PROTOCOL_SCHEMA,
            "protocol_id": self.protocol_id,
            "protocol_version": self.protocol_version,
            "workload_sha256": self.workload_sha256,
            "config_ids": list(self.config_ids),
            "primary_endpoint": self.primary_endpoint,
            "safety_endpoint": self.safety_endpoint,
            "minimum_repeats": self.minimum_repeats,
            "alpha": self.alpha,
            "missingness_rule": self.missingness_rule,
            "stopping_rule": self.stopping_rule,
            "contamination_guard": list(self.contamination_guard),
        }

    @property
    def sha256(self) -> str:
        return digest(self.payload())


@dataclass(frozen=True, slots=True)
class ControlledFactors:
    provider: str
    model_id: str
    model_version: str
    prompt_policy_sha256: str
    inference_settings_sha256: str
    tool_environment_sha256: str
    grader_id: str
    grader_version: str
    environment_sha256: str
    budget_policy_sha256: str

    def __post_init__(self) -> None:
        for name in ("provider", "model_id", "model_version", "grader_id", "grader_version"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ContractError(f"{name} required")
        for name in (
            "prompt_policy_sha256", "inference_settings_sha256",
            "tool_environment_sha256", "environment_sha256", "budget_policy_sha256",
        ):
            _hash(getattr(self, name), name)

    def payload(self) -> dict[str, str]:
        return {
            "provider": self.provider,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "prompt_policy_sha256": self.prompt_policy_sha256,
            "inference_settings_sha256": self.inference_settings_sha256,
            "tool_environment_sha256": self.tool_environment_sha256,
            "grader_id": self.grader_id,
            "grader_version": self.grader_version,
            "environment_sha256": self.environment_sha256,
            "budget_policy_sha256": self.budget_policy_sha256,
        }

    @property
    def sha256(self) -> str:
        return digest(self.payload())


@dataclass(frozen=True, slots=True)
class ExecutionManifest:
    protocol_sha256: str
    workload_sha256: str
    source_commit: str
    factors: ControlledFactors
    config_hashes: tuple[tuple[str, str], ...] = tuple(
        (c.config_id, c.sha256) for c in CONFIGURATIONS
    )
    evidence_level: str = "measured_live"

    def __post_init__(self) -> None:
        _hash(self.protocol_sha256, "protocol_sha256")
        _hash(self.workload_sha256, "workload_sha256")
        _hash(self.source_commit, "source_commit", 40)
        if not isinstance(self.factors, ControlledFactors):
            raise ContractError("ControlledFactors required")
        expected = tuple((c.config_id, c.sha256) for c in CONFIGURATIONS)
        if self.config_hashes != expected:
            raise ContractError("execution manifest must bind canonical R0-R5 hashes")
        if self.evidence_level != "measured_live":
            raise ContractError("measured campaign must use evidence_level='measured_live'")

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": EXECUTION_SCHEMA,
            "protocol_sha256": self.protocol_sha256,
            "workload_sha256": self.workload_sha256,
            "source_commit": self.source_commit,
            "factors": self.factors.payload(),
            "factors_sha256": self.factors.sha256,
            "config_hashes": [
                {"config_id": key, "sha256": value} for key, value in self.config_hashes
            ],
            "evidence_level": self.evidence_level,
        }

    @property
    def sha256(self) -> str:
        return digest(self.payload())


@dataclass(frozen=True, slots=True)
class TaskMeasurement:
    """Adapter output for one cell. Identity is bound by the outer runner."""

    state: str
    correct: bool | None
    accepted: bool
    fault_caught: bool | None
    verifier_rejected: bool
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    rework_attempts: int = 0
    conflicts: int = 0
    operator_interventions: int = 0
    recovery_attempts: int = 0
    recovered_failures: int = 0
    duplicate_work_items: int = 0
    unauthorized_actions: int = 0
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.state not in TERMINAL_STATES:
            raise ContractError("invalid measured state")
        if self.correct is not None and type(self.correct) is not bool:
            raise ContractError("correct must be bool or None")
        if type(self.accepted) is not bool or type(self.verifier_rejected) is not bool:
            raise ContractError("accepted/verifier_rejected must be bool")
        if self.fault_caught is not None and type(self.fault_caught) is not bool:
            raise ContractError("fault_caught must be bool or None")
        _nonnegative_float(self.latency_ms, "latency_ms")
        _nonnegative_float(self.cost_usd, "cost_usd")
        for name in (
            "input_tokens", "output_tokens", "rework_attempts", "conflicts",
            "operator_interventions", "recovery_attempts", "recovered_failures",
            "duplicate_work_items", "unauthorized_actions",
        ):
            _nonnegative_int(getattr(self, name), name)
        if self.state == "UNKNOWN" and (self.correct is not None or self.accepted):
            raise ContractError("UNKNOWN requires correct=None and accepted=False")
        if self.state == "PASS" and (self.correct is not True or not self.accepted):
            raise ContractError("PASS requires correct=True and accepted=True")
        if self.state == "FAIL" and (self.correct is not False or not self.accepted):
            raise ContractError("FAIL requires correct=False and accepted=True")
        if self.state == "REJECTED" and self.accepted:
            raise ContractError("REJECTED cannot be accepted")
        if not self.evidence_refs:
            raise ContractError("retained evidence reference required")
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ContractError("duplicate evidence reference")
        if any(not isinstance(ref, str) or not ref.strip() for ref in self.evidence_refs):
            raise ContractError("invalid evidence reference")


class MeasuredAblationAdapter(Protocol):
    def __call__(
        self,
        workload: FrozenWorkload,
        config: ExperimentConfig,
        task: FrozenTask,
        repeat: int,
        execution: ExecutionManifest,
    ) -> TaskMeasurement: ...


@dataclass(frozen=True, slots=True)
class MeasuredObservation:
    record_id: str
    protocol_sha256: str
    execution_sha256: str
    workload_sha256: str
    task_id: str
    slice: str
    config_id: str
    repeat: int
    state: str
    correct: bool | None
    accepted: bool
    fault_label: str | None
    fault_caught: bool | None
    verifier_rejected: bool
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    rework_attempts: int
    conflicts: int
    operator_interventions: int
    recovery_attempts: int
    recovered_failures: int
    duplicate_work_items: int
    unauthorized_actions: int
    evidence_refs: tuple[str, ...]

    def payload(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "protocol_sha256": self.protocol_sha256,
            "execution_sha256": self.execution_sha256,
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
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "rework_attempts": self.rework_attempts,
            "conflicts": self.conflicts,
            "operator_interventions": self.operator_interventions,
            "recovery_attempts": self.recovery_attempts,
            "recovered_failures": self.recovered_failures,
            "duplicate_work_items": self.duplicate_work_items,
            "unauthorized_actions": self.unauthorized_actions,
            "evidence_refs": list(self.evidence_refs),
        }


def _rate(num: int, den: int) -> float | None:
    return round(num / den, 9) if den else None


def summarize_observations(
    records: Sequence[MeasuredObservation],
) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for config in CONFIGURATIONS:
        rows = [r for r in records if r.config_id == config.config_id]
        if not rows:
            raise ContractError(f"missing observations for {config.config_id}")
        n = len(rows)
        accepted = [r for r in rows if r.accepted]
        correct = [r for r in rows if r.correct is True]
        incorrect = [r for r in rows if r.correct is False]
        accepted_correct = [r for r in accepted if r.correct is True]
        accepted_incorrect = [r for r in accepted if r.correct is False]
        faults = [r for r in rows if r.fault_label is not None]
        out[config.config_id] = {
            "runs": n,
            "unknown_runs": sum(r.state == "UNKNOWN" for r in rows),
            "accepted_and_sound_rate": _rate(len(accepted_correct), n),
            "unsafe_acceptance_rate": _rate(len(accepted_incorrect), n),
            "false_acceptance_rate": _rate(len(accepted_incorrect), len(accepted)),
            "acceptance_coverage": _rate(len(accepted), n),
            "raw_correctness_rate": _rate(len(correct), n),
            "incorrect_suppression_rate": _rate(
                sum(not r.accepted for r in incorrect), len(incorrect)
            ),
            "false_rejection_rate": _rate(
                sum(not r.accepted for r in correct), len(correct)
            ),
            "fault_capture_rate": (
                _rate(sum(r.fault_caught is True for r in faults), len(faults))
                if faults else None
            ),
            "latency_ms_mean": round(sum(r.latency_ms for r in rows) / n, 9),
            "input_tokens": sum(r.input_tokens for r in rows),
            "output_tokens": sum(r.output_tokens for r in rows),
            "cost_usd_total": round(sum(r.cost_usd for r in rows), 9),
            "rework_attempts": sum(r.rework_attempts for r in rows),
            "conflicts": sum(r.conflicts for r in rows),
            "operator_interventions": sum(r.operator_interventions for r in rows),
            "recovery_attempts": sum(r.recovery_attempts for r in rows),
            "recovered_failures": sum(r.recovered_failures for r in rows),
            "duplicate_work_items": sum(r.duplicate_work_items for r in rows),
            "unauthorized_actions": sum(r.unauthorized_actions for r in rows),
        }
    return out


def build_bundle(
    protocol: AblationProtocol,
    execution: ExecutionManifest,
    records: Sequence[MeasuredObservation],
) -> dict[str, object]:
    rows = list(records)
    if not rows:
        raise ContractError("measured bundle requires observations")
    for row in rows:
        if row.protocol_sha256 != protocol.sha256:
            raise ContractError("observation bound to another protocol")
        if row.execution_sha256 != execution.sha256:
            raise ContractError("observation bound to another execution")
        if row.workload_sha256 != protocol.workload_sha256:
            raise ContractError("observation bound to another workload")
    payload = {
        "schema_version": BUNDLE_SCHEMA,
        "evidence_level": execution.evidence_level,
        "protocol": protocol.payload(),
        "protocol_sha256": protocol.sha256,
        "execution": execution.payload(),
        "execution_sha256": execution.sha256,
        "records": [r.payload() for r in rows],
        "summaries": summarize_observations(rows),
    }
    return {**payload, "bundle_sha256": digest(payload)}


def verify_bundle(bundle: dict[str, object]) -> bool:
    if not isinstance(bundle, dict) or bundle.get("schema_version") != BUNDLE_SCHEMA:
        return False
    supplied = bundle.get("bundle_sha256")
    payload = {k: v for k, v in bundle.items() if k != "bundle_sha256"}
    return isinstance(supplied, str) and digest(payload) == supplied


@dataclass
class MeasuredAblationRunner:
    workload: FrozenWorkload
    protocol: AblationProtocol
    execution: ExecutionManifest
    execute: MeasuredAblationAdapter

    def __post_init__(self) -> None:
        if not isinstance(self.workload, FrozenWorkload):
            raise ContractError("FrozenWorkload required")
        if self.workload.sha256 != self.protocol.workload_sha256:
            raise ContractError("protocol bound to another workload")
        if self.execution.protocol_sha256 != self.protocol.sha256:
            raise ContractError("execution bound to another protocol")
        if self.execution.workload_sha256 != self.workload.sha256:
            raise ContractError("execution bound to another workload")
        if not callable(self.execute):
            raise ContractError("measured adapter must be callable")

    def run(
        self,
        *,
        repeats: int | None = None,
        slice_name: str = "evaluation",
        configs: Sequence[ExperimentConfig] = CONFIGURATIONS,
    ) -> dict[str, object]:
        repeats = self.protocol.minimum_repeats if repeats is None else repeats
        if type(repeats) is not int or repeats < self.protocol.minimum_repeats:
            raise ContractError("campaign below pre-registered repeat floor")
        ordered = tuple(configs)
        if tuple(c.config_id for c in ordered) != self.protocol.config_ids:
            raise ContractError("canonical ordered R0-R5 arms required")
        tasks = self.workload.slice_tasks(slice_name)
        if not tasks:
            raise ContractError("selected workload slice is empty")

        records: list[MeasuredObservation] = []
        for config in ordered:
            for task in tasks:
                for repeat in range(repeats):
                    m = self.execute(self.workload, config, task, repeat, self.execution)
                    if not isinstance(m, TaskMeasurement):
                        raise ContractError("adapter returned invalid measurement")
                    if task.fault_label is None and m.fault_caught is not None:
                        raise ContractError("fault_caught only valid for fault-labeled tasks")
                    if task.fault_label is not None and m.state != "UNKNOWN" and m.fault_caught is None:
                        raise ContractError("completed fault-labeled run requires fault_caught")
                    record_id = digest({
                        "protocol_sha256": self.protocol.sha256,
                        "execution_sha256": self.execution.sha256,
                        "task_id": task.task_id,
                        "config_id": config.config_id,
                        "repeat": repeat,
                    })
                    records.append(MeasuredObservation(
                        record_id=record_id,
                        protocol_sha256=self.protocol.sha256,
                        execution_sha256=self.execution.sha256,
                        workload_sha256=self.workload.sha256,
                        task_id=task.task_id,
                        slice=task.slice,
                        config_id=config.config_id,
                        repeat=repeat,
                        state=m.state,
                        correct=m.correct,
                        accepted=m.accepted,
                        fault_label=task.fault_label,
                        fault_caught=m.fault_caught,
                        verifier_rejected=m.verifier_rejected,
                        latency_ms=float(m.latency_ms),
                        input_tokens=m.input_tokens,
                        output_tokens=m.output_tokens,
                        cost_usd=float(m.cost_usd),
                        rework_attempts=m.rework_attempts,
                        conflicts=m.conflicts,
                        operator_interventions=m.operator_interventions,
                        recovery_attempts=m.recovery_attempts,
                        recovered_failures=m.recovered_failures,
                        duplicate_work_items=m.duplicate_work_items,
                        unauthorized_actions=m.unauthorized_actions,
                        evidence_refs=m.evidence_refs,
                    ))

        expected = {
            (task.task_id, repeat, config_id)
            for task in tasks
            for repeat in range(repeats)
            for config_id in self.protocol.config_ids
        }
        actual = {(r.task_id, r.repeat, r.config_id) for r in records}
        if actual != expected or len(records) != len(expected):
            raise ContractError("campaign is not a complete paired R0-R5 block")
        return build_bundle(self.protocol, self.execution, records)
