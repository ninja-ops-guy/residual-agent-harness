"""Deterministic M4 project integration over locally verified Evidence Bus receipts.

The integrator is deliberately mechanical: no LLM calls, no random merge choices,
and no direct worker-output reads. It consumes an EvidenceIntegrationPlan plus the
M3 Evidence Bus, resolves only identical/subset overlap automatically, requires
explicit HITL records for true conflicts, verifies the accumulated project state,
attributes a failing verification to a receipt by deterministic bisection, and
emits a Station-signed IntegrationReceipt.
"""
from __future__ import annotations

import difflib
import hashlib
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from residual.core import canonical, digest

from .evidence_bus import EvidenceBus
from .evidence_receipts import SIGNATURE_DOMAIN, EvidenceError, StationIdentity, WorkerReceipt, _sha256
from .m4_evidence import EvidenceIntegrationPlan, IntegrationConflict
from .runtime_journal import private_directory
from .runtime_workspace import git
from .worker_contract import WorkerContractError

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # pragma: no cover - same fail-closed dependency as M3
    InvalidSignature = None
    Ed25519PublicKey = None


INTEGRATION_SCHEMA = "factory-integration-receipt-v1"


class M4IntegrationError(WorkerContractError):
    pass


class IntegrationConflictError(M4IntegrationError):
    pass


class ProjectVerificationError(M4IntegrationError):
    def __init__(self, message: str, *, offending_receipt_hash: str | None = None):
        super().__init__(message)
        self.offending_receipt_hash = offending_receipt_hash


ObservationSink = Callable[[dict[str, object]], None]


@dataclass(frozen=True, slots=True)
class ConflictResolution:
    path: str
    selected_receipt_hash: str
    approved_by: str
    reason: str

    def __post_init__(self) -> None:
        if not all(isinstance(x, str) and x.strip() for x in
                   (self.path, self.selected_receipt_hash, self.approved_by, self.reason)):
            raise M4IntegrationError("complete HITL conflict resolution required")

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "selected_receipt_hash": self.selected_receipt_hash,
            "approved_by": self.approved_by.strip(),
            "reason": self.reason.strip(),
        }


@dataclass(frozen=True, slots=True)
class VerificationCommand:
    name: str
    category: str
    argv: tuple[str, ...]
    timeout_s: float = 120.0

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise M4IntegrationError("verification command name required")
        if self.category not in {"full_test_suite", "type_check", "contract_validation", "security_scan"}:
            raise M4IntegrationError("invalid verification category")
        if not self.argv or not all(isinstance(x, str) and x for x in self.argv):
            raise M4IntegrationError("verification argv required")
        if not isinstance(self.timeout_s, (int, float)) or self.timeout_s <= 0:
            raise M4IntegrationError("verification timeout must be positive")


@dataclass(frozen=True, slots=True)
class ProjectVerificationPolicy:
    commands: tuple[VerificationCommand, ...]
    secops_active: bool = False

    def __post_init__(self) -> None:
        if not self.commands:
            raise M4IntegrationError("project verification policy cannot be empty")
        names = [x.name for x in self.commands]
        if len(set(names)) != len(names):
            raise M4IntegrationError("verification command names must be unique")
        categories = {x.category for x in self.commands}
        required = {"full_test_suite", "type_check", "contract_validation"}
        if self.secops_active:
            required.add("security_scan")
        missing = required - categories
        if missing:
            raise M4IntegrationError("verification policy omits required categories")


@dataclass(frozen=True, slots=True)
class VerificationResult:
    name: str
    category: str
    status: str
    returncode: int | None
    stdout_sha256: str
    stderr_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "returncode": self.returncode,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
        }


