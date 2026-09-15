"""Bind a measured frozen-workload evaluation run to post-#63 M4 acceptance evidence.

This module is the rebuilt measured-evaluation -> M4-acceptance binding on
current main. It replaces the closed PR #71 design and addresses four
evidence-integrity requirements against the NEW API (de9c9fa8 "M4
trust-boundary closure (#63)", PR #95 ownership baseline, PR #100 clean-install
qualification, PR #86 frozen R0-R5 harness). Precise, non-overclaimed
semantics:

1. Fresh execution identity / anti-replay. Every measured run must be begun
   through :class:`FreshRunRegistry`, which issues a Station-signed,
   hash-chained :class:`RunIdentityRecord`. A run id can be begun exactly
   once per registry; resuming a run appends a signed ``fresh=False`` record
   and permanently marks that run's evidence as non-fresh: after a resume,
   :meth:`FreshRunRegistry.fresh_record` rejects the run, so resumed evidence
   cannot support acceptance. Replay (a second ``begin`` for the same run id,
   a broken chain, or a forged record) fails closed. The registry enforces
   uniqueness and resume-bars-acceptance *within its own signed chain*; the
   chain must be exported (:meth:`FreshRunRegistry.export_chain`) and retained
   with the evidence for a third party to verify freshness (see
   :func:`verify_acceptance_artifact`). Timestamps inside chain records are
   operator-asserted (see "Operator-asserted fields" below).

2. Authenticated scheduler/topology evidence spanning the run interval.
   :class:`SchedulerTopologyEvidence` is a Station-signed envelope over typed
   ``ReadyDagSnapshot`` / ``SchedulerMeasurements`` / ``SchedulerAction``
   values with observation timestamps. The binding rejects unsigned or
   wrongly-signed traces (no self-reported topology). Coverage rule: the
   earliest observation must be at or before ``run_started_ns``, the latest
   at or after ``run_ended_ns``, AND at least one observation must lie
   strictly inside the open interval ``(run_started_ns, run_ended_ns)``.
   Endpoint-only coverage (zero observations inside the run) fails closed at
   construction; it does not demonstrate that the topology was observed
   *during* the run. This is a coverage floor, not a density guarantee: a
   single interior observation satisfies it.

3. Exact frozen-workload -> Factory-task mapping.
   :class:`WorkloadTaskMapping.for_workload` requires an explicit, complete,
   injective mapping from every evaluation-slice frozen task to a Factory
   task id, and the binding requires the measured receipt task population to
   equal the mapped Factory task population exactly (no missing, extra, or
   duplicate tasks). An unenforced or divergent population fails closed.

4. Station-qualified verifier boundary with UNKNOWN failing closed. The
   :class:`VerifierQualification` is a Station-signed probe receipt, bound to
   the run id, constructible ONLY through the signed issuance path
   (:meth:`VerifierQualification.issue` /
   :meth:`VerifierQualification.from_isolated_result`); direct construction is
   blocked and a fabricated or unsigned qualification fails signature
   verification in the binding. ``probed_at_ns`` must lie inside
   ``[run_started_ns, run_ended_ns]``. NOTE: "qualified" here means the
   issuing Station attests the probe passed -- it is NOT an independent
   third-party qualification. Additionally the M4 ``IntegrationReceipt`` must
   be Station-signed, carry ``evidence_level="isolated_candidate_verification"``,
   bind the exact measured M3 receipt set, and every verification result must
   be a clean pass/exit/0 inside the isolated boundary. Any
   UNKNOWN/ERROR/unavailable verification outcome fails closed and is not
   attributed to a task (``attribution`` is always null in the artifact).

Prerequisites (fail closed): the binding requires a PASS clean-install
qualification report (PR #100) and a passing Factory ownership gate report
(PR #95). Semantics, documented honestly:

- The clean-install report is commit-matched to ``required_commit`` when one
  is supplied.
- The #95 ownership baseline pin LEGITIMATELY PREDATES the evaluated commit,
  so the ownership report is NOT commit-matched. The documented rule is: the
  report must pass, its ``pinned_at`` must equal the pin recorded in the
  on-repo baseline manifest (``verifier/v3/factory_ownership_baseline.json``,
  or an explicitly supplied baseline), and its ``protected_files`` count must
  equal the manifest's file count. A passing gate report asserts that no
  protected-path blob changed relative to that pin in the tree the checker
  ran on. Commit ORDERING (pin <= required_commit) cannot be verified from
  commit SHAs alone and is operator-asserted.
- Both prerequisite reports are UNAUTHENTICATED INPUTS: nothing signs them.
  Their integrity in the final artifact derives solely from the Station
  signature over their SHA-256 digests (``prerequisite_reports_sha256``).

Operator-asserted fields vs registry-enforced fields. The Station signature
proves integrity of the signed bytes, not the accuracy of any clock. All
timestamps are operator-asserted: ``issued_at_ns`` (chain records AND the
final artifact -- caller-supplied time is unavoidable because the Station
has no trusted clock; it proves only "the Station signed a payload claiming
this time", NOT that the run happened then), ``probed_at_ns``, observation
timestamps, and the run interval. Registry-enforced (verifiable from the
signed chain alone): run-id uniqueness, chain linkage, record authenticity,
and resume-bars-acceptance.

Non-claims: this module issues a *binding artifact*, not live empirical
results. It does not close #63 or any other issue, does not by itself
authorize R0-R5 confirmatory claims, and the local Station identity requires
an externally pinned public key before its signatures establish trust.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
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
CHAIN_SCHEMA = "residual.eval-frozen-run-identity-chain.v1"
TOPOLOGY_SCHEMA = "residual.eval-frozen-topology-evidence.v1"
MAPPING_SCHEMA = "residual.eval-frozen-task-mapping.v1"
QUALIFICATION_SCHEMA = "residual.eval-frozen-verifier-qualification.v1"
ACCEPTANCE_SCHEMA = "residual.eval-frozen-final-acceptance.v1"

MEASURED_EVIDENCE_LEVEL = "isolated_candidate_verification"

_HEX = frozenset("0123456789abcdef")

#: On-repo #95 ownership baseline manifest, cross-checked by default.
DEFAULT_OWNERSHIP_BASELINE_PATH = (
    Path(__file__).resolve().parents[2] / "verifier" / "v3" / "factory_ownership_baseline.json"
)

#: Minimum protected-file count: the baseline must protect AT LEAST the
#: 16-path core Factory trust surface. A "weaker" pin covering fewer files
#: than the current baseline manifest is rejected by the count equality rule.
MIN_PROTECTED_FILES = 16

CHAIN_RETENTION_REQUIREMENT = (
    "The exported run-identity chain (residual.eval-frozen-run-identity-chain.v1) "
    "MUST be retained with the evidence bundle. Freshness of the run is "
    "verifiable ONLY by presenting this chain to verify_acceptance_artifact; "
    "without it, freshness is unverified."
)

OPERATOR_ASSERTED_FIELDS = (
    "issued_at_ns (artifact and chain records): caller-supplied; the signature "
    "proves the Station signed a payload claiming this time, not that the time "
    "is accurate (the Station has no trusted clock)",
    "run_interval_ns, observation timestamps, probed_at_ns: asserted by the "
    "runner/Station; only ordering checks enforced by the binding are verifiable",
    "prerequisite report contents: unauthenticated inputs; integrity derives "
    "from the Station signature over their digests",
)

REGISTRY_ENFORCED_FIELDS = (
    "run-id uniqueness within the signed chain",
    "hash-chain linkage and per-record Station signatures",
    "resume-bars-acceptance (a resumed run is permanently non-fresh)",
)

NON_CLAIMS = (
    "This artifact binds evidence; it is not itself a live empirical result.",
    "Does not close issue #63 or any other issue.",
    "Does not authorize R0-R5 confirmatory claims until the full gate sequence "
    "(clean-install qualification, ownership gate, isolated measured execution) "
    "has been run and independently reviewed.",
    "The Station signature establishes integrity under this key only; trust "
    "requires an externally pinned Station public key.",
    "All timestamps in this artifact are operator-asserted; the signature does "
    "not prove their accuracy. See operator_asserted_fields.",
    "Freshness of the run is verifiable only against the retained run-identity "
    "chain referenced by run_identity_chain; without the chain it is unverified.",
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
    ``issued_at_ns`` is operator-asserted (caller-supplied or local clock).
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

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "RunIdentityRecord":
        record = cls(
            run_id=str(value["run_id"]),
            workload_sha256=str(value["workload_sha256"]),
            report_sha256=str(value["report_sha256"]),
            execution_plan_hash=str(value["execution_plan_hash"]),
            prev_record_hash=str(value["prev_record_hash"]),
            fresh=bool(value["fresh"]),
            resume_of=value.get("resume_of"),
            issued_at_ns=int(value["issued_at_ns"]),
            station_key_id=str(value["station_key_id"]),
            station_signature=str(value["station_signature"]),
            schema_version=str(value.get("schema_version", RUN_IDENTITY_SCHEMA)),
        )
        if record.record_hash != value.get("record_hash"):
            raise AcceptanceBindingError("run-identity record hash mismatch")
        return record

    def verify_signature(self, public_key: bytes) -> bool:
        return _verify_payload_signature(self.record_hash, self.station_key_id,
                                         self.station_signature, public_key)


class FreshRunRegistry:
    """Station-side issuer of fresh run identities (anti-replay).

    The registry keeps the complete signed chain. ``begin_run`` is the ONLY
    way to obtain a fresh identity and rejects any run id that already
    exists, so a replayed run cannot obtain a second fresh record.
    ``resume_run`` appends a signed non-fresh record; :meth:`fresh_record`
    then refuses to vouch for that run. :meth:`export_chain` serializes the
    signed chain so third parties can verify freshness out of process.
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
            # Operator-asserted time: the Station has no trusted clock. The
            # signature binds the CLAIMED time, not its accuracy.
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
        signature, or any resume record (a resumed run's evidence does not
        become fresh again).
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

    def export_chain(self) -> dict[str, object]:
        """Serialize the signed run-identity chain for retention/sharing.

        The export is itself Station-signed over the ordered record list, so
        a third party holding ONLY this export plus the Station public key can
        verify chain integrity and run freshness out of process (see
        :func:`verify_run_identity_chain`). Retain it with the evidence
        bundle: the final-acceptance artifact references its head hash.
        """
        self.verify_chain()
        payload: dict[str, object] = {
            "schema_version": CHAIN_SCHEMA,
            "station_key_id": self._identity.key_id,
            "records": [r.to_dict() for r in self._records],
        }
        chain_hash = digest(payload)
        return {**payload, "chain_hash": chain_hash,
                "station_signature": self._identity.sign(chain_hash)}


