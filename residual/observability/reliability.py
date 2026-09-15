"""Observation-first economics and paper metric reconstruction.

Prometheus is deliberately a projection of these retained observations.  It
is never used to make a control decision or to reconstruct a report.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Mapping, Sequence

from ..core import ContractError, canonical, digest, identifier, strict_json


OBSERVATION_SCHEMA = "residual.reliability-observation.v1"
REPORT_SCHEMA = "residual.reliability-report.v1"
AGGREGATE_PRECISION = 9


def _nonnegative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ContractError(f"{name} must be a nonnegative number")
    return float(value)


def _optional_nonnegative(value: object, name: str) -> float | None:
    return None if value is None else _nonnegative(value, name)


def _stable(value: float | None) -> float | None:
    return None if value is None else round(value, AGGREGATE_PRECISION)


def _rate(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else _stable(numerator / denominator)


@dataclass(frozen=True, slots=True)
class TimingBreakdown:
    """Exclusive critical-path buckets plus separate summed resource time.

    The nine phase fields must sum to ``wall_clock_ms``.  Worker and verifier
    resource time may exceed wall time when operations run concurrently and
    therefore are explicitly excluded from that conservation equation.
    """

    planning_ms: float = 0.0
    scheduling_ms: float = 0.0
    context_packaging_ms: float = 0.0
    worker_execution_ms: float = 0.0
    verifier_execution_ms: float = 0.0
    integration_ms: float = 0.0
    retry_rework_ms: float = 0.0
    coordination_ms: float = 0.0
    host_overhead_ms: float = 0.0
    wall_clock_ms: float = 0.0
    worker_resource_ms: float = 0.0
    verifier_resource_ms: float = 0.0

    def __post_init__(self) -> None:
        for item in fields(self):
            _nonnegative(getattr(self, item.name), item.name)
        if abs(self.exclusive_total_ms - self.wall_clock_ms) > 0.001:
            raise ContractError("exclusive timing buckets must equal wall_clock_ms")

    @property
    def exclusive_total_ms(self) -> float:
        return sum(getattr(self, item.name) for item in fields(self)
                   if item.name not in {"wall_clock_ms", "worker_resource_ms",
                                        "verifier_resource_ms"})

    def payload(self) -> dict[str, float]:
        return {item.name: float(getattr(self, item.name)) for item in fields(self)}

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "TimingBreakdown":
        expected = {item.name for item in fields(cls)}
        if set(value) != expected:
            raise ContractError("timing breakdown fields do not match schema")
        return cls(**{key: value[key] for key in expected})  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class CostAccounting:
    """Nullable usage is retained as unknown rather than coerced to zero."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    reasoning_tokens: int | None = None
    api_cost_usd: float | None = None
    local_cpu_ms: float | None = None
    local_gpu_ms: float | None = None
    retries: int = 0
    failed_call_cost_usd: float | None = None

    def __post_init__(self) -> None:
        for name in ("input_tokens", "output_tokens", "cached_tokens",
                     "reasoning_tokens"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ContractError(f"{name} must be a nonnegative integer or null")
        if type(self.retries) is not int or self.retries < 0:
            raise ContractError("retries must be a nonnegative integer")
        for name in ("api_cost_usd", "local_cpu_ms", "local_gpu_ms",
                     "failed_call_cost_usd"):
            _optional_nonnegative(getattr(self, name), name)

    @property
    def usage_complete(self) -> bool:
        return all(getattr(self, name) is not None for name in (
            "input_tokens", "output_tokens", "cached_tokens", "reasoning_tokens"))

    @property
    def cost_complete(self) -> bool:
        return self.api_cost_usd is not None and self.failed_call_cost_usd is not None

    def payload(self) -> dict[str, object]:
        return {item.name: getattr(self, item.name) for item in fields(self)}

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "CostAccounting":
        expected = {item.name for item in fields(cls)}
        if set(value) != expected:
            raise ContractError("cost accounting fields do not match schema")
        return cls(**{key: value[key] for key in expected})  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class ReliabilityObservation:
    observation_id: str
    task_id: str
    task_class: str
    topology: str
    engine_mix: tuple[str, ...]
    worker_count: int
    verifier_family: str
    evidence_size_bytes: int
    terminal_state: str
    correct: bool | None
    accepted: bool
    verifier_rejected: bool
    fault_label: str | None
    fault_caught: bool | None
    conflicts: int
    evidence_complete: bool
    commit_sha: str
    tree_sha: str
    timing: TimingBreakdown
    cost: CostAccounting
    schema_version: str = OBSERVATION_SCHEMA

    def __post_init__(self) -> None:
        for value in (self.observation_id, self.task_id, self.task_class,
                      self.topology, self.verifier_family):
            identifier(value)
        if self.schema_version != OBSERVATION_SCHEMA:
            raise ContractError("unsupported reliability observation schema")
        if not self.engine_mix or any(not isinstance(v, str) or not v for v in self.engine_mix):
            raise ContractError("engine_mix must contain at least one engine")
        if tuple(sorted(set(self.engine_mix))) != self.engine_mix:
            raise ContractError("engine_mix must be sorted and unique")
        if type(self.worker_count) is not int or self.worker_count < 1:
            raise ContractError("worker_count must be positive")
        if type(self.evidence_size_bytes) is not int or self.evidence_size_bytes < 0:
            raise ContractError("evidence_size_bytes must be nonnegative")
        if self.terminal_state not in {"PASS", "FAIL", "REJECTED", "UNKNOWN", "ERROR"}:
            raise ContractError("invalid terminal state")
        if any(type(v) is not bool for v in (
                self.accepted, self.verifier_rejected, self.evidence_complete)):
            raise ContractError("observation flags must be boolean")
        if self.correct is not None and type(self.correct) is not bool:
            raise ContractError("correct must be boolean or null")
        if self.fault_caught is not None and type(self.fault_caught) is not bool:
            raise ContractError("fault_caught must be boolean or null")
        if type(self.conflicts) is not int or self.conflicts < 0:
            raise ContractError("conflicts must be nonnegative")
        for name, value in (("commit_sha", self.commit_sha), ("tree_sha", self.tree_sha)):
            if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
                raise ContractError(f"{name} must be a lowercase git SHA-1")

    @property
    def rework_attempts(self) -> int:
        return self.cost.retries

    def body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "observation_id": self.observation_id,
            "task_id": self.task_id,
            "task_class": self.task_class,
            "topology": self.topology,
            "engine_mix": list(self.engine_mix),
            "worker_count": self.worker_count,
            "verifier_family": self.verifier_family,
            "evidence_size_bytes": self.evidence_size_bytes,
            "terminal_state": self.terminal_state,
            "correct": self.correct,
            "accepted": self.accepted,
            "verifier_rejected": self.verifier_rejected,
            "fault_label": self.fault_label,
            "fault_caught": self.fault_caught,
            "conflicts": self.conflicts,
            "evidence_complete": self.evidence_complete,
            "commit_sha": self.commit_sha,
            "tree_sha": self.tree_sha,
            "timing": self.timing.payload(),
            "cost": self.cost.payload(),
        }

    @property
    def observation_sha256(self) -> str:
        return digest(self.body())

    def payload(self) -> dict[str, object]:
        return {**self.body(), "observation_sha256": self.observation_sha256}

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> "ReliabilityObservation":
        value = strict_json(canonical(dict(raw)))
        claimed = value.pop("observation_sha256", None)
        timing = TimingBreakdown.from_dict(value.pop("timing"))
        cost = CostAccounting.from_dict(value.pop("cost"))
        value["engine_mix"] = tuple(value["engine_mix"])
        result = cls(timing=timing, cost=cost, **value)
        if claimed is not None and claimed != result.observation_sha256:
            raise ContractError("reliability observation hash mismatch")
        return result


