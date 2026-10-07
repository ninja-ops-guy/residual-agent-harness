"""SPEC-EVAL-001 evidence model for M4 comparative evaluation.

This module does not replace the older T10 simulator/report package. It adds the
system-level evidence contract required by SPEC-EVAL-001: the nine prescribed
metrics, run controls, cost analysis, observation-log derivability, statistical
comparisons, and a Station-signed ComparisonReport.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from observation_layer import Observation, ObservationBus, ObservationKind
from residual.core import digest
from residual.factory.evidence_receipts import (
    SIGNATURE_DOMAIN,
    StationIdentity,
    WorkerReceipt,
    _sha256,
)

from .stats import compare_samples, summary_stats
from .workload import FrozenWorkload

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # pragma: no cover
    InvalidSignature = None
    Ed25519PublicKey = None


SPEC_EVAL_SCHEMA = "residual.eval.spec001.v1"
REPORT_SCHEMA = "residual.eval.comparison-report.v1"
RUN_EVENT = "SpecEvalRunMeasured"
REPORT_EVENT = "SpecEvalReportIssued"
METRIC_NAMES = (
    "elapsed_time_minutes",
    "accepted_tasks_per_hour",
    "token_cost_total",
    "gpu_time_minutes",
    "coordination_overhead_pct",
    "rework_rate_pct",
    "merge_conflicts",
    "verifier_rejection_rate_pct",
    "final_test_pass_rate_pct",
)


class SpecEvalError(ValueError):
    pass


def _nonnegative(value: float | int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise SpecEvalError(f"{name} must be nonnegative")


@dataclass(frozen=True, slots=True)
class RunCounters:
    elapsed_seconds: float
    accepted_tasks: int
    total_tasks: int
    tokens_used: int
    gpu_seconds: float
    coordination_seconds: float
    rework_tasks: int
    merge_conflicts: int
    verifier_rejections: int
    verifier_outputs: int
    tests_passed: int
    tests_total: int

    def __post_init__(self) -> None:
        for name in ("elapsed_seconds", "gpu_seconds", "coordination_seconds"):
            _nonnegative(getattr(self, name), name)
        for name in (
            "accepted_tasks", "total_tasks", "tokens_used", "rework_tasks",
            "merge_conflicts", "verifier_rejections", "verifier_outputs",
            "tests_passed", "tests_total",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise SpecEvalError(f"{name} must be a nonnegative integer")
        if self.elapsed_seconds <= 0:
            raise SpecEvalError("elapsed_seconds must be positive")
        if self.total_tasks < 1 or self.accepted_tasks > self.total_tasks:
            raise SpecEvalError("accepted_tasks outside total_tasks")
        if self.rework_tasks > self.total_tasks:
            raise SpecEvalError("rework_tasks outside total_tasks")
        if self.verifier_outputs < self.verifier_rejections:
            raise SpecEvalError("verifier_rejections exceed outputs")
        if self.tests_total < 1 or self.tests_passed > self.tests_total:
            raise SpecEvalError("tests_passed outside tests_total")
        if self.coordination_seconds > self.elapsed_seconds:
            raise SpecEvalError("coordination time exceeds elapsed time")

    def to_dict(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "RunCounters":
        return cls(**{name: data[name] for name in cls.__dataclass_fields__})  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class SystemMetrics:
    elapsed_time_minutes: float
    accepted_tasks_per_hour: float
    token_cost_total: int
    gpu_time_minutes: float
    coordination_overhead_pct: float
    rework_rate_pct: float
    merge_conflicts: int
    verifier_rejection_rate_pct: float
    final_test_pass_rate_pct: float

    @classmethod
    def from_counters(cls, counters: RunCounters) -> "SystemMetrics":
        return cls(
            elapsed_time_minutes=counters.elapsed_seconds / 60.0,
            accepted_tasks_per_hour=counters.accepted_tasks / (counters.elapsed_seconds / 3600.0),
            token_cost_total=counters.tokens_used,
            gpu_time_minutes=counters.gpu_seconds / 60.0,
            coordination_overhead_pct=100.0 * counters.coordination_seconds / counters.elapsed_seconds,
            rework_rate_pct=100.0 * counters.rework_tasks / counters.total_tasks,
            merge_conflicts=counters.merge_conflicts,
            verifier_rejection_rate_pct=(
                100.0 * counters.verifier_rejections / counters.verifier_outputs
                if counters.verifier_outputs else 0.0
            ),
            final_test_pass_rate_pct=100.0 * counters.tests_passed / counters.tests_total,
        )

    def to_dict(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in METRIC_NAMES}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "SystemMetrics":
        return cls(**{name: data[name] for name in METRIC_NAMES})  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class CostRates:
    api_cost_per_1k_tokens: float = 0.0
    gpu_cost_per_hour: float = 0.0
    infrastructure_cost_per_run: float = 0.0

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            _nonnegative(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class CostAnalysis:
    api_cost: float
    gpu_cost: float
    infrastructure_cost: float
    total_cost: float
    cost_per_accepted_task: float | None

    @classmethod
    def calculate(cls, counters: RunCounters, rates: CostRates) -> "CostAnalysis":
        api = counters.tokens_used / 1000.0 * rates.api_cost_per_1k_tokens
        gpu = counters.gpu_seconds / 3600.0 * rates.gpu_cost_per_hour
        infra = rates.infrastructure_cost_per_run
        total = api + gpu + infra
        per_task = total / counters.accepted_tasks if counters.accepted_tasks else None
        return cls(api, gpu, infra, total, per_task)

    def to_dict(self) -> dict[str, object]:
        return {
            "api_cost": self.api_cost,
            "gpu_cost": self.gpu_cost,
            "infrastructure_cost": self.infrastructure_cost,
            "total_cost": self.total_cost,
            "cost_per_accepted_task": self.cost_per_accepted_task,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "CostAnalysis":
        return cls(
            api_cost=float(data["api_cost"]),
            gpu_cost=float(data["gpu_cost"]),
            infrastructure_cost=float(data["infrastructure_cost"]),
            total_cost=float(data["total_cost"]),
            cost_per_accepted_task=(
                None if data.get("cost_per_accepted_task") is None
                else float(data["cost_per_accepted_task"])
            ),
        )


@dataclass(frozen=True, slots=True)
class ExecutionControls:
    engine_ids: tuple[str, ...]
    model_versions: tuple[str, ...]
    temperatures: tuple[float, ...]
    seed: int

    def __post_init__(self) -> None:
        if not self.engine_ids or not self.model_versions:
            raise SpecEvalError("engine and model controls required")
        if any(not isinstance(value, str) or not value.strip() for value in self.engine_ids + self.model_versions):
            raise SpecEvalError("engine/model identities must be nonempty strings")
        if not self.temperatures:
            raise SpecEvalError("temperature controls required")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in self.temperatures):
            raise SpecEvalError("temperatures must be numeric")
        if type(self.seed) is not int:
            raise SpecEvalError("seed must be an integer")

    def to_dict(self) -> dict[str, object]:
        return {
            "engine_ids": list(self.engine_ids),
            "model_versions": list(self.model_versions),
            "temperatures": list(self.temperatures),
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "ExecutionControls":
        return cls(
            engine_ids=tuple(str(x) for x in data["engine_ids"]),  # type: ignore[index]
            model_versions=tuple(str(x) for x in data["model_versions"]),  # type: ignore[index]
            temperatures=tuple(float(x) for x in data["temperatures"]),  # type: ignore[index]
            seed=int(data["seed"]),
        )

    @classmethod
    def from_receipts(cls, receipts: Sequence[WorkerReceipt], *,
                      temperatures: Sequence[float], seed: int) -> "ExecutionControls":
        """Bind EVAL-R3 engine controls to signed M3 receipt attribution.

        Residual receipts expose engine name/version. The engine version is therefore
        the strongest receipt-backed model revision available at this boundary; a
        provider adapter that distinguishes model revision separately can include that
        revision in its engine version string.
        """
        if not receipts:
            raise SpecEvalError("receipt-backed controls require at least one receipt")
        engines = tuple(sorted({f"{r.engine_name}@{r.engine_version}" for r in receipts}))
        revisions = tuple(sorted({r.engine_version for r in receipts}))
        return cls(
            engine_ids=engines,
            model_versions=revisions,
            temperatures=tuple(float(value) for value in temperatures),
            seed=seed,
        )


@dataclass(frozen=True, slots=True)
class EvaluationRunEvidence:
    configuration: str
    run_index: int
    workload_hash: str
    evidence_mode: str
    controls: ExecutionControls
    counters: RunCounters
    metrics: SystemMetrics
    costs: CostAnalysis

    def __post_init__(self) -> None:
        if self.configuration not in {"single", "fixed", "dynamic"}:
            raise SpecEvalError("configuration must be single, fixed, or dynamic")
        if type(self.run_index) is not int or self.run_index < 0:
            raise SpecEvalError("run_index must be nonnegative")
        if self.evidence_mode not in {"measured", "simulated"}:
            raise SpecEvalError("evidence_mode must be measured or simulated")
        if len(self.workload_hash) != 64 or any(c not in "0123456789abcdef" for c in self.workload_hash):
            raise SpecEvalError("invalid workload hash")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": SPEC_EVAL_SCHEMA,
            "configuration": self.configuration,
            "run_index": self.run_index,
            "workload_hash": self.workload_hash,
            "evidence_mode": self.evidence_mode,
            "controls": self.controls.to_dict(),
            "counters": self.counters.to_dict(),
            "metrics": self.metrics.to_dict(),
            "costs": self.costs.to_dict(),
        }

    @property
    def run_hash(self) -> str:
        return digest(self.to_dict())

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "EvaluationRunEvidence":
        if data.get("schema_version") != SPEC_EVAL_SCHEMA:
            raise SpecEvalError("unsupported SPEC-EVAL run schema")
        return cls(
            configuration=str(data["configuration"]),
            run_index=int(data["run_index"]),
            workload_hash=str(data["workload_hash"]),
            evidence_mode=str(data["evidence_mode"]),
            controls=ExecutionControls.from_dict(data["controls"]),  # type: ignore[arg-type]
            counters=RunCounters.from_dict(data["counters"]),  # type: ignore[arg-type]
            metrics=SystemMetrics.from_dict(data["metrics"]),  # type: ignore[arg-type]
            costs=CostAnalysis.from_dict(data["costs"]),  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class SignedComparisonReport:
    payload: Mapping[str, object]
    station_key_id: str
    station_signature: str

    @property
    def report_hash(self) -> str:
        return digest(self.payload)

    def to_dict(self) -> dict[str, object]:
        return {
            **dict(self.payload),
            "report_hash": self.report_hash,
            "station_key_id": self.station_key_id,
            "station_signature": self.station_signature,
        }

    def verify_signature(self, public_key: bytes) -> bool:
        if Ed25519PublicKey is None or len(public_key) != 32:
            return False
        if _sha256(public_key) != self.station_key_id:
            return False
        try:
            Ed25519PublicKey.from_public_bytes(public_key).verify(
                bytes.fromhex(self.station_signature),
                SIGNATURE_DOMAIN + self.report_hash.encode("ascii"),
            )
            return True
        except (ValueError, InvalidSignature):
            return False


class SpecEvaluationEvidence:
    def __init__(self, workload: FrozenWorkload, station_identity: StationIdentity,
                 *, observation_bus: ObservationBus | None = None,
                 minimum_runs: int = 3) -> None:
        if not isinstance(workload, FrozenWorkload) or not workload.verify():
            raise SpecEvalError("verified FrozenWorkload required")
        if not isinstance(station_identity, StationIdentity):
            raise SpecEvalError("StationIdentity required")
        if type(minimum_runs) is not int or minimum_runs < 3:
            raise SpecEvalError("SPEC-EVAL requires at least three runs")
        self.workload = workload
        self.identity = station_identity
        self.bus = observation_bus
        self.minimum_runs = minimum_runs
        self._runs: list[EvaluationRunEvidence] = []

    def _emit(self, event: str, payload: Mapping[str, object]) -> Observation | None:
        if self.bus is None:
            return None
        observation = self.bus.emit(
            ObservationKind.CUSTOM,
            {"event": event, **dict(payload)},
            tags={"component": "spec-eval-001"},
            source="residual.eval.spec_eval",
        )
        if observation is None:
            raise SpecEvalError("observation delivery failed")
        return observation

    def record_run(self, configuration: str, run_index: int, counters: RunCounters,
                   controls: ExecutionControls, *, rates: CostRates | None = None,
                   evidence_mode: str = "measured") -> EvaluationRunEvidence:
        if any(run.configuration == configuration and run.run_index == run_index for run in self._runs):
            raise SpecEvalError("duplicate configuration/run_index")
        metrics = SystemMetrics.from_counters(counters)
        costs = CostAnalysis.calculate(counters, rates or CostRates())
        run = EvaluationRunEvidence(
            configuration=configuration,
            run_index=run_index,
            workload_hash=self.workload.manifest_hash,
            evidence_mode=evidence_mode,
            controls=controls,
            counters=counters,
            metrics=metrics,
            costs=costs,
        )
        self._runs.append(run)
        self._emit(RUN_EVENT, {"run": run.to_dict(), "run_hash": run.run_hash})
        return run

    @staticmethod
    def _validate_controls(runs: Sequence[EvaluationRunEvidence]) -> None:
        controls = [run.controls.to_dict() for run in runs]
        if controls and any(value != controls[0] for value in controls[1:]):
            raise SpecEvalError("model/engine/temperature/seed controls differ across runs")

    def build_report(self, runs: Sequence[EvaluationRunEvidence] | None = None,
                     *, significance_test: str = "mann_whitney_u",
                     alpha: float = 0.05) -> SignedComparisonReport:
        records = tuple(self._runs if runs is None else runs)
        if not records:
            raise SpecEvalError("no evaluation runs recorded")
        if any(run.workload_hash != self.workload.manifest_hash for run in records):
            raise SpecEvalError("evaluation runs use different FrozenWorkloads")
        by_config: dict[str, list[EvaluationRunEvidence]] = {}
        for run in records:
            by_config.setdefault(run.configuration, []).append(run)
        required = {"single", "fixed", "dynamic"}
        if set(by_config) != required:
            raise SpecEvalError("SPEC-EVAL requires single, fixed, and dynamic configurations")
        if any(len(group) < self.minimum_runs for group in by_config.values()):
            raise SpecEvalError("insufficient runs for one or more configurations")
        for group in by_config.values():
            indexes = [run.run_index for run in group]
            if len(set(indexes)) != len(indexes):
                raise SpecEvalError("duplicate run index in configuration")
        self._validate_controls(records)

        summaries: dict[str, object] = {}
        for config in sorted(by_config):
            group = sorted(by_config[config], key=lambda run: run.run_index)
            accepted_total = sum(run.counters.accepted_tasks for run in group)
            total_cost = sum(run.costs.total_cost for run in group)
            summaries[config] = {
                "runs": len(group),
                "evidence_modes": sorted({run.evidence_mode for run in group}),
                "metrics": {
                    metric: summary_stats([float(getattr(run.metrics, metric)) for run in group])
                    for metric in METRIC_NAMES
                },
                "costs": {
                    metric: summary_stats([float(getattr(run.costs, metric)) for run in group])
                    for metric in ("api_cost", "gpu_cost", "infrastructure_cost", "total_cost")
                },
                "aggregate_cost_per_accepted_task": (
                    total_cost / accepted_total if accepted_total else None
                ),
            }

        comparisons: list[dict[str, object]] = []
        for left, right in itertools.combinations(sorted(by_config), 2):
            for metric in METRIC_NAMES:
                comparison = compare_samples(
                    metric,
                    left,
                    [float(getattr(run.metrics, metric)) for run in by_config[left]],
                    right,
                    [float(getattr(run.metrics, metric)) for run in by_config[right]],
                    test=significance_test,
                    alpha=alpha,
                )
                comparisons.append(comparison.to_dict())

        ordered = sorted(records, key=lambda value: (value.configuration, value.run_index))
        payload: dict[str, object] = {
            "schema_version": REPORT_SCHEMA,
            "workload": self.workload.manifest(),
            "minimum_runs": self.minimum_runs,
            "run_count": len(records),
            "controls": records[0].controls.to_dict(),
            "summaries": summaries,
            "comparisons": comparisons,
            "cost_analysis": {
                "definition": {
                    "api_cost": "tokens_used/1000 * api_cost_per_1k_tokens",
                    "gpu_cost": "gpu_seconds/3600 * gpu_cost_per_hour",
                    "infrastructure_cost": "configured per-run infrastructure cost",
                    "cost_per_accepted_task": "total cost / accepted tasks",
                },
                "per_run": [
                    {
                        "configuration": run.configuration,
                        "run_index": run.run_index,
                        **run.costs.to_dict(),
                    }
                    for run in ordered
                ],
            },
            "run_hashes": [run.run_hash for run in ordered],
            "observation_derivable": True,
        }
        report_hash = digest(payload)
        report = SignedComparisonReport(
            payload=payload,
            station_key_id=self.identity.key_id,
            station_signature=self.identity.sign(report_hash),
        )
        # Do not copy the full report into the observation spine. Nine metrics x all
        # pairwise comparisons can exceed the Observation 24 KB ceiling. The run
        # observations are sufficient to rebuild the report; this terminal event only
        # binds the resulting hash/signature to the same trace.
        self._emit(REPORT_EVENT, {
            "report_hash": report.report_hash,
            "station_key_id": report.station_key_id,
            "station_signature": report.station_signature,
            "source_run_hashes": list(payload["run_hashes"]),
            "significance_test": significance_test,
            "alpha": alpha,
        })
        return report

    @classmethod
    def report_from_observations(cls, workload: FrozenWorkload,
                                 station_identity: StationIdentity,
                                 observations: Iterable[Observation], *,
                                 minimum_runs: int = 3,
                                 significance_test: str = "mann_whitney_u",
                                 alpha: float = 0.05) -> SignedComparisonReport:
        events = tuple(observations)
        runs: list[EvaluationRunEvidence] = []
        terminal: Mapping[str, object] | None = None
        for observation in events:
            payload = observation.payload
            if payload.get("event") == RUN_EVENT:
                run = EvaluationRunEvidence.from_dict(payload["run"])
                if payload.get("run_hash") != run.run_hash:
                    raise SpecEvalError("observation run hash mismatch")
                runs.append(run)
            elif payload.get("event") == REPORT_EVENT:
                terminal = payload
        builder = cls(workload, station_identity, minimum_runs=minimum_runs)
        rebuilt = builder.build_report(runs, significance_test=significance_test, alpha=alpha)
        if terminal is not None:
            expected = terminal.get("report_hash")
            if expected != rebuilt.report_hash:
                raise SpecEvalError("terminal observation report hash mismatch")
            if terminal.get("source_run_hashes") != tuple(rebuilt.payload["run_hashes"]):
                # Frozen observation arrays deserialize as tuples.
                raise SpecEvalError("terminal observation run binding mismatch")
        return rebuilt