def verify_run_identity_chain(chain: Mapping[str, object],
                              station_public_key: bytes) -> tuple[RunIdentityRecord, ...]:
    """Verify an exported run-identity chain; fail closed on any defect.

    Returns the verified records. Raises :class:`AcceptanceBindingError` on a
    broken chain, forged/tampered record, bad export signature, or a chain
    whose records were reordered, dropped, or extended.
    """
    if not isinstance(chain, Mapping):
        raise AcceptanceBindingError("run-identity chain absent or malformed")
    if chain.get("schema_version") != CHAIN_SCHEMA:
        raise AcceptanceBindingError("run-identity chain schema mismatch")
    raw_records = chain.get("records")
    if not isinstance(raw_records, Sequence) or isinstance(raw_records, (str, bytes)):
        raise AcceptanceBindingError("run-identity chain records malformed")
    records = tuple(RunIdentityRecord.from_dict(r) for r in raw_records)
    payload = {"schema_version": CHAIN_SCHEMA,
               "station_key_id": chain.get("station_key_id"),
               "records": [r.to_dict() for r in records]}
    if digest(payload) != chain.get("chain_hash"):
        raise AcceptanceBindingError("run-identity chain export was tampered with")
    if not _verify_payload_signature(str(chain.get("chain_hash")),
                                     str(chain.get("station_key_id")),
                                     str(chain.get("station_signature")),
                                     station_public_key):
        raise AcceptanceBindingError("run-identity chain export signature invalid")
    prev = "0" * 64
    seen: set[str] = set()
    for record in records:
        if record.prev_record_hash != prev:
            raise AcceptanceBindingError("run-identity chain is broken")
        if not record.verify_signature(station_public_key):
            raise AcceptanceBindingError("run-identity record signature invalid")
        if record.fresh:
            if record.run_id in seen:
                raise AcceptanceBindingError("run-identity chain contains a replayed run id")
            seen.add(record.run_id)
        prev = record.record_hash
    return records


