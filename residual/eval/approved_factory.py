"""Explicit authorization bindings for measured Factory evaluation runs.

A FrozenWorkload describes experimental work; it is not authorization to derive
WorkerContracts, tool scope, filesystem scope, acceptance criteria, or approvals.
This module closes that boundary by requiring every measured run to be registered
against an immutable, preapproved Factory binding before execution begins.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .measured_factory import FactoryRunMeasurement
from .spec_eval import SpecEvalError
from .workload import FrozenWorkload


_HEX = frozenset("0123456789abcdef")
_CONFIGS = frozenset({"single", "fixed", "dynamic"})


class ApprovedFactoryBindingError(SpecEvalError):
    """A measured run did not match its preapproved Factory binding."""


def _require_hash(value: str, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in _HEX for ch in value):
        raise ApprovedFactoryBindingError(f"invalid {name}")
    return value


@dataclass(frozen=True, slots=True)
class ApprovedFactoryRunBinding:
    """One preapproved measured experiment cell.

    ``execute`` is intentionally zero-argument. Authorization inputs are captured by
    the caller when this binding is created; the evaluation layer never passes the
    FrozenWorkload prompt into the execution callback and therefore cannot synthesize
    permissions or acceptance policy from benchmark text at runtime.
    """

    workload_manifest_hash: str
    configuration: str
    run_index: int
    approval_ref: str
    execution_plan_hash: str
    approved_attempt_ids: tuple[str, ...]
    execute: Callable[[], FactoryRunMeasurement]

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
        if self.configuration == "single" and len(attempts) != 1:
            raise ApprovedFactoryBindingError("single configuration requires exactly one approved attempt")
        if self.configuration in {"fixed", "dynamic"} and len(attempts) < 2:
            raise ApprovedFactoryBindingError("swarm configurations require at least two approved attempts")
        if not callable(self.execute):
            raise ApprovedFactoryBindingError("approved Factory execution callback is required")
        object.__setattr__(self, "approved_attempt_ids", attempts)

    @property
    def key(self) -> tuple[str, int]:
        return (self.configuration, self.run_index)

    def execute_and_validate(self) -> FactoryRunMeasurement:
        measurement = self.execute()
        if not isinstance(measurement, FactoryRunMeasurement):
            raise ApprovedFactoryBindingError("approved Factory callback returned invalid measurement")
        if measurement.total_tasks != len(self.approved_attempt_ids):
            raise ApprovedFactoryBindingError("measurement task count differs from approved attempts")

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
        return measurement


class ApprovedFactoryEvaluationAdapter:
    """Resolve measured Factory runs only from an explicit approval registry."""

    def __init__(self, bindings: Iterable[ApprovedFactoryRunBinding]):
        rows = tuple(bindings)
        if not rows:
            raise ApprovedFactoryBindingError("at least one approved Factory run binding is required")
        manifests = {row.workload_manifest_hash for row in rows}
        if len(manifests) != 1:
            raise ApprovedFactoryBindingError("one adapter cannot mix FrozenWorkload manifests")
        by_key: dict[tuple[str, int], ApprovedFactoryRunBinding] = {}
        for row in rows:
            if not isinstance(row, ApprovedFactoryRunBinding):
                raise ApprovedFactoryBindingError("invalid approved Factory run binding")
            if row.key in by_key:
                raise ApprovedFactoryBindingError("duplicate approved Factory run binding")
            by_key[row.key] = row
        self._manifest_hash = next(iter(manifests))
        self._bindings = by_key

    @property
    def workload_manifest_hash(self) -> str:
        return self._manifest_hash

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

    def __call__(
        self,
        workload: FrozenWorkload,
        configuration: str,
        run_index: int,
    ) -> FactoryRunMeasurement:
        if not isinstance(workload, FrozenWorkload) or not workload.verify():
            raise ApprovedFactoryBindingError("verified FrozenWorkload required")
        if workload.manifest_hash != self._manifest_hash:
            raise ApprovedFactoryBindingError("approved Factory bindings target another FrozenWorkload")
        binding = self._bindings.get((configuration, run_index))
        if binding is None:
            raise ApprovedFactoryBindingError("no preapproved Factory binding for requested experiment run")
        return binding.execute_and_validate()
