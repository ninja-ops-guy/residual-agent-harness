"""M4 offline integration: quarantined evidence plus consent yields one receipt.

Integration copies receipt-bound artifact bytes from the candidate worktree into
a private integration worktree using descriptor-relative, no-follow writes. The
recorded project baseline version and an explicit operator integration consent
record are checked in one process before any write. Verification commands are
short host-owned allowlisted commands (audit/build tooling, not project code) or
bounded trusted fixtures; no project test runner executes on the host.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import hmac
import json
import math
from pathlib import Path
import tempfile
import time
from typing import Callable

from residual.core import canonical, strict_json
from .m4_safety import FixtureProcessResult, M4SafetyError, apply_artifact, run_trusted_fixture, snapshot
from .m4_sandbox import sandbox_verification_supported
from .worker_contract import WorkerContractError


class M4IntegrationError(WorkerContractError):
    pass


INTEGRATION_SCHEMA = "factory-integration-receipt-v2"
ObservationSink = Callable[[dict[str, object]], None]

# Host-owned command allowlist. Entries are exact argv prefixes; project-defined
# arguments, wrappers, shells, and environment tricks are rejected elsewhere.
ALLOWED_VERIFICATION_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("python3", "--version"),
    ("python3", "-c"),
    ("git", "diff"),
    ("git", "status"),
)
MAX_OUTPUT = 65536
VERIFICATION_CATEGORIES = {
    "artifact_hash_replay",
    "patch_idempotency_check",
    "static_policy_scan",
    "type_check",
    "full_test_suite",
}
_RESULT_STATUSES = {"pass", "fail", "unknown", "error", "timeout"}


@dataclass(frozen=True)
class IntegrationPlan:
    worker_id: str
    candidate_id: str
    verification_profile: str
    verification_commands: tuple[str, ...]
    expected_base_tree_hash: str
    approval_hash: str

    def __post_init__(self) -> None:
        if not self.worker_id or not self.candidate_id:
            raise M4IntegrationError("integration plan requires worker and candidate identities")
        if not all(isinstance(command, str) and command for command in self.verification_commands):
            raise M4IntegrationError("verification commands must be host-owned strings")
        if len(self.expected_base_tree_hash) != 64:
            raise M4IntegrationError("expected base tree hash must be hex SHA-256")
        if len(self.approval_hash) != 64:
            raise M4IntegrationError("approval binding must be a SHA-256 hash")
        object.__setattr__(self, "verification_commands", tuple(self.verification_commands))

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "IntegrationPlan":
        return cls(**strict_json(canonical(value)))

    @property
    def plan_hash(self) -> str:
        return hashlib.sha256(canonical(self.to_dict()).encode()).hexdigest()


@dataclass(frozen=True)
class VerificationResult:
    name: str
    category: str
    status: str  # 'pass' | 'fail' | 'unknown' | 'error' | 'timeout'
    returncode: int | None
    stdout_sha256: str
    stderr_sha256: str
    termination_reason: str = "exit"
    execution_boundary: str = "trusted_fixture_unsandboxed"
    timed_out: bool = False

    def __post_init__(self) -> None:
        if self.status not in _RESULT_STATUSES:
            raise M4IntegrationError("invalid verification status")
        if self.category not in VERIFICATION_CATEGORIES:
            raise M4IntegrationError("verification category must be profile-declared")
        if self.status == "unknown":
            raise M4IntegrationError("evidence-bearing results may not be unknown")
        if self.returncode is not None and type(self.returncode) is not int:
            raise M4IntegrationError("invalid returncode")
        for name in ("stdout_sha256", "stderr_sha256"):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) != 64:
                raise M4IntegrationError(f"{name} must be a SHA-256 hex digest")
        if not isinstance(self.termination_reason, str) or not self.termination_reason:
            raise M4IntegrationError("termination reason must be recorded")
        if self.execution_boundary not in {"isolated_sandbox_v1", "trusted_fixture_unsandboxed"}:
            raise M4IntegrationError("unknown verification execution boundary")

    def to_dict(self) -> dict[str, object]:
        # Schema-explicit v2 serialization: the signed payload byte set is
        # FROZEN. The typed timeout flag (timed_out, added by the sandbox
        # timing work) is a runtime attribute only; it is encoded in the
        # payload through the already-versioned v2 fields
        # status == 'timeout', termination_reason == 'timeout' and the
        # deterministic returncode (124). Adding the flag here would mutate
        # canonical v2 signed bytes in place (review blocker, PR #108).
        return {
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "returncode": self.returncode,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "termination_reason": self.termination_reason,
            "execution_boundary": self.execution_boundary,
        }


@dataclass(frozen=True)
class ConflictResolution:
    policy: str
    choice: str
    rule_hash: str

    def __post_init__(self) -> None:
        if self.policy != "conservative_no_auto_merge":
            raise M4IntegrationError("only conservative conflict records are supported")
        if not self.choice or len(self.rule_hash) != 64:
            raise M4IntegrationError("conflict resolution requires a choice and rule hash")


@dataclass(frozen=True)
class IntegrationReceipt:
    execution_plan_hash: str
    integration_plan_hash: str
    input_receipt_hashes: tuple[str, ...]
    output_commit: str
    verification_results: tuple[VerificationResult, ...]
    conflict_resolutions: tuple[ConflictResolution, ...]
    integrated_at_ns: int
    station_key_id: str
    station_signature: str
    verification_policy_hash: str
    evidence_level: str = "development_fixture"
    schema_version: str = INTEGRATION_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_receipt_hashes", tuple(self.input_receipt_hashes))
        object.__setattr__(self, "verification_results", tuple(self.verification_results))
        object.__setattr__(self, "conflict_resolutions", tuple(self.conflict_resolutions))
        for value in (self.execution_plan_hash, self.integration_plan_hash, self.verification_policy_hash):
            if not isinstance(value, str) or len(value) != 64:
                raise M4IntegrationError("receipt hashes must be SHA-256 hex digests")

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "execution_plan_hash": self.execution_plan_hash,
            "integration_plan_hash": self.integration_plan_hash,
            "input_receipt_hashes": list(self.input_receipt_hashes),
            "output_commit": self.output_commit,
            "verification_results": [x.to_dict() for x in self.verification_results],
            "conflict_resolutions": [asdict(x) for x in self.conflict_resolutions],
            "integrated_at_ns": self.integrated_at_ns,
            "station_key_id": self.station_key_id,
            "verification_policy_hash": self.verification_policy_hash,
            "evidence_level": self.evidence_level,
        }

    @property
    def receipt_hash(self) -> str:
        return hashlib.sha256(canonical(self.unsigned_payload()).encode()).hexdigest()

    def verify_signature(self, verifier) -> bool:
        """Fail closed: a malformed or unverifiable signature is never valid."""
        try:
            return bool(verifier(self.station_key_id, canonical(self.unsigned_payload()),
                                 self.station_signature))
        except Exception:
            return False

    def to_dict(self) -> dict[str, object]:
        return {**self.unsigned_payload(), "station_signature": self.station_signature,
                "receipt_hash": self.receipt_hash}


@dataclass(frozen=True)
class IntegrationConsent:
    worker_id: str
    candidate_id: str
    baseline_version: str
    approved_at: str
    approved_by: str

    def __post_init__(self) -> None:
        if not all((self.worker_id, self.candidate_id, self.baseline_version,
                    self.approved_at, self.approved_by)):
            raise M4IntegrationError("integration consent requires explicit fields")

    @property
    def consent_hash(self) -> str:
        return hashlib.sha256(canonical(asdict(self)).encode()).hexdigest()


@dataclass
class ProjectRegistration:
    project_id: str
    baseline_version: str
    baseline_tree_hash: str
    plan: IntegrationPlan
    consent: IntegrationConsent | None = None


class Integrator:
    """One private integration worktree per integration; candidates stay quarantined."""

    def __init__(self, root: str | Path, *, observe: ObservationSink | None = None,
                 verification_policy_hash: str | None = None, clock_ns=time.time_ns):
        self.root = Path(root).absolute()
        self._observe = observe or (lambda payload: None)
        self._clock_ns = clock_ns
        self._registrations: dict[str, ProjectRegistration] = {}
        self._receipts: dict[str, IntegrationReceipt] = {}
        self._policy_hash = verification_policy_hash or hashlib.sha256(
            canonical({
                "commands": ALLOWED_VERIFICATION_COMMANDS,
                "fixture_bound_s": 900,
                "output_limit": MAX_OUTPUT,
            }).encode()).hexdigest()

    def register_project(self, project_id: str, baseline_version: str,
                         baseline_tree_hash: str, plan: IntegrationPlan) -> None:
        if not project_id or project_id in self._registrations:
            raise M4IntegrationError("unknown or duplicate project registration")
        if plan.expected_base_tree_hash != baseline_tree_hash:
            raise M4IntegrationError("integration plan baseline does not match registration")
        self._registrations[project_id] = ProjectRegistration(
            project_id, baseline_version, baseline_tree_hash, plan)

    def record_consent(self, project_id: str, consent: IntegrationConsent) -> None:
        registration = self._registration(project_id)
        if consent.worker_id != registration.plan.worker_id:
            raise M4IntegrationError("consent does not name the planned worker")
        if consent.candidate_id != registration.plan.candidate_id:
            raise M4IntegrationError("consent does not name the planned candidate")
        if consent.baseline_version != registration.baseline_version:
            raise M4IntegrationError("consent baseline drift detected")
        registration.consent = consent

    def integrate(self, project_id: str, source_root: str | Path,
                  artifacts: dict[str, bytes | None],
                  receipt_hashes: tuple[str, ...],
                  fixture_argv: tuple[str, ...] | None = None,
                  *, fixture_consent: IntegrationConsent | None = None) -> IntegrationReceipt:
        registration = self._registration(project_id)
        consent = registration.consent
        if consent is None or consent.consent_hash != registration.plan.approval_hash:
            raise M4IntegrationError("integration consent is missing or does not bind the plan")
        source = Path(source_root).absolute()
        if not source.is_dir():
            raise M4IntegrationError("candidate source is unavailable")
        if not isinstance(artifacts, dict) or not artifacts:
            raise M4IntegrationError("integration requires receipt-bound artifacts")
        # Untrusted project verification is structurally refused. Only an explicit
        # fixture-consent record may select the bounded trusted-fixture path.
        if fixture_argv is not None:
            if fixture_consent is None or fixture_consent.consent_hash != consent.consent_hash:
                raise M4IntegrationError("trusted fixture execution requires explicit consent")
        self._emit("M4IntegrationStarted", project_id=project_id,
                   worker_id=registration.plan.worker_id,
                   candidate_id=registration.plan.candidate_id,
                   integration_plan_hash=registration.plan.plan_hash)
        self.root.mkdir(parents=True, exist_ok=True)
        worktree = Path(tempfile.mkdtemp(prefix=f"m4-{project_id}-", dir=self.root))
        results: list[VerificationResult] = []
        try:
            inventory = snapshot(source)
            for relative, data in artifacts.items():
                if data is not None:
                    expected = hashlib.sha256(data).hexdigest()
                    entry = inventory.get(relative)
                    if entry is None or entry[0] != "file" or entry[2] != expected:
                        raise M4IntegrationError("artifact hash does not replay candidate evidence")
                apply_artifact(worktree, relative, data)
            integrated = snapshot(worktree)
            expected_names = {name for name, data in artifacts.items() if data is not None}
            present = {name for name, entry in integrated.items() if entry[0] == "file"}
            if not expected_names <= present:
                raise M4IntegrationError("integrated inventory is incomplete")
            for name in sorted(expected_names):
                entry = integrated[name]
                expected = hashlib.sha256(artifacts[name] or b"").hexdigest()
                results.append(VerificationResult(
                    name=f"artifact:{name}", category="artifact_hash_replay",
                    status="pass" if entry[2] == expected else "fail", returncode=0,
                    stdout_sha256=hashlib.sha256(entry[2].encode()).hexdigest(),
                    stderr_sha256=hashlib.sha256(b"").hexdigest()))
            if fixture_argv is not None:
                # Only the operator-consented trusted fixture may execute, and
                # only under the bounded process-group supervisor.
                fixture = run_trusted_fixture(fixture_argv, worktree, timeout_s=60,
                                              output_limit=MAX_OUTPUT)
                results.append(VerificationResult(
                    name="trusted_fixture", category="full_test_suite",
                    status=fixture.status, returncode=fixture.returncode,
                    stdout_sha256=fixture.stdout_sha256,
                    stderr_sha256=fixture.stderr_sha256,
                    termination_reason=fixture.reason, timed_out=fixture.timed_out))
            for command in registration.plan.verification_commands:
                argv = tuple(command.split())
                if not any(argv[:len(prefix)] == prefix for prefix in ALLOWED_VERIFICATION_COMMANDS):
                    results.append(VerificationResult(
                        name=command, category="static_policy_scan", status="error",
                        returncode=None, stdout_sha256=hashlib.sha256(b"").hexdigest(),
                        stderr_sha256=hashlib.sha256(b"not allowlisted".encode()).hexdigest(),
                        termination_reason="blocked_not_allowlisted"))
                    continue
                import subprocess
                try:
                    completed = subprocess.run(argv, cwd=worktree, capture_output=True,
                                               timeout=60, check=False)
                    results.append(VerificationResult(
                        name=command, category="static_policy_scan",
                        status="pass" if completed.returncode == 0 else "fail",
                        returncode=completed.returncode,
                        stdout_sha256=hashlib.sha256(completed.stdout).hexdigest(),
                        stderr_sha256=hashlib.sha256(completed.stderr).hexdigest()))
                except (OSError, subprocess.TimeoutExpired) as exc:
                    results.append(VerificationResult(
                        name=command, category="static_policy_scan", status="error",
                        returncode=None, stdout_sha256=hashlib.sha256(b"").hexdigest(),
                        stderr_sha256=hashlib.sha256(type(exc).__name__.encode()).hexdigest(),
                        termination_reason=type(exc).__name__))
        except M4SafetyError as exc:
            self._emit("M4IntegrationRefused", project_id=project_id, reason=type(exc).__name__)
            raise M4IntegrationError(str(exc)) from exc
        if any(result.status == "fail" for result in results):
            self._emit("M4IntegrationRejected", project_id=project_id,
                       failed=[result.name for result in results if result.status == "fail"])
            raise M4IntegrationError("verification failed; integration receipt refused")
        receipt = IntegrationReceipt(
            execution_plan_hash=hashlib.sha256(registration.plan.plan_hash.encode()).hexdigest(),
            integration_plan_hash=registration.plan.plan_hash,
            input_receipt_hashes=tuple(receipt_hashes),
            output_commit=hashlib.sha256(canonical(integrated).encode()).hexdigest()[:40],
            verification_results=tuple(results),
            conflict_resolutions=(),
            integrated_at_ns=self._clock_ns(),
            station_key_id="local-development-key",
            station_signature="pending-station-signing",
            verification_policy_hash=self._policy_hash)
        self._receipts[receipt.receipt_hash] = receipt
        self._emit("M4IntegrationCompleted", project_id=project_id,
                   receipt_hash=receipt.receipt_hash,
                   verification_results=[result.to_dict() for result in results])
        return receipt

    def receipts(self) -> dict[str, IntegrationReceipt]:
        return dict(self._receipts)

    def _registration(self, project_id: str) -> ProjectRegistration:
        try:
            return self._registrations[project_id]
        except KeyError:
            raise M4IntegrationError("unregistered project") from None

    def _emit(self, event: str, **payload: object) -> None:
        self._observe({"event": event, **payload})


def verify_receipt(receipt: IntegrationReceipt, verifier) -> bool:
    if not isinstance(receipt, IntegrationReceipt):
        return False
    return receipt.verify_signature(verifier)
