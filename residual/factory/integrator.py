"""M4 deterministic receipt integrator.

No LLM or randomized merge path exists here. Only locally verified M3 receipts
are consumed. True conflicts fail closed unless an explicit human resolution is
supplied and recorded in the final IntegrationReceipt.
"""
from __future__ import annotations

import dataclasses
import difflib
import hashlib
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from residual.core import canonical
from .evidence_bus import EvidenceBus
from .evidence_receipts import EvidenceError, StationIdentity, WorkerReceipt
from .runtime_workspace import git


class IntegrationConflict(EvidenceError):
    def __init__(self, conflicts: dict[str, tuple[str, ...]]):
        self.conflicts = conflicts
        super().__init__("integration_conflict")


@dataclass(frozen=True, slots=True)
class IntegrationReceipt:
    input_receipts: tuple[str, ...]
    output_commit: str
    verification_results: tuple[tuple[str, str], ...]
    integrated_at_ns: int
    station_key_id: str
    station_signature: str
    human_resolutions: tuple[tuple[str, str], ...] = ()
    schema_version: str = "factory-integration-receipt-v1"

    def __post_init__(self):
        if self.schema_version != "factory-integration-receipt-v1":
            raise EvidenceError("unsupported integration receipt schema")
        if not self.input_receipts or len(set(self.input_receipts)) != len(self.input_receipts):
            raise EvidenceError("input receipts must be unique and nonempty")
        if not all(isinstance(x, str) and len(x) == 64 for x in self.input_receipts):
            raise EvidenceError("invalid input receipt hash")
        if not isinstance(self.output_commit, str) or len(self.output_commit) != 40:
            raise EvidenceError("invalid output commit")
        if not self.verification_results or any(v != "pass" for _, v in self.verification_results):
            raise EvidenceError("IntegrationReceipt requires passing verification")
        if type(self.integrated_at_ns) is not int or self.integrated_at_ns <= 0:
            raise EvidenceError("integration timestamp required")
        if not self.station_key_id or not self.station_signature:
            raise EvidenceError("Station identity required")
        object.__setattr__(self, "input_receipts", tuple(self.input_receipts))
        object.__setattr__(self, "verification_results", tuple(sorted(self.verification_results)))
        object.__setattr__(self, "human_resolutions", tuple(sorted(self.human_resolutions)))

    def unsigned_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "input_receipts": list(self.input_receipts),
            "output_commit": self.output_commit,
            "verification_results": [list(x) for x in self.verification_results],
            "integrated_at_ns": self.integrated_at_ns,
            "station_key_id": self.station_key_id,
            "human_resolutions": [list(x) for x in self.human_resolutions],
        }

    @property
    def integration_hash(self) -> str:
        return hashlib.sha256(canonical(self.unsigned_payload()).encode()).hexdigest()

    def verify(self, public_key: bytes) -> bool:
        # Reuse the same Ed25519 trust root/domain-independent key, with an M4 domain.
        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            if hashlib.sha256(public_key).hexdigest() != self.station_key_id:
                return False
            Ed25519PublicKey.from_public_bytes(public_key).verify(
                bytes.fromhex(self.station_signature),
                b"residual.factory.integration-receipt.v1\n" + self.integration_hash.encode("ascii"))
            return True
        except (ValueError, InvalidSignature, ImportError):
            return False


