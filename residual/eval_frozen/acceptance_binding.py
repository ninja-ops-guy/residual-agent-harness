"""Bind a measured frozen-workload evaluation run to post-#63 M4 acceptance evidence.

This module is the rebuilt measured-evaluation -> M4-acceptance binding on
current main. It replaces the closed PR #71 design and satisfies four
evidence-integrity requirements against the NEW API (de9c9fa8 "M4
trust-boundary closure (#63)", PR #95 ownership baseline, PR #100 clean-install
qualification, PR #86 frozen R0-R5 harness):

1. Fresh execution identity / anti-replay. Every measured run must be begun
   through :class:`FreshRunRegistry`, which issues a Station-signed,
   hash-chained :class:`RunIdentityRecord`. A run id can be begun exactly
   once; resuming a run appends a signed ``fresh=False`` record and PERMANENTLY
   marks that run's evidence as non-fresh. Resume recovers a run; it never
   converts old evidence into fresh execution. Replay (a second ``begin`` for
   the same run id, a broken chain, or a forged record) fails closed.

2. Authenticated scheduler/topology evidence bound to the complete run
   interval. :class:`SchedulerTopologyEvidence` is a Station-signed envelope
   over typed ``ReadyDagSnapshot`` / ``SchedulerMeasurements`` /
   ``SchedulerAction`` values with observation timestamps. The binding rejects
   unsigned or wrongly-signed traces (no self-reported topology) and requires
   observations covering the FULL run interval ``[run_started_ns,
   run_ended_ns]`` -- a partial-interval trace fails closed.

3. Exact frozen-workload -> Factory-task mapping.
   :class:`WorkloadTaskMapping.for_workload` requires an explicit, complete,
   injective mapping from every evaluation-slice frozen task to a Factory task
   id, and the binding requires the measured receipt task population to equal
   the mapped Factory task population EXACTLY (no missing, extra, or duplicate
   tasks). An unenforced or divergent population fails closed.

4. Independently qualified verifier boundary with UNKNOWN failing closed.
   Final acceptance is only valid when (a) a :class:`VerifierQualification`
   proves the ``linux-userns-isolated-v1`` m4_sandbox boundary probed PASS for
   this run, and (b) the M4 ``IntegrationReceipt`` is Station-signed, carries
   ``evidence_level="isolated_candidate_verification"``, binds the exact
   measured M3 receipt set, and every verification result is a clean
   pass/exit/0 inside the isolated boundary. Any UNKNOWN/ERROR/unavailable
   verification outcome fails closed and is NEVER attributed to a task
   (``attribution`` is always null in the issued artifact).

Prerequisites (fail closed): the binding requires a PASS clean-install
qualification report (PR #100) and a passing Factory ownership gate report
(PR #95) for the same commit before it will issue anything.

Non-claims: this module issues a *binding artifact*, not live empirical
results. It does not close #63 or any other issue, does not by itself
authorize R0-R5 confirmatory claims, and the local Station identity requires
an externally pinned public key before its signatures establish trust.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from ..core import ContractError, digest
from ..factory.evidence_receipts import SIGNATURE_DOMAIN, StationIdentity, WorkerReceipt, _sha256
from ..factory.m4_evidence import ReadyDagSnapshot
from ..factory.m4_integrator import IntegrationReceipt
from ..factory.m4_sandbox import SANDBOX_PROFILE
from ..factory.m4_scheduler import SchedulerAction, SchedulerMeasurements
from .workload import FrozenWorkload

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # pragma: no cover - cryptography is a hard dependency
    InvalidSignature = None
    Ed25519PublicKey = None


RUN_IDENTITY_SCHEMA = "residual.eval-frozen-run-identity.v1"
TOPOLOGY_SCHEMA = "residual.eval-frozen-topology-evidence.v1"
MAPPING_SCHEMA = "residual.eval-frozen-task-mapping.v1"
ACCEPTANCE_SCHEMA = "residual.eval-frozen-final-acceptance.v1"

MEASURED_EVIDENCE_LEVEL = "isolated_candidate_verification"

_HEX = frozenset("0123456789abcdef")

NON_CLAIMS = (
    "This artifact binds evidence; it is not itself a live empirical result.",
    "Does not close issue #63 or any other issue.",
    "Does not authorize R0-R5 confirmatory claims until the full gate sequence "
    "(clean-install qualification, ownership gate, isolated measured execution) "
    "has been run and independently reviewed.",
    "The Station signature establishes integrity under this key only; trust "
    "requires an externally pinned Station public key.",
)


class AcceptanceBindingError(ContractError):
    """Measured-run evidence failed the acceptance binding. Fails closed."""


def _require_hash(value: object, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in _HEX for c in value):
        raise AcceptanceBindingError(f"invalid {name}")
    return value


def _require_ns(value: object, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise AcceptanceBindingError(f"invalid {name}")
    return value


def _verify_payload_signature(payload_hash: str, key_id: str, signature: str,
                              public_key: bytes) -> bool:
    if Ed25519PublicKey is None or len(public_key) != 32:
        return False
    if _sha256(public_key) != key_id:
        return False
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            bytes.fromhex(signature), SIGNATURE_DOMAIN + payload_hash.encode("ascii")
        )
        return True
    except (ValueError, TypeError, InvalidSignature):
        return False


# ---------------------------------------------------------------------------
# Requirement 1: fresh execution identity with anti-replay
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class RunIdentityRecord:
    """One Station-signed entry in the run-identity chain.

    ``fresh=True`` marks the first and only beginning of a run id.
    ``fresh=False`` records a resume: the run may be recovered operationally,
    but its evidence is permanently non-fresh and cannot support acceptance.
    """

    run_id: str
    workload_sha256: str
    report_sha256: str
    execution_plan_hash: str
    prev_record_hash: str
    fresh: bool
    resume_of: str | None
    issued_at_ns: int
    station_key_id: str
    station_signature: str
    schema_version: str = RUN_IDENTITY_SCHEMA

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "workload_sha256": self.workload_sha256,
            "report_sha256": self.report_sha256,
            "execution_plan_hash": self.execution_plan_hash,
            "prev_record_hash": self.prev_record_hash,
            "fresh": self.fresh,
            "resume_of": self.resume_of,
            "issued_at_ns": self.issued_at_ns,
            "station_key_id": self.station_key_id,
        }

    @property
    def record_hash(self) -> str:
        return digest(self.unsigned_payload())

    def to_dict(self) -> dict[str, object]:
        return {**self.unsigned_payload(), "record_hash": self.record_hash,
                "station_signature": self.station_signature}

    def verify_signature(self, public_key: bytes) -> bool:
        return _verify_payload_signature(self.record_hash, self.station_key_id,
                                         self.station_signature, public_key)


class FreshRunRegistry:
    """Station-side issuer of fresh run identities (anti-replay).

    The registry keeps the complete signed chain. ``begin_run`` is the ONLY
    way to obtain a fresh identity and rejects any run id that already
    exists, so a replayed run can never obtain a second fresh record.
    ``resume_run`` appends a signed non-fresh record; :meth:`fresh_record`
    then refuses to vouch for that run forever.
    """

    def __init__(self, identity: StationIdentity) -> None:
        if not isinstance(identity, StationIdentity):
            raise AcceptanceBindingError("StationIdentity required")
        self._identity = identity
        self._records: list[RunIdentityRecord] = []

    @property
    def public_key(self) -> bytes:
        return self._identity.public_bytes()

    @property
    def records(self) -> tuple[RunIdentityRecord, ...]:
        return tuple(self._records)

    def _issue(self, *, run_id: str, workload_sha256: str, report_sha256: str,
               execution_plan_hash: str, fresh: bool, resume_of: str | None,
               issued_at_ns: int | None) -> RunIdentityRecord:
        prev = self._records[-1].record_hash if self._records else "0" * 64
        unsigned = RunIdentityRecord(
            run_id=run_id,
            workload_sha256=_require_hash(workload_sha256, "workload hash"),
            report_sha256=_require_hash(report_sha256, "report hash"),
            execution_plan_hash=_require_hash(execution_plan_hash, "execution plan hash"),
            prev_record_hash=prev,
            fresh=fresh,
            resume_of=resume_of,
            issued_at_ns=issued_at_ns if issued_at_ns is not None else time.time_ns(),
            station_key_id=self._identity.key_id,
            station_signature="pending",
        )
        record = RunIdentityRecord(
            run_id=unsigned.run_id,
            workload_sha256=unsigned.workload_sha256,
            report_sha256=unsigned.report_sha256,
            execution_plan_hash=unsigned.execution_plan_hash,
            prev_record_hash=unsigned.prev_record_hash,
            fresh=unsigned.fresh,
            resume_of=unsigned.resume_of,
            issued_at_ns=unsigned.issued_at_ns,
            station_key_id=unsigned.station_key_id,
            station_signature=self._identity.sign(unsigned.record_hash),
        )
        self._records.append(record)
        return record

    def begin_run(self, run_id: str, *, workload_sha256: str, report_sha256: str,
                  execution_plan_hash: str,
                  issued_at_ns: int | None = None) -> RunIdentityRecord:
        if not isinstance(run_id, str) or not run_id.strip():
            raise AcceptanceBindingError("run id required")
        if any(r.run_id == run_id for r in self._records):
            # Anti-replay: a run id is fresh exactly once. A second begin is a
            # replay attempt and is rejected, never silently deduplicated.
            raise AcceptanceBindingError(
                f"run id already executed: {run_id!r}; replay is not fresh evidence")
        return self._issue(run_id=run_id, workload_sha256=workload_sha256,
                           report_sha256=report_sha256,
                           execution_plan_hash=execution_plan_hash,
                           fresh=True, resume_of=None, issued_at_ns=issued_at_ns)

    def resume_run(self, run_id: str, *,
                   issued_at_ns: int | None = None) -> RunIdentityRecord:
        """Recover a run operationally; the record is explicitly NON-fresh."""
        if not any(r.run_id == run_id and r.fresh for r in self._records):
            raise AcceptanceBindingError(f"cannot resume an unknown run: {run_id!r}")
        return self._issue(run_id=run_id,
                           workload_sha256=self.fresh_record(run_id).workload_sha256,
                           report_sha256=self.fresh_record(run_id).report_sha256,
                           execution_plan_hash=self.fresh_record(run_id).execution_plan_hash,
                           fresh=False, resume_of=run_id, issued_at_ns=issued_at_ns)

    def fresh_record(self, run_id: str) -> RunIdentityRecord:
        """Return the run's identity record ONLY if it is still fresh.

        Fails closed on: unknown run id, broken/forged chain, invalid
        signature, or any resume record (a resumed run's evidence never
        becomes fresh again).
        """
        self.verify_chain()
        fresh = [r for r in self._records if r.run_id == run_id and r.fresh]
        if not fresh:
            raise AcceptanceBindingError(f"no fresh execution identity for run {run_id!r}")
        if any(r.run_id == run_id and not r.fresh for r in self._records):
            raise AcceptanceBindingError(
                f"run {run_id!r} was resumed; its evidence is non-fresh and cannot "
                "support measured acceptance")
        return fresh[0]

    def verify_chain(self) -> None:
        prev = "0" * 64
        for record in self._records:
            if record.prev_record_hash != prev:
                raise AcceptanceBindingError("run-identity chain is broken")
            if not record.verify_signature(self._identity.public_bytes()):
                raise AcceptanceBindingError("run-identity record signature invalid")
            prev = record.record_hash


# ---------------------------------------------------------------------------
# Requirement 2: authenticated scheduler/topology evidence over the full interval
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SchedulerObservation:
    """One host scheduler measurement with the time it was observed."""

    observed_at_ns: int
    measurement: SchedulerMeasurements

    def __post_init__(self) -> None:
        _require_ns(self.observed_at_ns, "observation timestamp")
        if not isinstance(self.measurement, SchedulerMeasurements):
            raise AcceptanceBindingError("typed SchedulerMeasurements required")

    def to_dict(self) -> dict[str, object]:
        return {"observed_at_ns": self.observed_at_ns,
                "measurement": self.measurement.to_dict()}


@dataclass(frozen=True, slots=True)
class SchedulerTopologyEvidence:
    """Station-signed scheduler/topology envelope for exactly one run interval.

    The envelope is only constructible through :meth:`issue`, so topology
    evidence is always authenticated; a self-reported trace has no valid
    Station signature and the binding rejects it. Observations must cover the
    complete run interval: the first observation at or before
    ``run_started_ns`` and the last at or after ``run_ended_ns``.
    """

    execution_plan_hash: str
    run_started_ns: int
    run_ended_ns: int
    snapshots: tuple[ReadyDagSnapshot, ...]
    observations: tuple[SchedulerObservation, ...]
    actions: tuple[SchedulerAction, ...]
    station_key_id: str
    station_signature: str
    schema_version: str = TOPOLOGY_SCHEMA

    def __post_init__(self) -> None:
        _require_hash(self.execution_plan_hash, "topology execution plan hash")
        _require_ns(self.run_started_ns, "run start")
        _require_ns(self.run_ended_ns, "run end")
        if self.run_ended_ns < self.run_started_ns:
            raise AcceptanceBindingError("run interval is inverted")
        snapshots = tuple(self.snapshots)
        observations = tuple(self.observations)
        actions = tuple(self.actions)
        if not snapshots or not observations:
            raise AcceptanceBindingError("scheduler snapshots and observations required")
        if any(not isinstance(s, ReadyDagSnapshot) for s in snapshots):
            raise AcceptanceBindingError("typed ReadyDagSnapshot evidence required")
        if any(not isinstance(o, SchedulerObservation) for o in observations):
            raise AcceptanceBindingError("typed SchedulerObservation evidence required")
        if any(not isinstance(a, SchedulerAction) for a in actions):
            raise AcceptanceBindingError("typed SchedulerAction evidence required")
        if any(s.plan_hash != self.execution_plan_hash for s in snapshots):
            raise AcceptanceBindingError("scheduler snapshot belongs to another ExecutionPlan")
        snapshot_hashes = {s.snapshot_hash for s in snapshots}
        if any(o.measurement.ready_dag_hash not in snapshot_hashes for o in observations):
            raise AcceptanceBindingError(
                "scheduler measurement not bound to supplied Ready-DAG evidence")
        measurement_hashes = {o.measurement.measurement_hash for o in observations}
        if any(a.measurement_hash not in measurement_hashes for a in actions):
            raise AcceptanceBindingError(
                "scheduler action not bound to supplied measurement evidence")
        times = sorted(o.observed_at_ns for o in observations)
        if times[0] > self.run_started_ns or times[-1] < self.run_ended_ns:
            # Partial-interval evidence cannot authenticate the topology of the
            # WHOLE run; fail closed.
            raise AcceptanceBindingError(
                "scheduler evidence does not span the complete run interval")
        object.__setattr__(self, "snapshots", snapshots)
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "actions", actions)

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "execution_plan_hash": self.execution_plan_hash,
            "run_started_ns": self.run_started_ns,
            "run_ended_ns": self.run_ended_ns,
            "snapshots": [s.to_dict() for s in self.snapshots],
            "observations": [o.to_dict() for o in self.observations],
            "actions": [a.to_dict() for a in self.actions],
            "station_key_id": self.station_key_id,
        }

    @property
    def evidence_hash(self) -> str:
        return digest(self.unsigned_payload())

    def to_dict(self) -> dict[str, object]:
        return {**self.unsigned_payload(), "evidence_hash": self.evidence_hash,
                "station_signature": self.station_signature}

    def verify_signature(self, public_key: bytes) -> bool:
        return _verify_payload_signature(self.evidence_hash, self.station_key_id,
                                         self.station_signature, public_key)

    @classmethod
    def issue(cls, identity: StationIdentity, *, execution_plan_hash: str,
              run_started_ns: int, run_ended_ns: int,
              snapshots: Sequence[ReadyDagSnapshot],
              observations: Sequence[SchedulerObservation],
              actions: Sequence[SchedulerAction] = ()) -> "SchedulerTopologyEvidence":
        unsigned = cls(
            execution_plan_hash=execution_plan_hash,
            run_started_ns=run_started_ns,
            run_ended_ns=run_ended_ns,
            snapshots=tuple(snapshots),
            observations=tuple(observations),
            actions=tuple(actions),
            station_key_id=identity.key_id,
            station_signature="pending",
        )
        return cls(
            execution_plan_hash=unsigned.execution_plan_hash,
            run_started_ns=unsigned.run_started_ns,
            run_ended_ns=unsigned.run_ended_ns,
            snapshots=unsigned.snapshots,
            observations=unsigned.observations,
            actions=unsigned.actions,
            station_key_id=unsigned.station_key_id,
            station_signature=identity.sign(unsigned.evidence_hash),
        )


# ---------------------------------------------------------------------------
# Requirement 3: exact frozen-workload -> Factory-task mapping
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class WorkloadTaskMapping:
    """Explicit, complete, injective frozen-task -> Factory-task mapping."""

    entries: tuple[tuple[str, str], ...]
    workload_sha256: str
    schema_version: str = MAPPING_SCHEMA

    def __post_init__(self) -> None:
        _require_hash(self.workload_sha256, "workload hash")
        entries = tuple(self.entries)
        if not entries:
            raise AcceptanceBindingError("task mapping cannot be empty")
        frozen_ids = [a for a, _ in entries]
        factory_ids = [b for _, b in entries]
        if any(not isinstance(a, str) or not a.strip() for a in frozen_ids):
            raise AcceptanceBindingError("invalid frozen task id in mapping")
        if any(not isinstance(b, str) or not b.strip() for b in factory_ids):
            raise AcceptanceBindingError("invalid Factory task id in mapping")
        if len(set(frozen_ids)) != len(frozen_ids) or len(set(factory_ids)) != len(factory_ids):
            raise AcceptanceBindingError("task mapping must be injective in both directions")
        object.__setattr__(self, "entries",
                           tuple(sorted((a.strip(), b.strip()) for a, b in entries)))

    @classmethod
    def for_workload(cls, workload: FrozenWorkload,
                     mapping: Mapping[str, str]) -> "WorkloadTaskMapping":
        """Build a mapping enforced to cover the whole evaluation slice."""
        if not isinstance(workload, FrozenWorkload):
            raise AcceptanceBindingError("FrozenWorkload required")
        required = {t.task_id for t in workload.slice_tasks("evaluation")}
        supplied = {str(k).strip() for k in mapping}
        missing = sorted(required - supplied)
        extra = sorted(supplied - {t.task_id for t in workload.tasks})
        if missing or extra:
            raise AcceptanceBindingError(
                f"task mapping does not cover the frozen workload exactly: "
                f"missing={missing}, unknown={extra}")
        return cls(entries=tuple((str(k), str(v)) for k, v in mapping.items()),
                   workload_sha256=workload.sha256)

    @property
    def factory_task_ids(self) -> frozenset[str]:
        return frozenset(b for _, b in self.entries)

    @property
    def mapping_hash(self) -> str:
        return digest({"schema_version": self.schema_version,
                       "workload_sha256": self.workload_sha256,
                       "entries": [list(e) for e in self.entries]})

    def assert_population(self, receipts: Sequence[WorkerReceipt]) -> None:
        """Enforce the measured Factory task population EXACTLY.

        The set of task ids across receipts must equal the mapped Factory
        task population: no missing task, no extra task, no duplicate task.
        """
        observed = [r.task_id for r in receipts]
        if len(observed) != len(set(observed)):
            raise AcceptanceBindingError("duplicate Factory task in measured population")
        expected = self.factory_task_ids
        missing = sorted(expected - set(observed))
        extra = sorted(set(observed) - expected)
        if missing or extra:
            raise AcceptanceBindingError(
                f"measured task population diverges from the enforced mapping: "
                f"missing={missing}, extra={extra}")


# ---------------------------------------------------------------------------
# Requirement 4: qualified verifier boundary; UNKNOWN fails closed
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class VerifierQualification:
    """Record that the isolated verifier boundary was probed for this run.

    Only a ``pass``/``exit``/rc=0 probe of the ``linux-userns-isolated-v1``
    m4_sandbox boundary can construct this record. UNKNOWN or ERROR probes
    fail closed at construction: an unqualified verifier cannot produce
    acceptance evidence, and no result is ever attributed through it.
    """

    boundary: str
    probe_status: str
    probe_reason: str
    probe_returncode: int
    probe_stdout_sha256: str
    probe_stderr_sha256: str
    probed_at_ns: int

    def __post_init__(self) -> None:
        if self.boundary != SANDBOX_PROFILE:
            raise AcceptanceBindingError(
                f"verifier boundary must be {SANDBOX_PROFILE!r}, got {self.boundary!r}")
        if self.probe_status != "pass" or self.probe_reason != "exit" \
                or type(self.probe_returncode) is not int or self.probe_returncode != 0:
            # UNKNOWN/ERROR/timeout/isolation_unavailable: fail closed here.
            raise AcceptanceBindingError(
                "isolated verifier boundary probe did not PASS "
                f"(status={self.probe_status!r}, reason={self.probe_reason!r}); "
                "UNKNOWN/ERROR verifier outcomes fail closed and are never attributable")
        _require_hash(self.probe_stdout_sha256, "probe stdout hash")
        _require_hash(self.probe_stderr_sha256, "probe stderr hash")
        _require_ns(self.probed_at_ns, "probe timestamp")

    @classmethod
    def from_isolated_result(cls, result, *, probed_at_ns: int) -> "VerifierQualification":
        """Build from an ``IsolatedResult`` probe of the m4_sandbox boundary."""
        if getattr(result, "status", None) != "pass":
            raise AcceptanceBindingError(
                "isolated verifier probe unavailable or failing "
                f"(status={getattr(result, 'status', None)!r}, "
                f"reason={getattr(result, 'reason', None)!r}); failing closed")
        return cls(
            boundary=getattr(result, "execution_boundary", SANDBOX_PROFILE),
            probe_status=result.status,
            probe_reason=result.reason,
            probe_returncode=result.returncode,
            probe_stdout_sha256=result.stdout_sha256,
            probe_stderr_sha256=result.stderr_sha256,
            probed_at_ns=probed_at_ns,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "boundary": self.boundary,
            "probe_status": self.probe_status,
            "probe_reason": self.probe_reason,
            "probe_returncode": self.probe_returncode,
            "probe_stdout_sha256": self.probe_stdout_sha256,
            "probe_stderr_sha256": self.probe_stderr_sha256,
            "probed_at_ns": self.probed_at_ns,
        }


# ---------------------------------------------------------------------------
# Prerequisites: clean-install qualification (#100) + ownership gate (#95)
# ---------------------------------------------------------------------------

def validate_prerequisites(clean_install_report: Mapping[str, object] | None,
                           ownership_report: Mapping[str, object] | None, *,
                           required_commit: str | None = None) -> dict[str, object]:
    """Fail closed unless BOTH prerequisite gates passed for the same commit."""
    if not isinstance(clean_install_report, Mapping):
        raise AcceptanceBindingError("clean-install qualification report absent")
    if clean_install_report.get("status") != "PASS":
        raise AcceptanceBindingError(
            "clean-install qualification (#100) absent or failing; measured binding fails closed")
    if not isinstance(ownership_report, Mapping):
        raise AcceptanceBindingError("Factory ownership gate report absent")
    if ownership_report.get("passed") is not True:
        raise AcceptanceBindingError(
            "Factory ownership gate (#95) absent or failing; measured binding fails closed")
    if required_commit is not None:
        if not isinstance(required_commit, str) or len(required_commit) != 40 \
                or any(c not in _HEX for c in required_commit):
            raise AcceptanceBindingError("invalid required commit")
        if clean_install_report.get("commit") != required_commit:
            raise AcceptanceBindingError("clean-install qualification covers another commit")
        if ownership_report.get("pinned_at") is None:
            raise AcceptanceBindingError("ownership gate report carries no pin")
    return {
        "clean_install_commit": clean_install_report.get("commit"),
        "clean_install_tree": clean_install_report.get("tree"),
        "ownership_pinned_at": ownership_report.get("pinned_at"),
        "ownership_protected_files": ownership_report.get("protected_files"),
    }


# ---------------------------------------------------------------------------
# The binding: measured run evidence in, signed final acceptance out
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class MeasuredRunEvidence:
    """Complete evidence bundle for one measured evaluation run."""

    run_id: str
    workload: FrozenWorkload
    report_sha256: str
    run_started_ns: int
    run_ended_ns: int
    receipts: tuple[WorkerReceipt, ...]
    mapping: WorkloadTaskMapping
    topology: SchedulerTopologyEvidence
    final_acceptance: IntegrationReceipt
    verifier: VerifierQualification
    clean_install_report: Mapping[str, object] = field(default_factory=dict)
    ownership_report: Mapping[str, object] = field(default_factory=dict)


def validate_and_issue_acceptance(evidence: MeasuredRunEvidence,
                                  registry: FreshRunRegistry,
                                  identity: StationIdentity, *,
                                  required_commit: str | None = None,
                                  issued_at_ns: int | None = None) -> dict[str, object]:
    """Validate every requirement and issue the signed final-acceptance artifact.

    Raises :class:`AcceptanceBindingError` (fail closed) on ANY defect. The
    returned artifact is machine-readable JSON signed by the Station identity;
    ``attribution`` is always null because acceptance here is binary and an
    UNKNOWN/unavailable verifier outcome rejects instead of attributing.
    """
    if not isinstance(evidence, MeasuredRunEvidence):
        raise AcceptanceBindingError("MeasuredRunEvidence required")
    if not isinstance(registry, FreshRunRegistry):
        raise AcceptanceBindingError("FreshRunRegistry required")
    if not isinstance(identity, StationIdentity):
        raise AcceptanceBindingError("StationIdentity required")
    if identity.public_bytes() != registry.public_key:
        raise AcceptanceBindingError("acceptance signer differs from run-identity issuer")
    public_key = identity.public_bytes()

    # Prerequisite gates (#100, #95) fail closed.
    prerequisites = validate_prerequisites(
        evidence.clean_install_report, evidence.ownership_report,
        required_commit=required_commit)

    # (a) Exact frozen workload binding.
    if not isinstance(evidence.workload, FrozenWorkload):
        raise AcceptanceBindingError("FrozenWorkload required")
    workload_sha = evidence.workload.sha256
    _require_hash(evidence.report_sha256, "report hash")
    if evidence.mapping.workload_sha256 != workload_sha:
        raise AcceptanceBindingError("task mapping targets another frozen workload")

    # (b) Fresh run identity with anti-replay (requirement 1).
    record = registry.fresh_record(evidence.run_id)
    if record.workload_sha256 != workload_sha:
        raise AcceptanceBindingError("run identity binds another workload")
    if record.report_sha256 != evidence.report_sha256:
        raise AcceptanceBindingError("run identity binds another evaluation report")
    execution_plan_hash = record.execution_plan_hash

    # Measured M3 receipts: signed, unique attempts, same ExecutionPlan.
    receipts = tuple(evidence.receipts)
    if not receipts or any(not isinstance(r, WorkerReceipt) for r in receipts):
        raise AcceptanceBindingError("signed M3 WorkerReceipts required")
    if any(not StationIdentity.verify(r, public_key) for r in receipts):
        raise AcceptanceBindingError("M3 receipt Station signature invalid")
    if any(r.execution_plan_hash != execution_plan_hash for r in receipts):
        raise AcceptanceBindingError("M3 receipt belongs to another ExecutionPlan")
    attempts = [r.attempt_id for r in receipts]
    if len(attempts) != len(set(attempts)):
        raise AcceptanceBindingError("duplicate attempt in measured receipts")

    # (c) Enforced workload -> task mapping (requirement 3).
    evidence.mapping.assert_population(receipts)

    # (d) Authenticated scheduler/topology over the full run interval (req. 2).
    topology = evidence.topology
    if not isinstance(topology, SchedulerTopologyEvidence):
        raise AcceptanceBindingError("authenticated scheduler topology required")
    if not topology.verify_signature(public_key):
        raise AcceptanceBindingError(
            "scheduler/topology evidence is not authenticated by the Station")
    if topology.execution_plan_hash != execution_plan_hash:
        raise AcceptanceBindingError("scheduler topology belongs to another ExecutionPlan")
    if topology.run_started_ns != evidence.run_started_ns \
            or topology.run_ended_ns != evidence.run_ended_ns:
        raise AcceptanceBindingError("scheduler evidence interval does not match the run")

    # (e) Qualified verifier boundary; UNKNOWN fails closed (requirement 4).
    verifier = evidence.verifier
    if not isinstance(verifier, VerifierQualification):
        raise AcceptanceBindingError("qualified verifier boundary record required")

    acceptance = evidence.final_acceptance
    if not isinstance(acceptance, IntegrationReceipt):
        raise AcceptanceBindingError("M4 IntegrationReceipt required")
    if not acceptance.verify_signature(public_key):
        raise AcceptanceBindingError("M4 final-acceptance signature invalid")
    if acceptance.execution_plan_hash != execution_plan_hash:
        raise AcceptanceBindingError("M4 final acceptance belongs to another ExecutionPlan")
    if acceptance.evidence_level != MEASURED_EVIDENCE_LEVEL:
        raise AcceptanceBindingError(
            f"M4 acceptance must carry evidence_level={MEASURED_EVIDENCE_LEVEL!r}; "
            "development_fixture evidence cannot be relabelled as measured")
    if tuple(acceptance.input_receipt_hashes) != tuple(r.receipt_hash for r in receipts):
        raise AcceptanceBindingError(
            "M4 final acceptance does not bind the exact measured M3 receipt set")
    if not acceptance.verification_results:
        raise AcceptanceBindingError("M4 acceptance has no verification results")
    for result in acceptance.verification_results:
        if (result.status != "pass" or result.termination_reason != "exit"
                or result.returncode != 0):
            # UNKNOWN/ERROR/timeout/resource-limited verification fails closed
            # and is NEVER attributed to a task.
            raise AcceptanceBindingError(
                f"verifier outcome {result.status!r}/{result.termination_reason!r} "
                "fails closed; no attribution is possible")
        if result.execution_boundary != SANDBOX_PROFILE:
            raise AcceptanceBindingError(
                "verification executed outside the qualified isolated boundary")

    payload = {
        "schema_version": ACCEPTANCE_SCHEMA,
        "run_id": evidence.run_id,
        "workload_sha256": workload_sha,
        "report_sha256": evidence.report_sha256,
        "execution_plan_hash": execution_plan_hash,
        "run_identity_record_hash": record.record_hash,
        "run_interval_ns": [evidence.run_started_ns, evidence.run_ended_ns],
        "task_mapping_hash": evidence.mapping.mapping_hash,
        "measured_receipt_hashes": [r.receipt_hash for r in receipts],
        "topology_evidence_hash": topology.evidence_hash,
        "verifier_qualification": verifier.to_dict(),
        "m4_final_acceptance_receipt_hash": acceptance.receipt_hash,
        "integration_plan_hash": acceptance.integration_plan_hash,
        "verification_policy_hash": acceptance.verification_policy_hash,
        "prerequisites": prerequisites,
        "attribution": None,
        "issued_at_ns": issued_at_ns if issued_at_ns is not None else time.time_ns(),
        "station_key_id": identity.key_id,
        "non_claims": list(NON_CLAIMS),
    }
    artifact_hash = digest(payload)
    return {
        **payload,
        "artifact_hash": artifact_hash,
        "station_signature": identity.sign(artifact_hash),
    }


def verify_acceptance_artifact(artifact: Mapping[str, object],
                               station_public_key: bytes) -> bool:
    """Independently verify a signed final-acceptance artifact."""
    if not isinstance(artifact, Mapping):
        return False
    payload = {k: v for k, v in artifact.items()
               if k not in ("artifact_hash", "station_signature")}
    if digest(payload) != artifact.get("artifact_hash"):
        return False
    return _verify_payload_signature(
        str(artifact.get("artifact_hash")), str(artifact.get("station_key_id")),
        str(artifact.get("station_signature")), station_public_key)
