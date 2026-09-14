"""Fail-closed authorization and provenance bindings for measured Factory evaluation.

A FrozenWorkload is experimental input, not authorization.  A measured run is
eligible for the publication path only when it is preapproved, its M3 receipts
bind the approved ExecutionPlan, an M4 final-acceptance receipt is signed and
explicitly labelled measured, and the claimed topology is backed by host-owned
scheduler observations.  Attempt count is never used as topology evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence

from residual.core import digest
from residual.factory.evidence_receipts import StationIdentity
from residual.factory.m4_evidence import ReadyDagSnapshot
from residual.factory.m4_integrator import IntegrationReceipt
from residual.factory.m4_scheduler import SchedulerAction, SchedulerMeasurements

from .measured_factory import FactoryRunMeasurement, MeasuredFactoryEvaluationRunner
from .spec_eval import CostRates, SignedComparisonReport, SpecEvalError, SpecEvaluationEvidence
from .workload import FrozenWorkload

_HEX = frozenset("0123456789abcdef")
_CONFIGS = frozenset({"single", "fixed", "dynamic"})
ENVELOPE_SCHEMA = "residual.eval.approved-factory-comparison.v1"


class ApprovedFactoryBindingError(SpecEvalError):
    """A measured run did not match its preapproved Factory evidence contract."""


def _require_hash(value: str, name: str, *, length: int = 64) -> str:
    if not isinstance(value, str) or len(value) != length or any(ch not in _HEX for ch in value):
        raise ApprovedFactoryBindingError(f"invalid {name}")
    return value


def _require_public_key(value: bytes) -> bytes:
    if not isinstance(value, bytes) or len(value) != 32:
        raise ApprovedFactoryBindingError("32-byte Station public key required")
    return value


@dataclass(frozen=True, slots=True)
class FactoryTopologyTrace:
    """Hash-bound host scheduler evidence for one experiment cell.

    The trace uses actual M4 Ready-DAG snapshots and scheduler measurements.
    `worker_bounds` remains an approval input on the binding; observed worker
    counts must fall inside it.  Fixed/single topology is proved by the observed
    scheduler worker count, not by the number of attempts or receipts.
    """

    configuration: str
    execution_plan_hash: str
    snapshots: tuple[ReadyDagSnapshot, ...]
    measurements: tuple[SchedulerMeasurements, ...]
    actions: tuple[SchedulerAction, ...] = ()

    def __post_init__(self) -> None:
        if self.configuration not in _CONFIGS:
            raise ApprovedFactoryBindingError("invalid topology configuration")
        _require_hash(self.execution_plan_hash, "topology execution plan hash")
        snapshots = tuple(self.snapshots)
        measurements = tuple(self.measurements)
        actions = tuple(self.actions)
        if not snapshots or not measurements:
            raise ApprovedFactoryBindingError("scheduler snapshots and measurements are required")
        if any(not isinstance(value, ReadyDagSnapshot) for value in snapshots):
            raise ApprovedFactoryBindingError("typed ReadyDagSnapshot evidence required")
        if any(not isinstance(value, SchedulerMeasurements) for value in measurements):
            raise ApprovedFactoryBindingError("typed SchedulerMeasurements evidence required")
        if any(not isinstance(value, SchedulerAction) for value in actions):
            raise ApprovedFactoryBindingError("typed SchedulerAction evidence required")
        if any(value.plan_hash != self.execution_plan_hash for value in snapshots):
            raise ApprovedFactoryBindingError("scheduler snapshot belongs to another ExecutionPlan")
        snapshot_hashes = {value.snapshot_hash for value in snapshots}
        if any(value.ready_dag_hash not in snapshot_hashes for value in measurements):
            raise ApprovedFactoryBindingError("scheduler measurement is not bound to supplied Ready DAG evidence")
        measurement_hashes = {value.measurement_hash for value in measurements}
        if any(value.measurement_hash not in measurement_hashes for value in actions):
            raise ApprovedFactoryBindingError("scheduler action is not bound to supplied measurement evidence")
        object.__setattr__(self, "snapshots", snapshots)
        object.__setattr__(self, "measurements", measurements)
        object.__setattr__(self, "actions", actions)

    @property
    def observed_worker_counts(self) -> tuple[int, ...]:
        return tuple(value.total_workers for value in self.measurements)

    def validate_bounds(self, bounds: tuple[int, int]) -> None:
        if (not isinstance(bounds, tuple) or len(bounds) != 2 or
                any(type(value) is not int or value < 1 for value in bounds)):
            raise ApprovedFactoryBindingError("worker bounds must be a positive integer pair")
        low, high = bounds
        if low > high:
            raise ApprovedFactoryBindingError("worker bounds are inverted")
        if self.configuration == "single" and bounds != (1, 1):
            raise ApprovedFactoryBindingError("single configuration requires worker bounds (1, 1)")
        if self.configuration == "fixed" and (low != high or low < 2):
            raise ApprovedFactoryBindingError("fixed configuration requires one approved swarm width >= 2")
        if self.configuration == "dynamic" and low >= high:
            raise ApprovedFactoryBindingError("dynamic configuration requires a non-degenerate worker range")
        if any(not low <= count <= high for count in self.observed_worker_counts):
            raise ApprovedFactoryBindingError("observed scheduler worker count is outside approved bounds")
        if self.configuration in {"single", "fixed"}:
            expected = low
            if any(count != expected for count in self.observed_worker_counts):
                raise ApprovedFactoryBindingError("observed worker count drifted from fixed topology")
            if any(action.resource == "workers" and action.before != action.after for action in self.actions):
                raise ApprovedFactoryBindingError("fixed topology contains a worker-resize action")
        else:
            for action in self.actions:
                if action.resource == "workers" and (
                    not low <= action.before <= high or not low <= action.after <= high
                ):
                    raise ApprovedFactoryBindingError("dynamic worker action exceeds approved bounds")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "factory-eval-topology-trace-v1",
            "configuration": self.configuration,
            "execution_plan_hash": self.execution_plan_hash,
            "snapshots": [value.to_dict() for value in self.snapshots],
            "measurements": [value.to_dict() for value in self.measurements],
            "actions": [value.to_dict() for value in self.actions],
        }

    @property
    def trace_hash(self) -> str:
        return digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class AuthoritativeFactoryRunEvidence:
    """One callback result before evaluation-layer validation."""

    measurement: FactoryRunMeasurement
    final_acceptance: IntegrationReceipt
    topology: FactoryTopologyTrace

    def __post_init__(self) -> None:
        if not isinstance(self.measurement, FactoryRunMeasurement):
            raise ApprovedFactoryBindingError("FactoryRunMeasurement required")
        if not isinstance(self.final_acceptance, IntegrationReceipt):
            raise ApprovedFactoryBindingError("M4 IntegrationReceipt required")
        if not isinstance(self.topology, FactoryTopologyTrace):
            raise ApprovedFactoryBindingError("FactoryTopologyTrace required")


@dataclass(frozen=True, slots=True)
class ApprovedFactoryRunBinding:
    """One preregistered measured experiment cell.

    The zero-argument callback captures already-approved Factory inputs.  The
    evaluation layer never converts benchmark prompt text into WorkerContracts,
    filesystem/tool authority, verification policy, or approval policy.
    """

    workload_manifest_hash: str
    configuration: str
    run_index: int
    approval_ref: str
    execution_plan_hash: str
    approved_attempt_ids: tuple[str, ...]
    worker_bounds: tuple[int, int]
    station_public_key: bytes
    execute: Callable[[], AuthoritativeFactoryRunEvidence]

    def __post_init__(self) -> None:
        _require_hash(self.workload_manifest_hash, "workload manifest hash")
        _require_hash(self.execution_plan_hash, "execution plan hash")
        if self.configuration not in _CONFIGS:
            raise ApprovedFactoryBindingError("configuration must be single, fixed, or dynamic")
        if type(self.run_index) is not int or self.run_index < 0:
            raise ApprovedFactoryBindingError("run_index must be a non-negative integer")
        if not isinstance(self.approval_ref, str) or not self.approval_ref.strip():
            raise ApprovedFactoryBindingError("approval_ref is required")
        attempts = tuple(self.approved_attempt_ids)
        if not attempts or any(not isinstance(value, str) or not value.strip() for value in attempts):
            raise ApprovedFactoryBindingError("approved attempt ids are required")
        if len(attempts) != len(set(attempts)):
            raise ApprovedFactoryBindingError("approved attempt ids must be unique")
        _require_public_key(self.station_public_key)
        if not callable(self.execute):
            raise ApprovedFactoryBindingError("approved Factory execution callback is required")
        # Topology is an explicit scheduler/runtime approval, never inferred from
        # attempt count.  Validate it with a minimal synthetic trace shape here.
        low, high = self.worker_bounds if isinstance(self.worker_bounds, tuple) and len(self.worker_bounds) == 2 else (0, 0)
        if any(type(value) is not int or value < 1 for value in (low, high)) or low > high:
            raise ApprovedFactoryBindingError("worker bounds must be a positive ordered pair")
        if self.configuration == "single" and (low, high) != (1, 1):
            raise ApprovedFactoryBindingError("single configuration requires worker bounds (1, 1)")
        if self.configuration == "fixed" and (low != high or low < 2):
            raise ApprovedFactoryBindingError("fixed configuration requires one approved swarm width >= 2")
        if self.configuration == "dynamic" and low >= high:
            raise ApprovedFactoryBindingError("dynamic configuration requires a non-degenerate worker range")
        object.__setattr__(self, "approved_attempt_ids", attempts)

    @property
    def key(self) -> tuple[str, int]:
        return self.configuration, self.run_index

    def _validate_final_acceptance(self, evidence: AuthoritativeFactoryRunEvidence) -> None:
        receipt = evidence.final_acceptance
        if not receipt.verify_signature(self.station_public_key):
            raise ApprovedFactoryBindingError("M4 final-acceptance receipt signature is invalid")
        if receipt.execution_plan_hash != self.execution_plan_hash:
            raise ApprovedFactoryBindingError("M4 final acceptance belongs to another ExecutionPlan")
        # Current M4 v2 trusted-fixture receipts intentionally say
        # development_fixture.  They may not be relabelled as measured evidence.
        if receipt.evidence_level != "measured":
            raise ApprovedFactoryBindingError("measured evaluation requires M4 evidence_level=measured")
        if not receipt.verification_results:
            raise ApprovedFactoryBindingError("M4 final acceptance has no accumulated verification results")
        for result in receipt.verification_results:
            if (result.status != "pass" or result.termination_reason != "exit" or
                    result.returncode != 0):
                raise ApprovedFactoryBindingError("M4 final verification is not a clean PASS")
            if result.execution_boundary == "trusted_fixture_unsandboxed":
                raise ApprovedFactoryBindingError("unsandboxed trusted-fixture verification is not measured acceptance")

        measurement_hashes = tuple(value.receipt_hash for value in evidence.measurement.receipts)
        if tuple(receipt.input_receipt_hashes) != measurement_hashes:
            raise ApprovedFactoryBindingError("M4 final acceptance does not bind the measured M3 receipt set")

    def execute_and_validate(self) -> tuple[FactoryRunMeasurement, Mapping[str, str]]:
        evidence = self.execute()
        if not isinstance(evidence, AuthoritativeFactoryRunEvidence):
            raise ApprovedFactoryBindingError("approved callback returned invalid authoritative evidence")
        measurement = evidence.measurement
        receipts = measurement.receipts
        receipt_attempts = tuple(receipt.attempt_id for receipt in receipts)
        if len(receipt_attempts) != len(set(receipt_attempts)):
            raise ApprovedFactoryBindingError("measurement contains duplicate receipt attempts")
        if not set(receipt_attempts).issubset(set(self.approved_attempt_ids)):
            raise ApprovedFactoryBindingError("measurement contains an unapproved attempt receipt")
        if any(receipt.execution_plan_hash != self.execution_plan_hash for receipt in receipts):
            raise ApprovedFactoryBindingError("measurement receipt execution plan differs from approval")
        if measurement.accepted_tasks != len(receipts):
            raise ApprovedFactoryBindingError("accepted task count must equal passing M3 receipts")
        if measurement.verifier_outputs < measurement.accepted_tasks:
            raise ApprovedFactoryBindingError("verifier output count cannot be below accepted task count")

        topology = evidence.topology
        if topology.configuration != self.configuration:
            raise ApprovedFactoryBindingError("scheduler topology configuration differs from experiment cell")
        if topology.execution_plan_hash != self.execution_plan_hash:
            raise ApprovedFactoryBindingError("scheduler topology belongs to another ExecutionPlan")
        topology.validate_bounds(self.worker_bounds)
        self._validate_final_acceptance(evidence)

        acceptance = evidence.final_acceptance
        provenance = {
            "approval_ref_hash": digest({"approval_ref": self.approval_ref}),
            "execution_plan_hash": self.execution_plan_hash,
            "integration_plan_hash": acceptance.integration_plan_hash,
            "m4_integration_receipt_hash": acceptance.receipt_hash,
            "scheduler_topology_trace_hash": topology.trace_hash,
        }
        return measurement, provenance


class ApprovedFactoryEvaluationAdapter:
    """Resolve measured Factory runs only from an explicit approval registry."""

    def __init__(self, bindings: Iterable[ApprovedFactoryRunBinding]):
        rows = tuple(bindings)
        if not rows:
            raise ApprovedFactoryBindingError("at least one approved Factory run binding is required")
        if any(not isinstance(row, ApprovedFactoryRunBinding) for row in rows):
            raise ApprovedFactoryBindingError("invalid approved Factory run binding")
        manifests = {row.workload_manifest_hash for row in rows}
        public_keys = {row.station_public_key for row in rows}
        if len(manifests) != 1:
            raise ApprovedFactoryBindingError("one adapter cannot mix FrozenWorkload manifests")
        if len(public_keys) != 1:
            raise ApprovedFactoryBindingError("one adapter cannot mix Station identities")
        by_key: dict[tuple[str, int], ApprovedFactoryRunBinding] = {}
        for row in rows:
            if row.key in by_key:
                raise ApprovedFactoryBindingError("duplicate approved Factory run binding")
            by_key[row.key] = row
        self._manifest_hash = next(iter(manifests))
        self._station_public_key = next(iter(public_keys))
        self._bindings = by_key
        self._provenance: dict[tuple[str, int], Mapping[str, str]] = {}

    @property
    def workload_manifest_hash(self) -> str:
        return self._manifest_hash

    @property
    def station_public_key(self) -> bytes:
        return self._station_public_key

    def assert_complete(self, workload: FrozenWorkload, *, runs: int) -> None:
        if not isinstance(workload, FrozenWorkload) or not workload.verify():
            raise ApprovedFactoryBindingError("verified FrozenWorkload required")
        if workload.manifest_hash != self._manifest_hash:
            raise ApprovedFactoryBindingError("approved Factory bindings target another FrozenWorkload")
        if type(runs) is not int or runs < 1:
            raise ApprovedFactoryBindingError("runs must be a positive integer")
        expected = {(configuration, index) for configuration in _CONFIGS for index in range(runs)}
        missing = sorted(expected.difference(self._bindings))
        extra = sorted(set(self._bindings).difference(expected))
        if missing or extra:
            raise ApprovedFactoryBindingError(
                f"approved Factory experiment matrix mismatch: missing={missing}, extra={extra}"
            )

    def __call__(self, workload: FrozenWorkload, configuration: str,
                 run_index: int) -> FactoryRunMeasurement:
        if not isinstance(workload, FrozenWorkload) or not workload.verify():
            raise ApprovedFactoryBindingError("verified FrozenWorkload required")
        if workload.manifest_hash != self._manifest_hash:
            raise ApprovedFactoryBindingError("approved Factory bindings target another FrozenWorkload")
        binding = self._bindings.get((configuration, run_index))
        if binding is None:
            raise ApprovedFactoryBindingError("no preapproved Factory binding for requested experiment run")
        measurement, provenance = binding.execute_and_validate()
        self._provenance[(configuration, run_index)] = dict(provenance)
        return measurement

    def provenance(self, configuration: str, run_index: int) -> Mapping[str, str]:
        try:
            return dict(self._provenance[(configuration, run_index)])
        except KeyError as exc:
            raise ApprovedFactoryBindingError("run has no validated M4/topology provenance") from exc


@dataclass
class ApprovedMeasuredFactoryEvaluationRunner:
    """Run SPEC-EVAL and sign a provenance envelope around its comparison report."""

    workload: FrozenWorkload
    evidence: SpecEvaluationEvidence
    execute: ApprovedFactoryEvaluationAdapter
    temperatures: tuple[float, ...] = (0.0,)
    seed: int = 20260914
    rates: CostRates = CostRates()
    clock: Callable[[], float] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.execute, ApprovedFactoryEvaluationAdapter):
            raise ApprovedFactoryBindingError("ApprovedFactoryEvaluationAdapter required")
        if self.execute.station_public_key != self.evidence.identity.public_bytes():
            raise ApprovedFactoryBindingError("evaluation Station identity differs from Factory evidence identity")

    def run(self, *, runs: int = 3,
            configurations: Sequence[str] = ("single", "fixed", "dynamic"),
            significance_test: str = "mann_whitney_u", alpha: float = 0.05) -> SignedComparisonReport:
        configs = tuple(configurations)
        self.execute.assert_complete(self.workload, runs=runs)
        kwargs = {
            "workload": self.workload,
            "evidence": self.evidence,
            "execute": self.execute,
            "temperatures": self.temperatures,
            "seed": self.seed,
            "rates": self.rates,
        }
        if self.clock is not None:
            kwargs["clock"] = self.clock
        base = MeasuredFactoryEvaluationRunner(**kwargs).run(
            runs=runs, configurations=configs,
            significance_test=significance_test, alpha=alpha,
        )
        provenance = []
        for configuration in configs:
            for run_index in range(runs):
                provenance.append({
                    "configuration": configuration,
                    "run_index": run_index,
                    "refs": dict(sorted(self.execute.provenance(configuration, run_index).items())),
                })
        payload = {
            "schema_version": ENVELOPE_SCHEMA,
            "workload_manifest_hash": self.workload.manifest_hash,
            "comparison_report": base.to_dict(),
            "run_provenance": provenance,
        }
        report_hash = digest(payload)
        return SignedComparisonReport(
            payload=payload,
            station_key_id=self.evidence.identity.key_id,
            station_signature=self.evidence.identity.sign(report_hash),
        )