class DeterministicIntegrator:
    REQUIRED_CHECKS = ("full_test_suite", "type_check", "contract_validation")

    def __init__(self, repository: str | Path, bus: EvidenceBus, identity: StationIdentity,
                 *, observe: Callable[[dict[str, Any]], None] | None = None):
        self.repository = Path(repository).resolve()
        self.bus, self.identity = bus, identity
        self.observe = observe or (lambda event: None)

    def _emit(self, event: str, **data: Any) -> None:
        self.observe({"event": event, "component": "factory-integrator", **data})

    @staticmethod
    def topological_order(receipts: tuple[WorkerReceipt, ...]) -> tuple[WorkerReceipt, ...]:
        by_hash = {r.receipt_hash: r for r in receipts}
        if len(by_hash) != len(receipts):
            raise EvidenceError("duplicate integration receipt")
        missing = {p for r in receipts for p in r.parent_receipts if p not in by_hash}
        if missing:
            raise EvidenceError("receipt parent has not been integrated")
        indegree = {h: len(r.parent_receipts) for h, r in by_hash.items()}
        children: dict[str, list[str]] = {h: [] for h in by_hash}
        for h, r in by_hash.items():
            for parent in r.parent_receipts:
                children[parent].append(h)
        ready = sorted(h for h, degree in indegree.items() if degree == 0)
        ordered: list[WorkerReceipt] = []
        while ready:
            current = ready.pop(0)
            ordered.append(by_hash[current])
            for child in sorted(children[current]):
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child); ready.sort()
        if len(ordered) != len(receipts):
            raise EvidenceError("receipt dependency cycle")
        return tuple(ordered)

    def _base_bytes(self, commit: str, path: str) -> bytes:
        listed = git(self.repository, "ls-tree", "-r", "--name-only", commit, "--", path).decode().splitlines()
        if path not in listed:
            return b""
        return git(self.repository, "show", f"{commit}:{path}")

    @staticmethod
    def _edits(base: bytes, output: bytes) -> tuple[tuple[Any, ...], ...] | None:
        try:
            a = base.decode("utf-8").splitlines(keepends=True)
            b = output.decode("utf-8").splitlines(keepends=True)
        except UnicodeDecodeError:
            return None
        edits = []
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
            if tag != "equal":
                edits.append((tag, i1, i2, tuple(b[j1:j2])))
        return tuple(edits)

    def _classify_overlap(self, receipts: tuple[WorkerReceipt, ...], public_key: bytes) -> tuple[dict[str, str], dict[str, tuple[str, ...]]]:
        by_path: dict[str, list[tuple[WorkerReceipt, Any]]] = {}
        for receipt in receipts:
            for artifact in receipt.artifacts:
                by_path.setdefault(artifact.path, []).append((receipt, artifact))
        selected: dict[str, str] = {}
        conflicts: dict[str, tuple[str, ...]] = {}
        roots = [r for r in receipts if not r.parent_receipts]
        if not roots or len({r.input_commit for r in roots}) != 1:
            raise EvidenceError("integration roots require one common input commit")
        base_commit = roots[0].input_commit
        for path, entries in sorted(by_path.items()):
            if len(entries) == 1:
                selected[path] = entries[0][0].receipt_hash; continue
            fingerprints = {(a.sha256, a.deleted) for _, a in entries}
            if len(fingerprints) == 1:
                selected[path] = sorted(r.receipt_hash for r, _ in entries)[0]; continue
            base = self._base_bytes(base_commit, path)
            changes: list[tuple[str, tuple[tuple[Any, ...], ...] | None]] = []
            for receipt, artifact in entries:
                data = b"" if artifact.deleted else self.bus.artifact(receipt.receipt_hash, path, station_public_key=public_key)
                changes.append((receipt.receipt_hash, self._edits(base, data)))
            supersets = []
            for candidate_hash, candidate_edits in changes:
                if candidate_edits is None:
                    continue
                candidate_set = set(candidate_edits)
                if all(other is not None and set(other) <= candidate_set for _, other in changes):
                    supersets.append((len(candidate_set), candidate_hash))
            if supersets:
                selected[path] = sorted(supersets, key=lambda x: (-x[0], x[1]))[0][1]
            else:
                conflicts[path] = tuple(sorted(r.receipt_hash for r, _ in entries))
        return selected, conflicts

    def integrate(self, receipt_hashes: tuple[str, ...], *, checks: dict[str, Callable[[Path], bool]],
                  human_resolutions: dict[str, str] | None = None) -> IntegrationReceipt:
        if not receipt_hashes:
            raise EvidenceError("no receipts to integrate")
        public_key = self.identity.public_bytes()
        receipts = tuple(self.bus.consumable(h, station_public_key=public_key) for h in receipt_hashes)
        if len({r.execution_plan_hash for r in receipts}) != 1:
            raise EvidenceError("receipts belong to different execution plans")
        ordered = self.topological_order(receipts)
        selected, conflicts = self._classify_overlap(ordered, public_key)
        resolutions = human_resolutions or {}
        if conflicts:
            self._emit("IntegrationConflictDetected", conflicts={k: list(v) for k, v in conflicts.items()})
            unresolved = {path: choices for path, choices in conflicts.items()
                          if path not in resolutions or resolutions[path] not in choices}
            if unresolved:
                raise IntegrationConflict(unresolved)
            for path, choice in sorted(resolutions.items()):
                if path in conflicts:
                    selected[path] = choice
                    self._emit("IntegrationConflictResolved", path=path, selected_receipt=choice,
                               resolution_source="human")
        for name in self.REQUIRED_CHECKS:
            if name not in checks:
                raise EvidenceError(f"missing accumulated verification check: {name}")
        roots = [r for r in ordered if not r.parent_receipts]
        base_commit = roots[0].input_commit
        with tempfile.TemporaryDirectory() as temp:
            worktree = Path(temp) / "integration"
            git(self.repository, "worktree", "add", "--detach", str(worktree), base_commit)
            try:
                receipt_by_hash = {r.receipt_hash: r for r in ordered}
                for path, source_hash in sorted(selected.items()):
                    receipt = receipt_by_hash[source_hash]
                    artifact = next(a for a in receipt.artifacts if a.path == path)
                    target = worktree / path
                    if not target.resolve().is_relative_to(worktree.resolve()):
                        raise EvidenceError("integration path escapes worktree")
                    if artifact.deleted:
                        target.unlink(missing_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(self.bus.artifact(source_hash, path, station_public_key=public_key))
                results = []
                for name in sorted(checks):
                    passed = bool(checks[name](worktree))
                    results.append((name, "pass" if passed else "fail"))
                if any(status != "pass" for _, status in results):
                    self._emit("ProjectVerificationFailed", results=results)
                    raise EvidenceError("accumulated project verification failed")
                git(worktree, "add", "-A")
                tree = git(worktree, "write-tree").decode().strip()
                message = "Residual deterministic integration\n" + "\n".join(r.receipt_hash for r in ordered) + "\n"
                identity_env = {
                    "GIT_AUTHOR_NAME": "Residual Integrator", "GIT_AUTHOR_EMAIL": "integrator@localhost",
                    "GIT_COMMITTER_NAME": "Residual Integrator", "GIT_COMMITTER_EMAIL": "integrator@localhost",
                    "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
                }
                output_commit = git(worktree, "commit-tree", tree, "-p", base_commit,
                                    data=message.encode(), extra_env=identity_env).decode().strip()
            finally:
                git(self.repository, "worktree", "remove", "--force", str(worktree))
        fields = dict(input_receipts=tuple(r.receipt_hash for r in ordered), output_commit=output_commit,
                      verification_results=tuple(results), integrated_at_ns=time.time_ns(),
                      station_key_id=self.identity.key_id,
                      human_resolutions=tuple(sorted((k, v) for k, v in resolutions.items() if k in conflicts)),
                      station_signature="00")
        draft = IntegrationReceipt(**fields)
        signature = self.identity._private.sign(
            b"residual.factory.integration-receipt.v1\n" + draft.integration_hash.encode("ascii")).hex()
        receipt = dataclasses.replace(draft, station_signature=signature)
        self._emit("IntegrationReceiptIssued", integration_hash=receipt.integration_hash,
                   output_commit=receipt.output_commit, input_receipts=list(receipt.input_receipts))
        return receipt
