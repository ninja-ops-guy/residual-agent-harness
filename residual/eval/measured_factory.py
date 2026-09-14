"""Measured SPEC-EVAL-001 runner for approved Factory execution.

The runner deliberately does not synthesize WorkerContracts, approval, verification,
or integration policy from a FrozenWorkload prompt. A caller supplies an execution
adapter that performs the real approved Factory run and returns measured counters plus
signed M3 receipts. This layer owns comparative run control, wall-clock measurement,
receipt-backed engine attribution, and emission into the signed SPEC-EVAL evidence
model.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol, Sequence

from residual.factory.evidence_receipts import WorkerReceipt

from .spec_eval import (
    CostRates,
    ExecutionControls,
    EvaluationRunEvidence,
    RunCounters,
    SignedComparisonReport,
    SpecEvalError,
    SpecEvaluationEvidence,
)
from .workload import FrozenWorkload


@dataclass(frozen=True, slots=True)
class FactoryRunMeasurement:
    """Counters returned by one real Factory configuration run.

    ``elapsed_seconds`` is intentionally absent: the trusted evaluation runner measures
    wall clock around the adapter call so a backend cannot self-report a faster run.
    GPU and coordination time remain adapter measurements because they require runtime
    instrumentation not available to the outer wall-clock observer.
    """

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
    receipts: tuple[WorkerReceipt, ...]

    def __post_init__(self) -> None:
        if not self.receipts:
            raise SpecEvalError("measured Factory evaluation requires signed M3 receipts")
        # Reuse RunCounters validation with a harmless positive elapsed value. The real
        # measured elapsed duration is supplied by MeasuredFactoryEvaluationRunner.
        RunCounters(
            elapsed_seconds=1.0,
            accepted_tasks=self.accepted_tasks,
            total_tasks=self.total_tasks,
            tokens_used=self.tokens_used,
            gpu_seconds=self.gpu_seconds,
            coordination_seconds=min(self.coordination_seconds, 1.0),
            rework_tasks=self.rework_tasks,
            merge_conflicts=self.merge_conflicts,
            verifier_rejections=self.verifier_rejections,
            verifier_outputs=self.verifier_outputs,
            tests_passed=self.tests_passed,
            tests_total=self.tests_total,
        )
        if self.coordination_seconds < 0:
            raise SpecEvalError("coordination_seconds must be nonnegative")


class FactoryEvaluationAdapter(Protocol):
    """Execute one approved Factory experiment configuration.

    Implementations are responsible for mapping the FrozenWorkload into already
    approved Factory plans/contracts and for returning counters from the real runtime,
    verifier, Evidence Bus, integrator, scheduler and test harness.
    """

    def __call__(
        self,
        workload: FrozenWorkload,
        configuration: str,
        run_index: int,
    ) -> FactoryRunMeasurement: ...


@dataclass
class MeasuredFactoryEvaluationRunner:
    workload: FrozenWorkload
    evidence: SpecEvaluationEvidence
    execute: FactoryEvaluationAdapter
    temperatures: tuple[float, ...] = (0.0,)
    seed: int = 20260914
    rates: CostRates = CostRates()
    clock: callable = time.monotonic

    def __post_init__(self) -> None:
        if not isinstance(self.workload, FrozenWorkload) or not self.workload.verify():
            raise SpecEvalError("verified FrozenWorkload required")
        if self.evidence.workload.manifest_hash != self.workload.manifest_hash:
            raise SpecEvalError("evaluation evidence is bound to another FrozenWorkload")
        if not callable(self.execute) or not callable(self.clock):
            raise SpecEvalError("measured evaluation requires execution and clock callables")
        if not self.temperatures:
            raise SpecEvalError("temperature controls required")
        if type(self.seed) is not int:
            raise SpecEvalError("seed must be an integer")

    @staticmethod
    def _validate_receipts(measurement: FactoryRunMeasurement) -> None:
        plan_hashes = {receipt.execution_plan_hash for receipt in measurement.receipts}
        if len(plan_hashes) != 1:
            raise SpecEvalError("one measured run cannot mix Factory execution plans")
        verdicts = {receipt.overall_verdict for receipt in measurement.receipts}
        if verdicts - {"pass", "fail", "unknown"}:
            raise SpecEvalError("measured run contains invalid receipt verdict")
        hashes = [receipt.receipt_hash for receipt in measurement.receipts]
        if len(hashes) != len(set(hashes)):
            raise SpecEvalError("measured run contains duplicate M3 receipts")

    def run_one(self, configuration: str, run_index: int) -> EvaluationRunEvidence:
        if configuration not in {"single", "fixed", "dynamic"}:
            raise SpecEvalError("configuration must be single, fixed, or dynamic")
        started = float(self.clock())
        measurement = self.execute(self.workload, configuration, run_index)
        finished = float(self.clock())
        if not isinstance(measurement, FactoryRunMeasurement):
            raise SpecEvalError("Factory evaluation adapter returned invalid measurement")
        elapsed = finished - started
        if elapsed <= 0:
            raise SpecEvalError("measured Factory wall clock must advance")
        if measurement.coordination_seconds > elapsed:
            raise SpecEvalError("coordination time exceeds trusted measured wall clock")
        self._validate_receipts(measurement)

        controls = ExecutionControls.from_receipts(
            measurement.receipts,
            temperatures=self.temperatures,
            seed=self.seed,
        )
        counters = RunCounters(
            elapsed_seconds=elapsed,
            accepted_tasks=measurement.accepted_tasks,
            total_tasks=measurement.total_tasks,
            tokens_used=measurement.tokens_used,
            gpu_seconds=measurement.gpu_seconds,
            coordination_seconds=measurement.coordination_seconds,
            rework_tasks=measurement.rework_tasks,
            merge_conflicts=measurement.merge_conflicts,
            verifier_rejections=measurement.verifier_rejections,
            verifier_outputs=measurement.verifier_outputs,
            tests_passed=measurement.tests_passed,
            tests_total=measurement.tests_total,
        )
        return self.evidence.record_run(
            configuration,
            run_index,
            counters,
            controls,
            rates=self.rates,
            evidence_mode="measured",
        )

    def run(self, *, runs: int = 3,
            configurations: Sequence[str] = ("single", "fixed", "dynamic"),
            significance_test: str = "mann_whitney_u",
            alpha: float = 0.05) -> SignedComparisonReport:
        if type(runs) is not int or runs < 3:
            raise SpecEvalError("SPEC-EVAL requires at least three measured runs")
        configs = tuple(configurations)
        if len(configs) != 3 or set(configs) != {"single", "fixed", "dynamic"}:
            raise SpecEvalError("measured evaluation requires single, fixed, and dynamic exactly once")
        if self.evidence.minimum_runs > runs:
            raise SpecEvalError("requested runs are below the evidence minimum")

        for configuration in configs:
            for run_index in range(runs):
                self.run_one(configuration, run_index)
        return self.evidence.build_report(
            significance_test=significance_test,
            alpha=alpha,
        )
