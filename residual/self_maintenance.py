"""Evidence-bounded recursive maintenance primitives.

The controller can evaluate candidate generations and declare them ready for an
external publication step. It intentionally has no merge operation, treats
unknown verification as non-acceptance, and never grants a self-maintaining
candidate authority over RESIDUAL's trust/governance surfaces.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Mapping


class SelfMaintenanceError(ValueError):
    pass


class VerificationState(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class CandidateState(str, Enum):
    REJECTED = "rejected"
    PR_READY = "pr_ready"


def canonical(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


SAFE_ACTIONS = frozenset({"file.write", "git.commit", "pull_request.create"})
FORBIDDEN_ACTIONS = frozenset(
    {
        "git.merge",
        "git.push.main",
        "branch_protection.write",
        "trust_boundary.write",
        "policy_authority.write",
        "self.approve",
    }
)
PROTECTED_WRITE_PREFIXES = (
    ".github/",
    "residual/control_plane/",
    "residual/factory/",
)
PROTECTED_WRITE_FILES = frozenset(
    {
        "residual/verifier.py",
        "residual/goalspec.py",
        "residual/loop.py",
    }
)
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def _repo_path(value: object, *, allow_protected: bool = True) -> str:
    """Validate an exact canonical repository-relative POSIX path.

    This is validation, not normalization: ambiguous spellings are rejected so
    policy comparisons cannot authorize one string while the host resolves a
    different pathname (for example Windows drive/backslash traversal).
    """
    if not isinstance(value, str) or not value or "\x00" in value:
        raise SelfMaintenanceError("repository paths must be non-empty strings")
    if value.startswith("/") or "\\" in value or ":" in value:
        raise SelfMaintenanceError("repository paths must be canonical POSIX-relative paths")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise SelfMaintenanceError("repository paths must not contain empty, dot, or parent components")
    if parts[0] == ".git":
        raise SelfMaintenanceError("Git metadata is never writable by self-maintenance")
    if not allow_protected and (
        value in PROTECTED_WRITE_FILES
        or any(value.startswith(prefix) for prefix in PROTECTED_WRITE_PREFIXES)
    ):
        raise SelfMaintenanceError("self-maintenance contract cannot grant protected write scope")
    return value


def _string_tuple(value: object, name: str, *, minimum: int = 0) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise SelfMaintenanceError(f"{name} must be a tuple")
    if len(value) < minimum:
        raise SelfMaintenanceError(f"{name} requires at least {minimum} entries")
    if any(not isinstance(item, str) or not item for item in value):
        raise SelfMaintenanceError(f"{name} must contain non-empty strings")
    if len(value) != len(set(value)):
        raise SelfMaintenanceError(f"{name} must not contain duplicates")
    return value


@dataclass(frozen=True)
class MaintenanceContract:
    mission_id: str
    base_commit: str
    issue_ref: str
    objective: str
    writable_paths: tuple[str, ...]
    allowed_actions: tuple[str, ...] = (
        "file.write",
        "git.commit",
        "pull_request.create",
    )
    proposer_id: str = "candidate-worker"
    verifier_ids: tuple[str, ...] = ("scope-verifier", "behavior-verifier")
    max_generations: int = 100
    require_external_merge: bool = True

    def __post_init__(self) -> None:
        for value, name in (
            (self.mission_id, "mission_id"),
            (self.base_commit, "base_commit"),
            (self.objective, "objective"),
            (self.proposer_id, "proposer_id"),
        ):
            if not isinstance(value, str) or not value:
                raise SelfMaintenanceError(f"{name} is required")
        if not isinstance(self.issue_ref, str):
            raise SelfMaintenanceError("issue_ref must be a string")

        paths = _string_tuple(self.writable_paths, "writable_paths", minimum=1)
        for path in paths:
            _repo_path(path, allow_protected=False)

        actions = _string_tuple(self.allowed_actions, "allowed_actions", minimum=1)
        if any(action in FORBIDDEN_ACTIONS or action not in SAFE_ACTIONS for action in actions):
            raise SelfMaintenanceError("self-maintenance actions exceed the closed safe action set")

        verifiers = _string_tuple(self.verifier_ids, "verifier_ids", minimum=2)
        if self.proposer_id in verifiers:
            raise SelfMaintenanceError("verifier identities must be distinct from the proposer")
        if type(self.max_generations) is not int or self.max_generations <= 0:
            raise SelfMaintenanceError("max_generations must be positive")
        if self.require_external_merge is not True:
            raise SelfMaintenanceError("self-maintenance must preserve external merge authority")

    @property
    def contract_hash(self) -> str:
        return digest(
            {
                "mission_id": self.mission_id,
                "base_commit": self.base_commit,
                "issue_ref": self.issue_ref,
                "objective": self.objective,
                "writable_paths": self.writable_paths,
                "allowed_actions": self.allowed_actions,
                "proposer_id": self.proposer_id,
                "verifier_ids": self.verifier_ids,
                "max_generations": self.max_generations,
                "require_external_merge": self.require_external_merge,
            }
        )


@dataclass(frozen=True)
class CandidateProposal:
    generation: int
    parent_receipt_hash: str | None
    files: Mapping[str, str]
    requested_actions: tuple[str, ...] = (
        "file.write",
        "git.commit",
        "pull_request.create",
    )
    proposer_id: str = "candidate-worker"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if type(self.generation) is not int or self.generation <= 0:
            raise SelfMaintenanceError("generation must be positive")
        if self.parent_receipt_hash is not None and (
            not isinstance(self.parent_receipt_hash, str)
            or _HEX64.fullmatch(self.parent_receipt_hash) is None
        ):
            raise SelfMaintenanceError("parent_receipt_hash must be null or lowercase SHA-256")
        if not isinstance(self.proposer_id, str) or not self.proposer_id:
            raise SelfMaintenanceError("proposer_id must be a non-empty string")
        _string_tuple(self.requested_actions, "requested_actions", minimum=1)

        if not isinstance(self.files, Mapping) or not self.files:
            raise SelfMaintenanceError("candidate must contain at least one file")
        frozen_files: dict[str, str] = {}
        for path, content in self.files.items():
            canonical_path = _repo_path(path)
            if not isinstance(content, str):
                raise SelfMaintenanceError("candidate file contents must be UTF-8 text strings")
            frozen_files[canonical_path] = content

        if not isinstance(self.metadata, Mapping) or any(
            not isinstance(key, str) for key in self.metadata
        ):
            raise SelfMaintenanceError("metadata must be a string-keyed mapping")
        frozen_metadata = dict(self.metadata)
        try:
            canonical(frozen_metadata)
        except (TypeError, ValueError, OverflowError) as exc:
            raise SelfMaintenanceError("metadata must be finite canonical JSON") from exc

        object.__setattr__(self, "files", MappingProxyType(frozen_files))
        object.__setattr__(self, "metadata", MappingProxyType(frozen_metadata))

    @property
    def proposal_hash(self) -> str:
        return digest(
            {
                "generation": self.generation,
                "parent_receipt_hash": self.parent_receipt_hash,
                "files": dict(sorted(self.files.items())),
                "requested_actions": self.requested_actions,
                "proposer_id": self.proposer_id,
                "metadata": dict(self.metadata),
            }
        )


@dataclass(frozen=True)
class VerificationResult:
    verifier_id: str
    state: VerificationState
    reason: str


@dataclass(frozen=True)
class GenerationReceipt:
    mission_id: str
    contract_hash: str
    generation: int
    proposal_hash: str
    previous_receipt_hash: str | None
    state: CandidateState
    verifications: tuple[VerificationResult, ...]
    rejection_reason: str | None
    merge_authorized: bool = False

    @property
    def receipt_hash(self) -> str:
        return digest(
            {
                "mission_id": self.mission_id,
                "contract_hash": self.contract_hash,
                "generation": self.generation,
                "proposal_hash": self.proposal_hash,
                "previous_receipt_hash": self.previous_receipt_hash,
                "state": self.state.value,
                "verifications": [
                    {
                        "verifier_id": result.verifier_id,
                        "state": result.state.value,
                        "reason": result.reason,
                    }
                    for result in self.verifications
                ],
                "rejection_reason": self.rejection_reason,
                "merge_authorized": self.merge_authorized,
            }
        )


Verifier = Callable[
    [CandidateProposal, MaintenanceContract], tuple[VerificationState | str, str]
]


class ProtectedSelfMaintenanceController:
    def __init__(self, contract: MaintenanceContract):
        if not isinstance(contract, MaintenanceContract):
            raise SelfMaintenanceError("controller requires a MaintenanceContract")
        self.contract = contract
        self._receipts: list[GenerationReceipt] = []

    @property
    def receipts(self) -> tuple[GenerationReceipt, ...]:
        return tuple(self._receipts)

    @property
    def last_receipt_hash(self) -> str | None:
        return self._receipts[-1].receipt_hash if self._receipts else None

    def _reject(
        self,
        proposal: CandidateProposal,
        reason: str,
        verifications: tuple[VerificationResult, ...] | list[VerificationResult] = (),
    ) -> GenerationReceipt:
        receipt = GenerationReceipt(
            self.contract.mission_id,
            self.contract.contract_hash,
            proposal.generation,
            proposal.proposal_hash,
            self.last_receipt_hash,
            CandidateState.REJECTED,
            tuple(verifications),
            reason,
            False,
        )
        self._receipts.append(receipt)
        return receipt

    def evaluate(
        self,
        proposal: CandidateProposal,
        verifiers: Mapping[str, Verifier],
    ) -> GenerationReceipt:
        if not isinstance(proposal, CandidateProposal):
            raise SelfMaintenanceError("controller requires a CandidateProposal")
        if not isinstance(verifiers, Mapping) or any(
            not isinstance(verifier_id, str) for verifier_id in verifiers
        ):
            return self._reject(proposal, "independent_verifier_set_mismatch")

        contract = self.contract
        if proposal.generation > contract.max_generations:
            return self._reject(proposal, "generation_budget_exhausted")
        if proposal.proposer_id != contract.proposer_id:
            return self._reject(proposal, "unexpected_proposer_identity")
        if proposal.generation != len(self._receipts) + 1:
            return self._reject(proposal, "non_monotonic_generation")
        if proposal.parent_receipt_hash != self.last_receipt_hash:
            return self._reject(proposal, "parent_receipt_mismatch")
        if any(
            action in FORBIDDEN_ACTIONS
            or action not in SAFE_ACTIONS
            or action not in contract.allowed_actions
            for action in proposal.requested_actions
        ):
            return self._reject(proposal, "authority_escalation_requested")
        if set(proposal.files) - set(contract.writable_paths):
            return self._reject(proposal, "candidate_write_scope_exceeded")
        if set(verifiers) != set(contract.verifier_ids):
            return self._reject(proposal, "independent_verifier_set_mismatch")

        results: list[VerificationResult] = []
        for verifier_id in contract.verifier_ids:
            try:
                verifier = verifiers[verifier_id]
                if not callable(verifier):
                    raise TypeError("verifier must be callable")
                state, reason = verifier(proposal, contract)
                state = VerificationState(state)
                if not isinstance(reason, str):
                    raise TypeError("verifier reason must be a string")
            except Exception:
                state, reason = VerificationState.UNKNOWN, "verifier_error"
            results.append(VerificationResult(verifier_id, state, reason[:1000]))

        if any(result.state is not VerificationState.PASS for result in results):
            return self._reject(proposal, "verification_not_unanimous_pass", results)

        receipt = GenerationReceipt(
            contract.mission_id,
            contract.contract_hash,
            proposal.generation,
            proposal.proposal_hash,
            self.last_receipt_hash,
            CandidateState.PR_READY,
            tuple(results),
            None,
            False,
        )
        self._receipts.append(receipt)
        return receipt

    def verify_receipt_chain(self) -> bool:
        """Verify internal lineage consistency; this is not external authentication."""
        previous: str | None = None
        for index, receipt in enumerate(self._receipts, start=1):
            if (
                receipt.generation != index
                or receipt.contract_hash != self.contract.contract_hash
                or receipt.previous_receipt_hash != previous
                or receipt.merge_authorized
            ):
                return False
            previous = receipt.receipt_hash
        return True


def receipt_to_dict(receipt: GenerationReceipt) -> dict[str, object]:
    return {
        "mission_id": receipt.mission_id,
        "contract_hash": receipt.contract_hash,
        "generation": receipt.generation,
        "proposal_hash": receipt.proposal_hash,
        "previous_receipt_hash": receipt.previous_receipt_hash,
        "state": receipt.state.value,
        "verifications": [
            {
                "verifier_id": result.verifier_id,
                "state": result.state.value,
                "reason": result.reason,
            }
            for result in receipt.verifications
        ],
        "rejection_reason": receipt.rejection_reason,
        "merge_authorized": receipt.merge_authorized,
        "receipt_hash": receipt.receipt_hash,
    }