@dataclass(frozen=True, slots=True)
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
    schema_version: str = INTEGRATION_SCHEMA

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "execution_plan_hash": self.execution_plan_hash,
            "integration_plan_hash": self.integration_plan_hash,
            "input_receipt_hashes": list(self.input_receipt_hashes),
            "output_commit": self.output_commit,
            "verification_results": [x.to_dict() for x in self.verification_results],
            "conflict_resolutions": [x.to_dict() for x in self.conflict_resolutions],
            "integrated_at_ns": self.integrated_at_ns,
            "station_key_id": self.station_key_id,
        }

    @property
    def receipt_hash(self) -> str:
        return digest(self.unsigned_payload())

    def to_dict(self) -> dict[str, object]:
        return {**self.unsigned_payload(), "receipt_hash": self.receipt_hash,
                "station_signature": self.station_signature}

    def verify_signature(self, public_key: bytes) -> bool:
        if Ed25519PublicKey is None or len(public_key) != 32:
            return False
        if _sha256(public_key) != self.station_key_id:
            return False
        try:
            Ed25519PublicKey.from_public_bytes(public_key).verify(
                bytes.fromhex(self.station_signature),
                SIGNATURE_DOMAIN + self.receipt_hash.encode("ascii"),
            )
            return True
        except (ValueError, InvalidSignature):
            return False


@dataclass(frozen=True, slots=True)
class IntegrationOutcome:
    receipt: IntegrationReceipt
    output_tree: str
    root_input_commit: str