def _sum_known(rows: Sequence[ReliabilityObservation], field_name: str) -> int | float | None:
    values = [getattr(row.cost, field_name) for row in rows]
    return None if any(value is None for value in values) else sum(values)  # type: ignore[arg-type]


def _aggregate(rows: Sequence[ReliabilityObservation]) -> dict[str, object]:
    n = len(rows)
    accepted = [r for r in rows if r.accepted]
    correct = [r for r in rows if r.correct is True]
    incorrect = [r for r in rows if r.correct is False]
    accepted_correct = [r for r in accepted if r.correct is True]
    accepted_incorrect = [r for r in accepted if r.correct is False]
    faults = [r for r in rows if r.fault_label is not None]
    latency = [r.timing.wall_clock_ms for r in rows]
    total_wall_seconds = sum(latency) / 1000.0
    state_counts = {state: sum(r.terminal_state == state for r in rows)
                    for state in ("PASS", "FAIL", "REJECTED", "UNKNOWN", "ERROR")}
    timing_totals = {name: _stable(sum(getattr(r.timing, name) for r in rows))
                     for name in TimingBreakdown.__dataclass_fields__}
    api_cost = _sum_known(rows, "api_cost_usd")
    failed_cost = _sum_known(rows, "failed_call_cost_usd")
    cost_total = None if api_cost is None or failed_cost is None else api_cost + failed_cost
    evidence_missing = sum(not r.evidence_complete for r in rows)
    missing_grades = sum(r.correct is None for r in rows)
    return {
        "runs": n,
        "state_counts": state_counts,
        "P_X": _rate(len(correct), n),
        "P_A": _rate(len(accepted), n),
        "P_X_given_A": _rate(len(accepted_correct), len(accepted)),
        "aer_far": _rate(len(accepted_incorrect), len(accepted)),
        "isr": _rate(sum(not r.accepted for r in incorrect), len(incorrect)),
        "assr": _rate(len(accepted_correct), n),
        "acceptance_coverage": _rate(len(accepted), n),
        "false_rejection_rate": _rate(sum(not r.accepted for r in correct), len(correct)),
        "fcr": _rate(sum(r.fault_caught is True for r in faults), len(faults)),
        "throughput_runs_per_sec": _stable(n / total_wall_seconds) if total_wall_seconds else None,
        "latency_ms_mean": _stable(sum(latency) / n),
        "latency_ms_min": _stable(min(latency)),
        "latency_ms_max": _stable(max(latency)),
        "rework_per_run": _stable(sum(r.rework_attempts for r in rows) / n),
        "conflicts_total": sum(r.conflicts for r in rows),
        "conflict_rate": _stable(sum(r.conflicts for r in rows) / n),
        "verifier_rejection_rate": _rate(sum(r.verifier_rejected for r in rows), n),
        "input_tokens": _sum_known(rows, "input_tokens"),
        "output_tokens": _sum_known(rows, "output_tokens"),
        "cached_tokens": _sum_known(rows, "cached_tokens"),
        "reasoning_tokens": _sum_known(rows, "reasoning_tokens"),
        "api_cost_usd": _stable(api_cost),
        "failed_call_cost_usd": _stable(failed_cost),
        "cost_usd_total": _stable(cost_total),
        "local_cpu_ms": _stable(_sum_known(rows, "local_cpu_ms")),
        "local_gpu_ms": _stable(_sum_known(rows, "local_gpu_ms")),
        "timing_totals_ms": timing_totals,
        "completeness": {
            "evidence_complete": n - evidence_missing,
            "evidence_missing": evidence_missing,
            "missing_grades": missing_grades,
            "unknown_usage": sum(not r.cost.usage_complete for r in rows),
            "unknown_cost": sum(not r.cost.cost_complete for r in rows),
        },
    }


