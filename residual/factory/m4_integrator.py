"""Deterministic M4 project integration over locally verified M3 evidence."""
from __future__ import annotations

import difflib
import hashlib
import math
import re
import tempfile
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from residual.core import digest

from .evidence_bus import EvidenceBus
from .evidence_receipts import SIGNATURE_DOMAIN, StationIdentity, WorkerReceipt, _sha256
from .m4_evidence import EvidenceIntegrationPlan, IntegrationConflict
from .m4_safety import artifact_parts, apply_artifact, snapshot, run_trusted_fixture
from .runtime_journal import private_directory
from .runtime_workspace import git
from .worker_contract import WorkerContractError

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # pragma: no cover
    InvalidSignature = None
    Ed25519PublicKey = None


INTEGRATION_SCHEMA = "factory-integration-receipt-v2"
ObservationSink = Callable[[dict[str, object]], None]


class M4IntegrationError(WorkerContractError):
    pass


class IntegrationConflictError(M4IntegrationError):
    pass


class ProjectVerificationError(M4IntegrationError):
    def __init__(self, message: str, *, offending_receipt_hash: str | None = None):
        super().__init__(message)
        self.offending_receipt_hash = offending_receipt_hash


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
    max_output_bytes: int = 1024 * 1024

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise M4IntegrationError("verification command name required")
        if self.category not in {"full_test_suite", "type_check", "contract_validation", "security_scan"}:
            raise M4IntegrationError("invalid verification category")
        if not isinstance(self.argv, tuple) or not self.argv or not all(
                isinstance(x, str) and x and "\x00" not in x for x in self.argv):
            raise M4IntegrationError("verification argv required")
        if type(self.timeout_s) not in (int, float) or not math.isfinite(self.timeout_s) or not 0 < self.timeout_s <= 900:
            raise M4IntegrationError("verification timeout must be finite and within (0, 900]")
        if type(self.max_output_bytes) is not int or not 1 <= self.max_output_bytes <= 16 * 1024 * 1024:
            raise M4IntegrationError("verification output cap must be an integer within [1, 16 MiB]")


@dataclass(frozen=True, slots=True)
class ProjectVerificationPolicy:
    commands: tuple[VerificationCommand, ...]
    secops_active: bool = False
    trusted_fixture_mode: bool = False

    def __post_init__(self) -> None:
        if type(self.trusted_fixture_mode) is not bool or type(self.secops_active) is not bool:
            raise M4IntegrationError("verification mode flags must be boolean")
        if not isinstance(self.commands, tuple) or not all(isinstance(c, VerificationCommand) for c in self.commands):
            raise M4IntegrationError("immutable verification commands required")
        if not self.commands:
            raise M4IntegrationError("project verification policy cannot be empty")
        names = [x.name for x in self.commands]
        if len(set(names)) != len(names):
            raise M4IntegrationError("verification command names must be unique")
        categories = {x.category for x in self.commands}
        required = {"full_test_suite", "type_check", "contract_validation"}
        if self.secops_active:
            required.add("security_scan")
        missing = sorted(required - categories)
        if missing:
            raise M4IntegrationError(
                "verification policy omits required categories: " + ", ".join(missing)
            )