class DeterministicIntegrator:
    def __init__(self, repository: str | Path, integration_root: str | Path,
                 bus: EvidenceBus, *, station_public_key: bytes,
                 observe: ObservationSink | None = None) -> None:
        self.repository = Path(repository).absolute()
        if self.repository.resolve() != self.repository or not self.repository.is_dir():
            raise M4IntegrationError("repository must be a resolved local directory")
        self.root = private_directory(Path(integration_root).absolute())
        if self.root == self.repository or self.root.is_relative_to(self.repository) or self.repository.is_relative_to(self.root):
            raise M4IntegrationError("integration storage and source repository must be disjoint")
        self.bus = bus
        self.station_public_key = station_public_key
        self.observe = observe

    def _emit(self, event: str, **payload: object) -> None:
        if self.observe is not None:
            self.observe({"event": event, "component": "factory-m4-integrator", **payload})

    def _receipts(self, plan: EvidenceIntegrationPlan) -> tuple[WorkerReceipt, ...]:
        receipts = tuple(self.bus.consumable(h, station_public_key=self.station_public_key)
                         for h in plan.ordered_receipt_hashes)
        if tuple(r.receipt_hash for r in receipts) != plan.ordered_receipt_hashes:
            raise M4IntegrationError("integration plan receipt order changed")
        if any(r.execution_plan_hash != plan.execution_plan_hash for r in receipts):
            raise M4IntegrationError("receipt belongs to another ExecutionPlan")
        return receipts

    def _root_commit(self, receipts: Sequence[WorkerReceipt]) -> str:
        by_hash = {r.receipt_hash: r for r in receipts}
        roots = [r for r in receipts if not r.parent_receipts]
        if not roots:
            raise M4IntegrationError("integration requires at least one root receipt")
        commits = {r.input_commit for r in roots}
        if len(commits) != 1:
            raise M4IntegrationError("root receipts do not share one input commit")
        root = next(iter(commits))
        resolved = git(self.repository, "rev-parse", "--verify", f"{root}^{{commit}}").decode().strip()
        if resolved != root:
            raise M4IntegrationError("root input commit does not resolve exactly")
        for r in receipts:
            for parent in r.parent_receipts:
                if parent not in by_hash:
                    raise M4IntegrationError("receipt parent absent from integration set")
        return root

    def _ancestors(self, receipts: Sequence[WorkerReceipt]) -> dict[str, set[str]]:
        parents = {r.receipt_hash: set(r.parent_receipts) for r in receipts}
        result: dict[str, set[str]] = {}
        def visit(value: str) -> set[str]:
            if value in result:
                return result[value]
            seen: set[str] = set()
            for parent in parents[value]:
                seen.add(parent)
                seen.update(visit(parent))
            result[value] = seen
            return seen
        for value in parents:
            visit(value)
        return result

    def _git_blob(self, commit: str, path: str) -> bytes | None:
        command = ["git", "-c", f"core.hooksPath={os.devnull}", "-c", "core.fsmonitor=false",
                   "-c", "submodule.recurse=false", "-C", str(self.repository), "show", f"{commit}:{path}"]
        env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
               "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                env=env, timeout=20, check=False)
        return result.stdout if result.returncode == 0 else None

    @staticmethod
    def _normalized_edits(before: bytes | None, after: bytes | None) -> frozenset[tuple[object, ...]]:
        before = before or b""
        after = after or b""
        try:
            left = before.decode("utf-8").splitlines(keepends=True)
            right = after.decode("utf-8").splitlines(keepends=True)
        except UnicodeDecodeError:
            return frozenset({("binary", hashlib.sha256(before).hexdigest(),
                               hashlib.sha256(after).hexdigest())})
        edits: set[tuple[object, ...]] = set()
        matcher = difflib.SequenceMatcher(a=left, b=right, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            replacement = tuple(hashlib.sha256(x.encode("utf-8")).hexdigest() for x in right[j1:j2])
            edits.add((tag, i1, i2, replacement))
        return frozenset(edits)

    def _artifact_bytes(self, receipt: WorkerReceipt, path: str) -> bytes | None:
        binding = next((a for a in receipt.artifacts if a.path == path), None)
        if binding is None:
            raise M4IntegrationError("planned overlap path absent from receipt")
        if binding.deleted:
            return None
        return self.bus.artifact(receipt.receipt_hash, path, station_public_key=self.station_public_key)

    def _classify_overlaps(self, plan: EvidenceIntegrationPlan,
                           receipts: Sequence[WorkerReceipt]) -> tuple[dict[str, str], tuple[IntegrationConflict, ...]]:
        by_hash = {r.receipt_hash: r for r in receipts}
        ancestors = self._ancestors(receipts)
        path_receipts: dict[str, list[WorkerReceipt]] = {}
        for receipt in receipts:
            for artifact in receipt.artifacts:
                path_receipts.setdefault(artifact.path, []).append(receipt)
        winners: dict[str, str] = {}
        true_conflicts: list[IntegrationConflict] = []
        for path in sorted(path_receipts):
            values = path_receipts[path]
            if len(values) == 1:
                winners[path] = values[0].receipt_hash
                continue
            # Ancestor/descendant changes are intentional sequential evolution; the
            # later topological receipt owns the final state. Only incomparable
            # receipts require overlap classification.
            incomparable: list[WorkerReceipt] = []
            for receipt in values:
                if any(receipt.receipt_hash in ancestors[other.receipt_hash] for other in values):
                    continue
                incomparable.append(receipt)
            if len(incomparable) <= 1:
                winners[path] = values[-1].receipt_hash
                continue
            edit_sets: list[tuple[WorkerReceipt, frozenset[tuple[object, ...]], bytes | None]] = []
            for receipt in incomparable:
                after = self._artifact_bytes(receipt, path)
                before = self._git_blob(receipt.input_commit, path)
                edits = self._normalized_edits(before, after)
                edit_sets.append((receipt, edits, after))
            # Identical changes collapse. Strict subset keeps the superset. If no
            # single receipt contains every peer edit, this is a true conflict.
            candidates = []
            for receipt, edits, _ in edit_sets:
                if all(other_edits <= edits for _, other_edits, _ in edit_sets):
                    candidates.append((len(edits), receipt.receipt_hash))
            if candidates:
                winners[path] = sorted(candidates, key=lambda x: (x[0], x[1]))[-1][1]
                continue
            true_conflicts.append(IntegrationConflict(
                path=path,
                receipt_hashes=tuple(r.receipt_hash for r in incomparable),
                artifact_hashes=tuple(next(a.sha256 for a in r.artifacts if a.path == path)
                                      for r in incomparable),
            ))
        return winners, tuple(true_conflicts)

    @staticmethod
    def _safe_path(worktree: Path, relative: str) -> Path:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise M4IntegrationError("invalid integration artifact path")
        current = worktree
        for part in path.parts[:-1]:
            current = current / part
            if current.exists() and current.is_symlink():
                raise M4IntegrationError("symlink parent forbidden in integration workspace")
        target = worktree / path
        if target.exists() and target.is_symlink():
            raise M4IntegrationError("symlink artifact target forbidden")
        return target

    def _apply_receipts(self, worktree: Path, receipts: Sequence[WorkerReceipt],
                        winners: dict[str, str]) -> None:
        for receipt in receipts:
            for artifact in receipt.artifacts:
                # For incomparable overlaps, only the deterministic winner applies.
                # Dependent later receipts naturally overwrite their ancestors.
                winner = winners.get(artifact.path)
                if winner is not None and winner != receipt.receipt_hash:
                    continue
                target = self._safe_path(worktree, artifact.path)
                if artifact.deleted:
                    if target.exists():
                        if target.is_dir():
                            raise M4IntegrationError("artifact deletion cannot target directory")
                        target.unlink()
                    continue
                data = self.bus.artifact(receipt.receipt_hash, artifact.path,
                                         station_public_key=self.station_public_key)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)

    def _run_verification(self, worktree: Path, policy: ProjectVerificationPolicy) -> tuple[VerificationResult, ...]:
        results: list[VerificationResult] = []
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
               "PYTHONHASHSEED": "0", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
        for check in policy.commands:
            try:
                process = subprocess.run(list(check.argv), cwd=worktree, env=env,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         timeout=check.timeout_s, check=False)
                status = "pass" if process.returncode == 0 else "fail"
                rc: int | None = process.returncode
                stdout, stderr = process.stdout, process.stderr
            except subprocess.TimeoutExpired as exc:
                status, rc = "fail", None
                stdout = exc.stdout or b""
                stderr = exc.stderr or b""
            results.append(VerificationResult(
                check.name, check.category, status, rc,
                hashlib.sha256(stdout).hexdigest(), hashlib.sha256(stderr).hexdigest(),
            ))
        return tuple(results)

    @staticmethod
    def _passes(results: Sequence[VerificationResult]) -> bool:
        return bool(results) and all(x.status == "pass" for x in results)

    def _worktree(self, name: str, root_commit: str) -> Path:
        path = self.root / name
        if path.exists() or path.is_symlink():
            raise M4IntegrationError("integration workspace already exists")
        git(self.repository, "worktree", "add", "--detach", str(path), root_commit)
        os.chmod(path, 0o700)
        return path

    def _remove_worktree(self, path: Path) -> None:
        if path.exists():
            git(self.repository, "worktree", "remove", "--force", str(path))

    def _verify_subset(self, root_commit: str, receipts: Sequence[WorkerReceipt],
                       winners: dict[str, str], policy: ProjectVerificationPolicy,
                       token: str) -> bool:
        path = self._worktree(f"bisect-{token}", root_commit)
        try:
            self._apply_receipts(path, receipts, winners)
            return self._passes(self._run_verification(path, policy))
        finally:
            self._remove_worktree(path)

    def _attribute_failure(self, root_commit: str, receipts: Sequence[WorkerReceipt],
                           winners: dict[str, str], policy: ProjectVerificationPolicy) -> str | None:
        candidates = list(receipts)
        round_id = 0
        while len(candidates) > 1:
            midpoint = len(candidates) // 2
            left, right = candidates[:midpoint], candidates[midpoint:]
            left_passes = self._verify_subset(root_commit, left, winners, policy, f"{round_id}-left")
            self._emit("M4VerificationBisect", round=round_id,
                       candidate_count=len(candidates), tested="left", passes=left_passes)
            if not left_passes:
                candidates = left
            else:
                right_passes = self._verify_subset(root_commit, right, winners, policy, f"{round_id}-right")
                self._emit("M4VerificationBisect", round=round_id,
                           candidate_count=len(candidates), tested="right", passes=right_passes)
                if not right_passes:
                    candidates = right
                else:
                    return None  # interaction-only failure; no single receipt is attributable
            round_id += 1
        return candidates[0].receipt_hash if candidates else None

    def integrate(self, plan: EvidenceIntegrationPlan, *, policy: ProjectVerificationPolicy,
                  station_identity: StationIdentity,
                  resolutions: Sequence[ConflictResolution] = ()) -> IntegrationOutcome:
        if not isinstance(plan, EvidenceIntegrationPlan):
            raise M4IntegrationError("EvidenceIntegrationPlan required")
        if station_identity.key_id != _sha256(self.station_public_key):
            raise M4IntegrationError("Station signing identity does not match Evidence Bus trust root")
        receipts = self._receipts(plan)
        root_commit = self._root_commit(receipts)
        winners, conflicts = self._classify_overlaps(plan, receipts)
        by_resolution = {r.path: r for r in resolutions}
        if len(by_resolution) != len(tuple(resolutions)):
            raise M4IntegrationError("duplicate HITL conflict resolution path")
        for conflict in conflicts:
            resolution = by_resolution.get(conflict.path)
            if resolution is None:
                self._emit("M4IntegrationConflict", path=conflict.path,
                           receipt_hashes=list(conflict.receipt_hashes), action="hitl_required")
                raise IntegrationConflictError("true integration conflict requires HITL resolution")
            if resolution.selected_receipt_hash not in conflict.receipt_hashes:
                raise M4IntegrationError("HITL resolution selects receipt outside conflict")
            winners[conflict.path] = resolution.selected_receipt_hash
            self._emit("M4ConflictResolved", path=conflict.path,
                       selected_receipt_hash=resolution.selected_receipt_hash,
                       approved_by=resolution.approved_by.strip())
        extra = set(by_resolution) - {c.path for c in conflicts}
        if extra:
            raise M4IntegrationError("HITL resolution supplied for non-conflicting path")

        worktree = self._worktree(f"integrate-{plan.plan_hash[:16]}", root_commit)
        try:
            self._apply_receipts(worktree, receipts, winners)
            results = self._run_verification(worktree, policy)
            self._emit("M4ProjectVerification", integration_plan_hash=plan.plan_hash,
                       passed=self._passes(results), checks=[x.to_dict() for x in results])
            if not self._passes(results):
                offender = self._attribute_failure(root_commit, receipts, winners, policy)
                if offender is not None:
                    task_id = next(r.task_id for r in receipts if r.receipt_hash == offender)
                    self._emit("M4ReceiptRevisionRequired", receipt_hash=offender,
                               task_id=task_id, action="replan")
                raise ProjectVerificationError("accumulated project verification failed",
                                               offending_receipt_hash=offender)
            git(worktree, "add", "-A")
            tree = git(worktree, "write-tree").decode().strip()
            identity = {"GIT_AUTHOR_NAME": "Residual Factory", "GIT_AUTHOR_EMAIL": "factory@localhost",
                        "GIT_COMMITTER_NAME": "Residual Factory", "GIT_COMMITTER_EMAIL": "factory@localhost",
                        "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z"}
            output_commit = git(worktree, "commit-tree", tree, "-p", root_commit,
                                data=f"Residual M4 integration {plan.plan_hash}\n".encode(),
                                extra_env=identity).decode().strip()
            integrated_at_ns = time.time_ns()
            unsigned = IntegrationReceipt(
                execution_plan_hash=plan.execution_plan_hash,
                integration_plan_hash=plan.plan_hash,
                input_receipt_hashes=plan.ordered_receipt_hashes,
                output_commit=output_commit,
                verification_results=results,
                conflict_resolutions=tuple(sorted(resolutions, key=lambda x: x.path)),
                integrated_at_ns=integrated_at_ns,
                station_key_id=station_identity.key_id,
                station_signature="pending",
            )
            signature = station_identity.sign(unsigned.receipt_hash)
            receipt = IntegrationReceipt(
                execution_plan_hash=unsigned.execution_plan_hash,
                integration_plan_hash=unsigned.integration_plan_hash,
                input_receipt_hashes=unsigned.input_receipt_hashes,
                output_commit=unsigned.output_commit,
                verification_results=unsigned.verification_results,
                conflict_resolutions=unsigned.conflict_resolutions,
                integrated_at_ns=unsigned.integrated_at_ns,
                station_key_id=unsigned.station_key_id,
                station_signature=signature,
            )
            self._emit("IntegrationReceiptIssued", receipt_hash=receipt.receipt_hash,
                       output_commit=output_commit, input_receipt_count=len(receipts))
            return IntegrationOutcome(receipt, tree, root_commit)
        finally:
            self._remove_worktree(worktree)