def build_reliability_report(
        observations: Sequence[ReliabilityObservation | Mapping[str, object]]) -> dict[str, object]:
    """Rebuild a deterministic report exclusively from retained observations."""
    if not observations:
        raise ContractError("reliability report requires observations")
    rows = [item if isinstance(item, ReliabilityObservation)
            else ReliabilityObservation.from_dict(item) for item in observations]
    if len({r.observation_id for r in rows}) != len(rows):
        raise ContractError("duplicate reliability observation")
    if any(not r.evidence_complete for r in rows):
        # Incomplete executions remain valid denominators.  A missing/corrupt
        # observation document itself is rejected by schema/hash validation.
        pass
    rows.sort(key=lambda r: r.observation_id)
    groups: dict[tuple[str, str], list[ReliabilityObservation]] = {}
    for row in rows:
        groups.setdefault((row.task_class, row.topology), []).append(row)
    aggregates = []
    for (task_class, topology), grouped in sorted(groups.items()):
        aggregates.append({"task_class": task_class, "topology": topology,
                           **_aggregate(grouped)})
    identities = sorted({(r.commit_sha, r.tree_sha) for r in rows})
    body: dict[str, object] = {
        "schema_version": REPORT_SCHEMA,
        "source_schema_version": OBSERVATION_SCHEMA,
        "source_observation_sha256": [r.observation_sha256 for r in rows],
        "source_identities": [
            {"commit_sha": commit, "tree_sha": tree} for commit, tree in identities],
        "aggregates": aggregates,
        "overall": _aggregate(rows),
    }
    body["report_sha256"] = digest(body)
    return body


def pareto_inputs(report: Mapping[str, object]) -> dict[str, object]:
    if report.get("schema_version") != REPORT_SCHEMA:
        raise ContractError("invalid reliability report")
    points = []
    for row in report["aggregates"]:  # type: ignore[index]
        points.append({
            "task_class": row["task_class"],
            "topology": row["topology"],
            "reliability": row["assr"],
            "cost_usd": row["cost_usd_total"],
            "latency_ms": row["latency_ms_mean"],
            "accepted_throughput": (
                None if row["throughput_runs_per_sec"] is None
                else _stable(row["throughput_runs_per_sec"] * row["assr"])),
        })
    return {
        "schema_version": "residual.pareto-inputs.v1",
        "source_report_sha256": report["report_sha256"],
        "points": points,
        "pareto_sha256": digest(points),
    }