def chain_fresh_record(records: Sequence[RunIdentityRecord],
                       run_id: str) -> RunIdentityRecord:
    """Fresh-record rule over an already-verified chain (fail closed)."""
    fresh = [r for r in records if r.run_id == run_id and r.fresh]
    if not fresh:
        raise AcceptanceBindingError(f"no fresh execution identity for run {run_id!r}")
    if any(r.run_id == run_id and not r.fresh for r in records):
        raise AcceptanceBindingError(
            f"run {run_id!r} was resumed; its evidence is non-fresh and cannot "
            "support measured acceptance")
    return fresh[0]


# ---------------------------------------------------------------------------
# Requirement 2: authenticated scheduler/topology evidence spanning the run
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SchedulerObservation:
    """One host scheduler measurement with the time it was observed.

    ``observed_at_ns`` is operator-asserted; the binding enforces coverage
    ordering only, not clock accuracy.
    """

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
    Station signature and the binding rejects it. Coverage rule (fail closed
    at construction): the earliest observation must be at or before
    ``run_started_ns``, the latest at or after ``run_ended_ns``, AND at least
    one observation must lie STRICTLY INSIDE ``(run_started_ns, run_ended_ns)``.
    Endpoint-only coverage -- observations only at the boundary, none during
    the run -- is rejected: it does not show the topology was observed while
    the run executed. This is a minimal coverage floor, not a density proof.
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
            # whole run; fail closed.
            raise AcceptanceBindingError(
                "scheduler evidence does not span the run interval")
        if not any(self.run_started_ns < t < self.run_ended_ns for t in times):
            # Endpoint-only coverage: every observation sits on the boundary
            # (or outside) and NOTHING was observed while the run executed.
            # That cannot evidence in-run topology; fail closed.
            raise AcceptanceBindingError(
                "scheduler evidence has no observation strictly inside the run "
                "interval; endpoint-only coverage does not demonstrate in-run "
                "topology observation")
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
        """Enforce the measured Factory task population exactly.

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
# Requirement 4: Station-signed verifier probe receipt; UNKNOWN fails closed
# ---------------------------------------------------------------------------

#: Private construction token: only the signed issuance paths below hold it.
#: Direct construction of VerifierQualification is blocked; even bypassing
#: the token yields a record whose signature cannot verify in the binding.
_ISSUANCE_TOKEN = object()


@dataclass(frozen=True, slots=True)
class VerifierQualification:
    """Station-signed probe receipt binding verifier qualification to a run.

    Constructible ONLY via :meth:`issue` or :meth:`from_isolated_result`
    (both require a :class:`StationIdentity` and sign the receipt); direct
    construction raises. The binding verifies the Station signature, the run
    id binding, and that ``probed_at_ns`` lies inside the run interval.

    Only a ``pass``/``exit``/rc=0 probe of the ``linux-userns-isolated-v1``
    m4_sandbox boundary can be issued. UNKNOWN or ERROR probes fail closed at
    issuance: an unqualified verifier cannot produce acceptance evidence, and
    no result is attributed through it. "Qualified" means the issuing Station
    attests the probe passed -- not an independent third-party qualification.
    ``probed_at_ns`` is operator-asserted; only its containment in the run
    interval is checked.
    """

    boundary: str
    probe_status: str
    probe_reason: str
    probe_returncode: int
    probe_stdout_sha256: str
    probe_stderr_sha256: str
    probed_at_ns: int
    run_id: str
    station_key_id: str
    station_signature: str
    schema_version: str = QUALIFICATION_SCHEMA
    _token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _ISSUANCE_TOKEN:
            raise AcceptanceBindingError(
                "VerifierQualification is constructible only via the signed "
                "issuance path (VerifierQualification.issue / from_isolated_result)")
        if self.boundary != SANDBOX_PROFILE:
            raise AcceptanceBindingError(
                f"verifier boundary must be {SANDBOX_PROFILE!r}, got {self.boundary!r}")
        if self.probe_status != "pass" or self.probe_reason != "exit" \
                or type(self.probe_returncode) is not int or self.probe_returncode != 0:
            # UNKNOWN/ERROR/timeout/isolation_unavailable: fail closed here.
            raise AcceptanceBindingError(
                "isolated verifier boundary probe did not PASS "
                f"(status={self.probe_status!r}, reason={self.probe_reason!r}); "
                "UNKNOWN/ERROR verifier outcomes fail closed and are not attributable")
        _require_hash(self.probe_stdout_sha256, "probe stdout hash")
        _require_hash(self.probe_stderr_sha256, "probe stderr hash")
        _require_ns(self.probed_at_ns, "probe timestamp")
        if not isinstance(self.run_id, str) or not self.run_id.strip():
            raise AcceptanceBindingError("probe receipt must bind a run id")

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "boundary": self.boundary,
            "probe_status": self.probe_status,
            "probe_reason": self.probe_reason,
            "probe_returncode": self.probe_returncode,
            "probe_stdout_sha256": self.probe_stdout_sha256,
            "probe_stderr_sha256": self.probe_stderr_sha256,
            "probed_at_ns": self.probed_at_ns,
            "run_id": self.run_id,
            "station_key_id": self.station_key_id,
        }

    @property
    def qualification_hash(self) -> str:
        return digest(self.unsigned_payload())

    def verify_signature(self, public_key: bytes) -> bool:
        return _verify_payload_signature(self.qualification_hash, self.station_key_id,
                                         self.station_signature, public_key)

    @classmethod
    def issue(cls, identity: StationIdentity, *, run_id: str,
              boundary: str = SANDBOX_PROFILE, probe_status: str,
              probe_reason: str, probe_returncode: int,
              probe_stdout_sha256: str, probe_stderr_sha256: str,
              probed_at_ns: int) -> "VerifierQualification":
        """Signed issuance path: the Station attests this probe for this run."""
        if not isinstance(identity, StationIdentity):
            raise AcceptanceBindingError("StationIdentity required")
        unsigned = cls(
            boundary=boundary, probe_status=probe_status, probe_reason=probe_reason,
            probe_returncode=probe_returncode,
            probe_stdout_sha256=probe_stdout_sha256,
            probe_stderr_sha256=probe_stderr_sha256,
            probed_at_ns=probed_at_ns, run_id=run_id,
            station_key_id=identity.key_id, station_signature="pending",
            _token=_ISSUANCE_TOKEN,
        )
        return cls(
            boundary=unsigned.boundary, probe_status=unsigned.probe_status,
            probe_reason=unsigned.probe_reason,
            probe_returncode=unsigned.probe_returncode,
            probe_stdout_sha256=unsigned.probe_stdout_sha256,
            probe_stderr_sha256=unsigned.probe_stderr_sha256,
            probed_at_ns=unsigned.probed_at_ns, run_id=unsigned.run_id,
            station_key_id=unsigned.station_key_id,
            station_signature=identity.sign(unsigned.qualification_hash),
            _token=_ISSUANCE_TOKEN,
        )

    @classmethod
    def from_isolated_result(cls, identity: StationIdentity, result, *, run_id: str,
                             probed_at_ns: int) -> "VerifierQualification":
        """Issue from an ``IsolatedResult`` probe of the m4_sandbox boundary.

        The result object must carry the isolated-runner fields (status,
        reason, returncode, stdout/stderr hashes, execution_boundary); their
        values are attested by the Station signature on the issued receipt.
        """
        if getattr(result, "status", None) != "pass":
            raise AcceptanceBindingError(
                "isolated verifier probe unavailable or failing "
                f"(status={getattr(result, 'status', None)!r}, "
                f"reason={getattr(result, 'reason', None)!r}); failing closed")
        return cls.issue(
            identity, run_id=run_id,
            boundary=getattr(result, "execution_boundary", SANDBOX_PROFILE),
            probe_status=result.status, probe_reason=result.reason,
            probe_returncode=result.returncode,
            probe_stdout_sha256=result.stdout_sha256,
            probe_stderr_sha256=result.stderr_sha256,
            probed_at_ns=probed_at_ns,
        )

    def to_dict(self) -> dict[str, object]:
        return {**self.unsigned_payload(),
                "qualification_hash": self.qualification_hash,
                "station_signature": self.station_signature}


# ---------------------------------------------------------------------------
# Prerequisites: clean-install qualification (#100) + ownership gate (#95)
# ---------------------------------------------------------------------------

def _load_ownership_baseline(baseline: Mapping[str, object] | None) -> Mapping[str, object]:
    """Load the #95 baseline manifest (default: the on-repo pinned manifest)."""
    if baseline is not None:
        if not isinstance(baseline, Mapping):
            raise AcceptanceBindingError("ownership baseline must be a mapping")
        return baseline
    if not DEFAULT_OWNERSHIP_BASELINE_PATH.is_file():
        raise AcceptanceBindingError(
            f"ownership baseline manifest unavailable: {DEFAULT_OWNERSHIP_BASELINE_PATH}")
    try:
        data = json.loads(DEFAULT_OWNERSHIP_BASELINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcceptanceBindingError(f"ownership baseline manifest unreadable: {exc}")
    if not isinstance(data, Mapping):
        raise AcceptanceBindingError("ownership baseline manifest must be a JSON object")
    return data


def validate_prerequisites(clean_install_report: Mapping[str, object] | None,
                           ownership_report: Mapping[str, object] | None, *,
                           required_commit: str | None = None,
                           ownership_baseline: Mapping[str, object] | None = None
                           ) -> dict[str, object]:
    """Fail closed unless BOTH prerequisite gates passed.

    Documented semantics (see module docstring):

    - The clean-install report is commit-matched to ``required_commit`` when
      one is supplied.
    - The ownership report is NOT commit-matched: the #95 baseline pin
      legitimately predates the evaluated commit. The enforced rule is:
      ``passed`` is true, ``pinned_at`` is a valid commit SHA EQUAL to the
      baseline manifest's pin, and ``protected_files`` equals the manifest's
      file count (a mismatched or weaker pin fails closed). Commit ordering
      (pin <= required_commit) cannot be derived from SHAs and remains
      operator-asserted.
    - Both reports are unauthenticated inputs; their integrity in the final
      artifact derives solely from the Station signature over their digests.
    """
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

    baseline = _load_ownership_baseline(ownership_baseline)
    baseline_pin = baseline.get("pinned_at")
    baseline_files = baseline.get("files")
    if not isinstance(baseline_pin, str) or len(baseline_pin) != 40 \
            or any(c not in _HEX for c in baseline_pin):
        raise AcceptanceBindingError("ownership baseline carries no valid pin")
    if not isinstance(baseline_files, Mapping) or not baseline_files:
        raise AcceptanceBindingError("ownership baseline carries no protected-file set")

    # Ownership rule: the report's pin must BE the current baseline pin, and
    # the reported protection breadth must equal the baseline's (a weaker pin
    # covering fewer protected paths fails closed).
    report_pin = ownership_report.get("pinned_at")
    if not isinstance(report_pin, str) or len(report_pin) != 40 \
            or any(c not in _HEX for c in report_pin):
        raise AcceptanceBindingError("ownership gate report carries no valid pin")
    if report_pin != baseline_pin:
        raise AcceptanceBindingError(
            "ownership gate report pin does not match the current #95 baseline pin; "
            "the baseline legitimately predates the evaluated commit, but the pin "
            "itself must be the pinned baseline's")
    protected = ownership_report.get("protected_files")
    if type(protected) is not int or protected < MIN_PROTECTED_FILES \
            or protected != len(baseline_files):
        raise AcceptanceBindingError(
            "ownership gate report protects fewer paths than the #95 baseline; "
            "a weaker ownership pin fails closed")

    if required_commit is not None:
        if not isinstance(required_commit, str) or len(required_commit) != 40 \
                or any(c not in _HEX for c in required_commit):
            raise AcceptanceBindingError("invalid required commit")
        if clean_install_report.get("commit") != required_commit:
            raise AcceptanceBindingError("clean-install qualification covers another commit")
        # NOTE: ownership pinned_at is intentionally NOT compared to
        # required_commit. The #95 pin predates the evaluated commit by
        # design; ordering is operator-asserted (documented in the docstring).
    return {
        "clean_install_commit": clean_install_report.get("commit"),
        "clean_install_tree": clean_install_report.get("tree"),
        "ownership_pinned_at": report_pin,
        "ownership_protected_files": protected,
        "ownership_rule": (
            "pin equals the #95 baseline pin and protected-file count equals the "
            "baseline; the pin legitimately predates the evaluated commit; commit "
            "ordering is operator-asserted; the passing report asserts no "
            "protected-path blob changed relative to the pin in the checked tree"),
        "prerequisite_authentication": (
            "prerequisite reports are unauthenticated inputs; their integrity "
            "derives from the Station signature over prerequisite_reports_sha256"),
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
                                  issued_at_ns: int | None = None,
                                  ownership_baseline: Mapping[str, object] | None = None
                                  ) -> dict[str, object]:
    """Validate every requirement and issue the signed final-acceptance artifact.

    Raises :class:`AcceptanceBindingError` (fail closed) on ANY defect. The
    returned artifact is machine-readable JSON signed by the Station identity;
    ``attribution`` is always null because acceptance here is binary and an
    UNKNOWN/unavailable verifier outcome rejects instead of attributing.
    ``issued_at_ns`` is caller-supplied (operator-asserted): the signature
    binds the claimed time, it does not prove the time is accurate.
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
        required_commit=required_commit, ownership_baseline=ownership_baseline)

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

    # (d) Authenticated scheduler/topology spanning the run (requirement 2).
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

    # (e) Station-qualified verifier boundary; UNKNOWN fails closed (req. 4).
    verifier = evidence.verifier
    if not isinstance(verifier, VerifierQualification):
        raise AcceptanceBindingError("Station-signed verifier probe receipt required")
    if not verifier.verify_signature(public_key):
        raise AcceptanceBindingError(
            "verifier probe receipt is not authenticated by the Station; "
            "fabricated or unsigned qualifications fail closed")
    if verifier.run_id != evidence.run_id:
        raise AcceptanceBindingError(
            "verifier probe receipt is bound to another run id")
    if not (evidence.run_started_ns <= verifier.probed_at_ns <= evidence.run_ended_ns):
        raise AcceptanceBindingError(
            "verifier probe timestamp lies outside the run interval; the probe "
            "must occur within the run it qualifies")

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
            # and is never attributed to a task.
            raise AcceptanceBindingError(
                f"verifier outcome {result.status!r}/{result.termination_reason!r} "
                "fails closed; no attribution is possible")
        if result.execution_boundary != SANDBOX_PROFILE:
            raise AcceptanceBindingError(
                "verification executed outside the qualified isolated boundary")

    chain_records = registry.records
    chain_ref = {
        "schema_version": CHAIN_SCHEMA,
        "head_record_hash": chain_records[-1].record_hash,
        "record_count": len(chain_records),
        "retention_requirement": CHAIN_RETENTION_REQUIREMENT,
    }
    payload = {
        "schema_version": ACCEPTANCE_SCHEMA,
        "run_id": evidence.run_id,
        "workload_sha256": workload_sha,
        "report_sha256": evidence.report_sha256,
        "execution_plan_hash": execution_plan_hash,
        "run_identity_record_hash": record.record_hash,
        "run_identity_chain": chain_ref,
        "run_interval_ns": [evidence.run_started_ns, evidence.run_ended_ns],
        "task_mapping_hash": evidence.mapping.mapping_hash,
        "measured_receipt_hashes": [r.receipt_hash for r in receipts],
        "topology_evidence_hash": topology.evidence_hash,
        "verifier_qualification": verifier.to_dict(),
        "m4_final_acceptance_receipt_hash": acceptance.receipt_hash,
        "integration_plan_hash": acceptance.integration_plan_hash,
        "verification_policy_hash": acceptance.verification_policy_hash,
        "prerequisites": prerequisites,
        "prerequisite_reports_sha256": {
            "clean_install": digest(dict(evidence.clean_install_report)),
            "ownership": digest(dict(evidence.ownership_report)),
        },
        "operator_asserted_fields": list(OPERATOR_ASSERTED_FIELDS),
        "registry_enforced_fields": list(REGISTRY_ENFORCED_FIELDS),
        "attribution": None,
        # Operator-asserted time; the signature binds the claim, not the clock.
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
                               station_public_key: bytes,
                               chain: Mapping[str, object] | None = None) -> bool:
    """Independently verify a signed final-acceptance artifact.

    ALWAYS verified: payload hash and Station signature.

    FRESHNESS is verified ONLY when ``chain`` (the exported
    ``residual.eval-frozen-run-identity-chain.v1`` referenced by the
    artifact's ``run_identity_chain`` field) is supplied. With a chain, this
    function additionally verifies: the chain export signature, per-record
    signatures and linkage, no replayed run id, that the artifact's
    ``run_identity_record_hash`` is a FRESH record for ``run_id`` in the
    chain (resume bars acceptance), and that the chain head matches the
    artifact's chain reference. WITHOUT a chain the function returns True on
    signature validity alone and freshness is UNVERIFIED -- callers requiring
    freshness MUST pass the retained chain (see the artifact's
    ``run_identity_chain.retention_requirement``).

    Timestamps remain operator-asserted in all modes; verification proves
    integrity under the Station key, never clock accuracy.
    """
    if not isinstance(artifact, Mapping):
        return False
    payload = {k: v for k, v in artifact.items()
               if k not in ("artifact_hash", "station_signature")}
    if digest(payload) != artifact.get("artifact_hash"):
        return False
    if not _verify_payload_signature(
            str(artifact.get("artifact_hash")), str(artifact.get("station_key_id")),
            str(artifact.get("station_signature")), station_public_key):
        return False
    if chain is None:
        # Freshness not verifiable without the retained chain (documented).
        return True
    try:
        records = verify_run_identity_chain(chain, station_public_key)
        record = chain_fresh_record(records, str(artifact.get("run_id")))
    except AcceptanceBindingError:
        return False
    if record.record_hash != artifact.get("run_identity_record_hash"):
        return False
    chain_ref = artifact.get("run_identity_chain")
    if not isinstance(chain_ref, Mapping):
        return False
    if chain_ref.get("schema_version") != CHAIN_SCHEMA:
        return False
    if not records or chain_ref.get("head_record_hash") != records[-1].record_hash:
        return False
    if chain_ref.get("record_count") != len(records):
        return False
    return True