@dataclass(frozen=True, slots=True)
class VerificationResult:
    name: str
    category: str
    status: str
    returncode: int | None
    stdout_sha256: str
    stderr_sha256: str
    termination_reason: str = "exit"
    execution_boundary: str = "trusted_fixture_unsandboxed"

    def to_dict(self) -> dict[str, object]:
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
    verification_policy_hash: str
    evidence_level: str = "development_fixture"
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
            "verification_policy_hash": self.verification_policy_hash,
            "evidence_level": self.evidence_level,
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
        if (self.root == self.repository or self.root.is_relative_to(self.repository)
                or self.repository.is_relative_to(self.root)):
            raise M4IntegrationError("integration storage and source repository must be disjoint")
        self.bus = bus
        self.station_public_key = station_public_key
        self.observe = observe

    def _emit(self, event: str, **payload: object) -> None:
        if self.observe is not None:
            self.observe({"event": event, "component": "factory-m4-integrator", **payload})

    def _receipts(self, plan: EvidenceIntegrationPlan) -> tuple[WorkerReceipt, ...]:
        if not plan.ordered_receipt_hashes:
            raise M4IntegrationError("integration plan cannot be empty")
        receipts = tuple(
            self.bus.consumable(value, station_public_key=self.station_public_key)
            for value in plan.ordered_receipt_hashes
        )
        if tuple(r.receipt_hash for r in receipts) != plan.ordered_receipt_hashes:
            raise M4IntegrationError("integration plan receipt order changed")
        if tuple(r.task_id for r in receipts) != plan.ordered_task_ids:
            raise M4IntegrationError("integration plan task order does not match receipts")
        if any(r.execution_plan_hash != plan.execution_plan_hash for r in receipts):
            raise M4IntegrationError("receipt belongs to another ExecutionPlan")
        if len(set(plan.ordered_receipt_hashes)) != len(receipts) or len(set(plan.ordered_task_ids)) != len(receipts):
            raise M4IntegrationError("duplicate integration receipt or task")
        seen: set[str] = set()
        for receipt in receipts:
            if any(parent not in seen for parent in receipt.parent_receipts):
                raise M4IntegrationError("integration plan is not topological")
            seen.add(receipt.receipt_hash)
        return receipts

    def _root_commit(self, receipts: Sequence[WorkerReceipt]) -> str:
        roots = [r for r in receipts if not r.parent_receipts]
        if not roots:
            raise M4IntegrationError("integration requires at least one root receipt")
        commits = {r.input_commit for r in roots}
        if len(commits) != 1:
            raise M4IntegrationError("root receipts do not share one input commit")
        root = next(iter(commits))
        for receipt in receipts:
            self._validated_commit(receipt.input_commit)
        resolved = git(self.repository, "rev-parse", "--verify", f"{root}^{{commit}}").decode().strip()
        if resolved != root:
            raise M4IntegrationError("root input commit does not resolve exactly")
        return root

    def _ancestors(self, receipts: Sequence[WorkerReceipt]) -> dict[str, set[str]]:
        parents = {r.receipt_hash: set(r.parent_receipts) for r in receipts}
        result: dict[str, set[str]] = {}

        def visit(value: str) -> set[str]:
            if value in result:
                return result[value]
            found: set[str] = set()
            for parent in parents[value]:
                if parent not in parents:
                    raise M4IntegrationError("receipt parent absent from integration set")
                found.add(parent)
                found.update(visit(parent))
            result[value] = found
            return found

        for value in parents:
            visit(value)
        return result

    def _validated_commit(self, commit: str) -> str:
        if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
            raise M4IntegrationError("exact SHA-1 Git commit required")
        resolved = git(self.repository, "rev-parse", "--verify", f"{commit}^{{commit}}",
                       extra_env={"GIT_NO_REPLACE_OBJECTS": "1"}).decode().strip()
        if resolved != commit:
            raise M4IntegrationError("input commit does not resolve exactly")
        return resolved

    def _git_blob(self, commit: str, path: str) -> bytes | None:
        artifact_parts(path)
        self._validated_commit(commit)
        env = {"GIT_NO_REPLACE_OBJECTS": "1"}
        listing = git(self.repository, "ls-tree", "-z", "--full-tree", commit,
                      "--", f":(literal){path}", extra_env=env)
        if not listing:
            return None  # Only successful exact-path lookup proves absence.
        entries = listing.rstrip(b"\0").split(b"\0")
        if len(entries) != 1:
            raise M4IntegrationError("ambiguous Git base path")
        metadata, name = entries[0].split(b"\t", 1)
        mode, kind, oid = metadata.split()
        if name != path.encode("utf-8") or kind != b"blob" or mode not in (b"100644", b"100755"):
            raise M4IntegrationError("Git base artifact is not a regular file")
        object_id = oid.decode("ascii")
        size = int(git(self.repository, "cat-file", "-s", object_id, extra_env=env))
        if size > 16 * 1024 * 1024:
            raise M4IntegrationError("Git base artifact exceeds 16 MiB")
        data = git(self.repository, "cat-file", "blob", object_id, extra_env=env)
        actual = git(self.repository, "hash-object", "--no-filters", "--stdin", data=data, extra_env=env).strip()
        if len(data) != size or actual != oid:
            raise M4IntegrationError("Git base object bytes do not match their identity")
        return data

    @staticmethod
    def _normalized_edits(before: bytes | None, after: bytes | None) -> frozenset[tuple[object, ...]]:
        # Preserve existence so an absent file and an empty file are not equivalent.
        before_exists, after_exists = before is not None, after is not None
        left_bytes = b"" if before is None else before
        right_bytes = b"" if after is None else after
        existence = ("existence", before_exists, after_exists)
        try:
            left = left_bytes.decode("utf-8").splitlines(keepends=True)
            right = right_bytes.decode("utf-8").splitlines(keepends=True)
        except UnicodeDecodeError:
            return frozenset({
                existence,
                ("binary", hashlib.sha256(left_bytes).hexdigest(),
                 hashlib.sha256(right_bytes).hexdigest()),
            })
        edits: set[tuple[object, ...]] = {existence}
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
        return self.bus.artifact(
            receipt.receipt_hash, path, station_public_key=self.station_public_key
        )

    def _classify_overlaps(self, receipts: Sequence[WorkerReceipt]) -> tuple[dict[str, str], tuple[IntegrationConflict, ...]]:
        ancestors = self._ancestors(receipts)
        path_receipts: dict[str, list[WorkerReceipt]] = {}
        for receipt in receipts:
            for artifact in receipt.artifacts:
                path_receipts.setdefault(artifact.path, []).append(receipt)

        winners: dict[str, str] = {}
        conflicts: list[IntegrationConflict] = []
        for path in sorted(path_receipts):
            values = path_receipts[path]
            if len(values) == 1:
                winners[path] = values[0].receipt_hash
                continue
            incomparable = [
                receipt for receipt in values
                if not any(receipt.receipt_hash in ancestors[other.receipt_hash] for other in values)
            ]
            if len(incomparable) <= 1:
                winners[path] = values[-1].receipt_hash
                continue

            base_values = [self._git_blob(receipt.input_commit, path) for receipt in incomparable]
            if any(value != base_values[0] for value in base_values[1:]):
                raise M4IntegrationError("incomparable edits have different base file states")
            edit_sets: list[tuple[WorkerReceipt, frozenset[tuple[object, ...]]]] = []
            for receipt in incomparable:
                after = self._artifact_bytes(receipt, path)
                before = self._git_blob(receipt.input_commit, path)
                edit_sets.append((receipt, self._normalized_edits(before, after)))

            candidates: list[tuple[int, str]] = []
            for receipt, edits in edit_sets:
                if all(other <= edits for _, other in edit_sets):
                    candidates.append((len(edits), receipt.receipt_hash))
            if candidates:
                winners[path] = max(candidates, key=lambda value: (value[0], value[1]))[1]
                continue

            conflicts.append(IntegrationConflict(
                path=path,
                receipt_hashes=tuple(r.receipt_hash for r in incomparable),
                artifact_hashes=tuple(
                    next(a.sha256 for a in r.artifacts if a.path == path) for r in incomparable
                ),
            ))
        return winners, tuple(conflicts)

    def _apply_receipts(self, worktree: Path, receipts: Sequence[WorkerReceipt],
                        winners: dict[str, str]) -> None:
        for receipt in receipts:
            for artifact in receipt.artifacts:
                if winners.get(artifact.path) != receipt.receipt_hash:
                    continue
                data = None if artifact.deleted else self._artifact_bytes(receipt, artifact.path)
                apply_artifact(worktree, artifact.path, data)

    @staticmethod
    def _require_execution_policy(policy: ProjectVerificationPolicy) -> None:
        if not isinstance(policy, ProjectVerificationPolicy) or not policy.trusted_fixture_mode:
            raise M4IntegrationError(
                "untrusted project verification blocked: no qualified isolation runner; "
                "trusted_fixture_mode is only for operator-reviewed development fixtures"
            )

    def _run_verification(self, worktree: Path,
                          policy: ProjectVerificationPolicy) -> tuple[VerificationResult, ...]:
        self._require_execution_policy(policy)
        before = snapshot(worktree)
        results = []
        for check in policy.commands:
            process = run_trusted_fixture(check.argv, worktree, timeout_s=check.timeout_s,
                                          output_limit=check.max_output_bytes)
            if snapshot(worktree) != before:
                self._emit("M4VerificationMutationRejected", check_name=check.name)
                raise M4IntegrationError("verification modified the frozen candidate workspace")
            results.append(VerificationResult(
                check.name, check.category, process.status, process.returncode,
                process.stdout_sha256, process.stderr_sha256, process.reason,
            ))
            if process.status != "pass":
                break
        return tuple(results)

    def _freeze_tree(self, worktree: Path, root_commit: str, receipts: Sequence[WorkerReceipt],
                     winners: dict[str, str]) -> str:
        # Build solely from signed artifact bytes + the validated root, never from
        # `git add -A` or a verifier-controlled index/worktree. Filters cannot run.
        by_hash = {r.receipt_hash: r for r in receipts}
        inventory = snapshot(worktree)
        with tempfile.TemporaryDirectory(prefix="frozen-index-", dir=self.root) as directory:
            env = {"GIT_INDEX_FILE": str(Path(directory) / "index"), "GIT_NO_REPLACE_OBJECTS": "1"}
            git(self.repository, "read-tree", root_commit, extra_env=env)
            for path, receipt_hash in sorted(winners.items()):
                artifact_parts(path)
                receipt = by_hash[receipt_hash]
                data = self._artifact_bytes(receipt, path)
                if data is None:
                    if path in inventory:
                        raise M4IntegrationError("deleted artifact still present")
                    git(self.repository, "update-index", "--force-remove", "--", path, extra_env=env)
                    continue
                actual = inventory.get(path)
                if actual is None or actual[0] != "file" or actual[2] != hashlib.sha256(data).hexdigest():
                    raise M4IntegrationError("materialized candidate differs from receipted bytes")
                oid = git(self.repository, "hash-object", "-w", "--no-filters", "--stdin",
                          data=data, extra_env=env).decode().strip()
                mode = "100755" if actual[1] & 0o111 else "100644"
                git(self.repository, "update-index", "--add", "--cacheinfo", f"{mode},{oid},{path}", extra_env=env)
            return git(self.repository, "write-tree", extra_env=env).decode().strip()

    @staticmethod
    def _passes(results: Sequence[VerificationResult]) -> bool:
        return bool(results) and all(result.status == "pass" for result in results)

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
                       policy: ProjectVerificationPolicy, token: str) -> bool:
        path = self._worktree(f"bisect-{token}", root_commit)
        try:
            winners, conflicts = self._classify_overlaps(receipts)
            if conflicts:
                # A subset that becomes ambiguous cannot be treated as a passing
                # counterfactual. Fail closed instead of silently choosing a side.
                return False
            self._apply_receipts(path, receipts, winners)
            return self._passes(self._run_verification(path, policy))
        finally:
            self._remove_worktree(path)

    def _attribute_failure(self, root_commit: str, receipts: Sequence[WorkerReceipt],
                           policy: ProjectVerificationPolicy) -> str | None:
        candidates = list(receipts)
        round_id = 0
        while len(candidates) > 1:
            midpoint = len(candidates) // 2
            left, right = candidates[:midpoint], candidates[midpoint:]
            left_passes = self._verify_subset(root_commit, left, policy, f"{round_id}-left")
            self._emit("M4VerificationBisect", round=round_id,
                       candidate_count=len(candidates), tested="left", passes=left_passes)
            if not left_passes:
                candidates = left
            else:
                right_passes = self._verify_subset(root_commit, right, policy, f"{round_id}-right")
                self._emit("M4VerificationBisect", round=round_id,
                           candidate_count=len(candidates), tested="right", passes=right_passes)
                if not right_passes:
                    candidates = right
                else:
                    return None
            round_id += 1
        return candidates[0].receipt_hash if candidates else None

    def integrate(self, plan: EvidenceIntegrationPlan, *, policy: ProjectVerificationPolicy,
                  station_identity: StationIdentity,
                  resolutions: Sequence[ConflictResolution] = ()) -> IntegrationOutcome:
        self._require_execution_policy(policy)
        if not isinstance(plan, EvidenceIntegrationPlan):
            raise M4IntegrationError("EvidenceIntegrationPlan required")
        if station_identity.key_id != _sha256(self.station_public_key):
            raise M4IntegrationError("Station signing identity does not match Evidence Bus trust root")

        receipts = self._receipts(plan)
        root_commit = self._root_commit(receipts)
        winners, conflicts = self._classify_overlaps(receipts)
        by_resolution = {resolution.path: resolution for resolution in resolutions}
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
        if set(by_resolution) - {conflict.path for conflict in conflicts}:
            raise M4IntegrationError("HITL resolution supplied for non-conflicting path")

        worktree = self._worktree(f"integrate-{plan.plan_hash[:16]}", root_commit)
        try:
            snapshot(worktree)  # Reject links/special files inherited from the root.
            self._apply_receipts(worktree, receipts, winners)
            tree = self._freeze_tree(worktree, root_commit, receipts, winners)
            results = self._run_verification(worktree, policy)
            passed = self._passes(results)
            self._emit("M4ProjectVerification", integration_plan_hash=plan.plan_hash,
                       passed=passed, checks=[result.to_dict() for result in results])
            if not passed:
                offender = self._attribute_failure(root_commit, receipts, policy)
                if offender is not None:
                    task_id = next(r.task_id for r in receipts if r.receipt_hash == offender)
                    self._emit("M4ReceiptRevisionRequired", receipt_hash=offender,
                               task_id=task_id, action="replan")
                raise ProjectVerificationError(
                    "accumulated project verification failed",
                    offending_receipt_hash=offender,
                )

            identity = {
                "GIT_AUTHOR_NAME": "Residual Factory",
                "GIT_AUTHOR_EMAIL": "factory@localhost",
                "GIT_COMMITTER_NAME": "Residual Factory",
                "GIT_COMMITTER_EMAIL": "factory@localhost",
                "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
                "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
            }
            output_commit = git(
                self.repository, "commit-tree", tree, "-p", root_commit,
                data=f"Residual M4 integration {plan.plan_hash}\n".encode(),
                extra_env={**identity, "GIT_NO_REPLACE_OBJECTS": "1"},
            ).decode().strip()

            unsigned = IntegrationReceipt(
                execution_plan_hash=plan.execution_plan_hash,
                integration_plan_hash=plan.plan_hash,
                input_receipt_hashes=plan.ordered_receipt_hashes,
                output_commit=output_commit,
                verification_results=results,
                conflict_resolutions=tuple(sorted(resolutions, key=lambda value: value.path)),
                integrated_at_ns=time.time_ns(),
                station_key_id=station_identity.key_id,
                station_signature="pending",
                verification_policy_hash=digest({
                    "execution_boundary": "trusted_fixture_unsandboxed",
                    "secops_active": policy.secops_active,
                    "commands": [dict(name=c.name, category=c.category, argv=list(c.argv),
                                      timeout_s=c.timeout_s, max_output_bytes=c.max_output_bytes)
                                 for c in policy.commands],
                }),
            )
            receipt = IntegrationReceipt(
                execution_plan_hash=unsigned.execution_plan_hash,
                integration_plan_hash=unsigned.integration_plan_hash,
                input_receipt_hashes=unsigned.input_receipt_hashes,
                output_commit=unsigned.output_commit,
                verification_results=unsigned.verification_results,
                conflict_resolutions=unsigned.conflict_resolutions,
                integrated_at_ns=unsigned.integrated_at_ns,
                station_key_id=unsigned.station_key_id,
                station_signature=station_identity.sign(unsigned.receipt_hash),
                verification_policy_hash=unsigned.verification_policy_hash,
            )
            self._emit("IntegrationReceiptIssued", receipt_hash=receipt.receipt_hash,
                       output_commit=output_commit, input_receipt_count=len(receipts))
            return IntegrationOutcome(receipt, tree, root_commit)
        finally:
            self._remove_worktree(worktree)
