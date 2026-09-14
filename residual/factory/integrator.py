"""M4 deterministic integration of Station-verified WorkerReceipts."""
from __future__ import annotations

import difflib
import hashlib
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from residual.core import canonical
from .evidence_bus import EvidenceBus, EvidenceError, StationIdentity, WorkerReceipt

INTEGRATION_DOMAIN = b"residual.factory.integration-receipt.v1\n"


class IntegrationError(EvidenceError):
    pass


@dataclass(frozen=True, slots=True)
class VerificationCommand:
    name: str
    argv: tuple[str, ...]
    timeout_s: float = 300.0

    def __post_init__(self):
        if not self.name or not self.argv or self.timeout_s <= 0:
            raise IntegrationError("invalid verification command")


@dataclass(frozen=True, slots=True)
class IntegrationReceipt:
    execution_plan_hash: str
    base_commit: str
    input_receipts: tuple[str, ...]
    output_tree: str
    output_commit: str
    verification_results: tuple[tuple[str, str], ...]
    resolutions: tuple[tuple[str, ...], ...]
    issued_at_ns: int
    station_key_id: str
    station_signature: str
    schema_version: str = "factory-integration-receipt-v1"

    def unsigned_payload(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "execution_plan_hash": self.execution_plan_hash,
                "base_commit": self.base_commit, "input_receipts": list(self.input_receipts),
                "output_tree": self.output_tree, "output_commit": self.output_commit,
                "verification_results": [list(x) for x in self.verification_results],
                "resolutions": [list(x) for x in self.resolutions], "issued_at_ns": self.issued_at_ns,
                "station_key_id": self.station_key_id}

    @property
    def receipt_hash(self) -> str:
        return hashlib.sha256(canonical(self.unsigned_payload()).encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {**self.unsigned_payload(), "receipt_hash": self.receipt_hash,
                "station_signature": self.station_signature}

    def verify(self, public_key: bytes) -> bool:
        return StationIdentity.verify_hash(self.receipt_hash, self.station_signature, public_key,
                                           key_id=self.station_key_id, domain=INTEGRATION_DOMAIN)


@dataclass(frozen=True, slots=True)
class IntegrationConflict:
    path: str
    receipt_hashes: tuple[str, ...]
    reason: str = "integration_conflict"


@dataclass(frozen=True, slots=True)
class HumanResolution:
    content: bytes
    approved_by: str
    decision_id: str

    def __post_init__(self):
        if not isinstance(self.content, bytes):
            raise IntegrationError("human resolution content must be bytes")
        if not isinstance(self.approved_by, str) or not self.approved_by.strip():
            raise IntegrationError("human resolution approver required")
        if not isinstance(self.decision_id, str) or not self.decision_id.strip():
            raise IntegrationError("human resolution decision_id required")

    @property
    def content_sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()

    def binding(self, path: str) -> tuple[str, str, str, str]:
        return (path, self.content_sha256, self.approved_by.strip(), self.decision_id.strip())


@dataclass(frozen=True, slots=True)
class IntegrationResult:
    status: str
    receipt: IntegrationReceipt | None
    conflicts: tuple[IntegrationConflict, ...] = ()
    offending_receipt: str | None = None


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=False, env={**os.environ, **(env or {})})
    if proc.returncode:
        raise IntegrationError("git operation failed")
    return proc.stdout.decode().strip()


def _text_edits(base: bytes, new: bytes):
    try:
        a, b = base.decode("utf-8").splitlines(keepends=True), new.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return None
    edits = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag != "equal":
            edits.append((tag, i1, i2, tuple(b[j1:j2])))
    return tuple(edits)


class DeterministicIntegrator:
    def __init__(self, repository: str | Path, bus: EvidenceBus, station_identity: StationIdentity,
                 *, observe: Callable[[dict[str, Any]], None] | None = None):
        self.repo = Path(repository).resolve()
        self.bus = bus
        self.identity = station_identity
        self.observe = observe or (lambda event: None)

    @staticmethod
    def topological(receipts: tuple[WorkerReceipt, ...]) -> tuple[WorkerReceipt, ...]:
        by = {r.receipt_hash: r for r in receipts}
        if len(by) != len(receipts):
            raise IntegrationError("duplicate input receipt")
        if any(set(r.parent_receipts) - by.keys() for r in receipts):
            raise IntegrationError("receipt parent is absent from integration set")
        done, out = set(), []
        while len(out) < len(receipts):
            ready = sorted((r for r in receipts if r.receipt_hash not in done and set(r.parent_receipts) <= done),
                           key=lambda r: r.receipt_hash)
            if not ready:
                raise IntegrationError("receipt dependency cycle")
            for r in ready:
                out.append(r)
                done.add(r.receipt_hash)
        return tuple(out)

    def _base_bytes(self, base_commit: str, path: str) -> bytes:
        proc = subprocess.run(["git", "-C", str(self.repo), "show", f"{base_commit}:{path}"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            return b""
        return proc.stdout

    def _resolve_overlaps(self, receipts: tuple[WorkerReceipt, ...], public_key: bytes):
        choices: dict[str, tuple[str, bytes | None]] = {}
        conflicts = []
        resolutions = []
        grouped: dict[str, list[tuple[WorkerReceipt, Any, bytes | None]]] = {}
        for r in receipts:
            self.bus.consumable(r.receipt_hash, station_public_key=public_key)
            for a in r.artifacts:
                data = None if a.deleted else self.bus.artifact(r.receipt_hash, a.path, station_public_key=public_key)
                grouped.setdefault(a.path, []).append((r, a, data))
        base_commit = receipts[0].input_commit
        for path, versions in sorted(grouped.items()):
            unique = {(a.sha256, a.deleted) for _, a, _ in versions}
            if len(unique) == 1:
                winner = min(versions, key=lambda x: x[0].receipt_hash)
                choices[path] = (winner[0].receipt_hash, winner[2])
                if len(versions) > 1:
                    resolutions.append((path, "identical_deduplicated"))
                continue
            base = self._base_bytes(base_commit, path)
            ranked = []
            for r, a, data in versions:
                if data is None:
                    ranked.append((r, a, data, None))
                    continue
                ranked.append((r, a, data, _text_edits(base, data)))
            winner = None
            for candidate in ranked:
                if candidate[3] is None:
                    continue
                cset = set(candidate[3])
                if all(other is candidate or (other[3] is not None and set(other[3]) < cset) for other in ranked):
                    winner = candidate
                    break
            if winner is None:
                conflicts.append(IntegrationConflict(path, tuple(sorted(r.receipt_hash for r, _, _ in versions))))
            else:
                choices[path] = (winner[0].receipt_hash, winner[2])
                resolutions.append((path, "strict_superset"))
        return choices, tuple(conflicts), tuple(resolutions)

    def _materialize(self, base_commit: str, choices: dict[str, tuple[str, bytes | None]],
                     receipt_hashes: tuple[str, ...], root: Path):
        work = root / "integration"
        _git(self.repo, "worktree", "add", "--detach", str(work), base_commit)
        try:
            for path, (_, data) in sorted(choices.items()):
                target = work / path
                if data is None:
                    if target.exists() or target.is_symlink():
                        target.unlink()
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
            _git(work, "add", "-A")
            tree = _git(work, "write-tree")
            message = canonical({"schema": "factory-deterministic-integration-v1", "receipts": list(receipt_hashes)})
            env = {"GIT_AUTHOR_NAME": "Residual", "GIT_AUTHOR_EMAIL": "residual@local.invalid",
                   "GIT_COMMITTER_NAME": "Residual", "GIT_COMMITTER_EMAIL": "residual@local.invalid",
                   "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
                   "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00"}
            proc = subprocess.run(["git", "-C", str(work), "commit-tree", tree, "-p", base_commit],
                                  input=(message + "\n").encode(), stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, env={**os.environ, **env})
            if proc.returncode:
                raise IntegrationError("deterministic commit creation failed")
            return work, tree, proc.stdout.decode().strip()
        except Exception:
            _git(self.repo, "worktree", "remove", "--force", str(work))
            raise

    @staticmethod
    def _verify(work: Path, commands: tuple[VerificationCommand, ...]) -> tuple[tuple[str, str], ...]:
        results = []
        for cmd in commands:
            try:
                proc = subprocess.run(list(cmd.argv), cwd=work, stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL, timeout=cmd.timeout_s)
                results.append((cmd.name, "pass" if proc.returncode == 0 else "fail"))
            except (subprocess.TimeoutExpired, OSError):
                results.append((cmd.name, "unknown"))
        return tuple(results)

    def integrate(self, receipt_hashes: tuple[str, ...], *, station_public_key: bytes,
                  verification: tuple[VerificationCommand, ...],
                  resolutions: dict[str, HumanResolution] | None = None) -> IntegrationResult:
        if not receipt_hashes:
            raise IntegrationError("integration requires receipts")
        receipts = tuple(self.bus.consumable(h, station_public_key=station_public_key) for h in receipt_hashes)
        if len({r.execution_plan_hash for r in receipts}) != 1 or len({r.input_commit for r in receipts}) != 1:
            raise IntegrationError("receipts must share plan and base commit")
        ordered = self.topological(receipts)
        ordered_hashes = tuple(r.receipt_hash for r in ordered)
        choices, conflicts, auto = self._resolve_overlaps(ordered, station_public_key)
        resolutions = resolutions or {}
        unresolved = []
        human = []
        for conflict in conflicts:
            if conflict.path not in resolutions:
                unresolved.append(conflict)
                continue
            resolution = resolutions[conflict.path]
            if not isinstance(resolution, HumanResolution):
                raise IntegrationError("conflict resolution requires HumanResolution")
            choices[conflict.path] = ("HITL", resolution.content)
            human.append(resolution.binding(conflict.path))
            self.observe({"event": "IntegrationConflictResolved", "path": conflict.path,
                          "approved_by": resolution.approved_by.strip(),
                          "decision_id": resolution.decision_id.strip(),
                          "content_sha256": resolution.content_sha256})
        if unresolved:
            self.observe({"event": "IntegrationConflict", "paths": [c.path for c in unresolved]})
            return IntegrationResult("CONFLICT", None, tuple(unresolved))
        with tempfile.TemporaryDirectory(prefix="residual-integration-") as td:
            work, tree, commit = self._materialize(ordered[0].input_commit, choices, ordered_hashes, Path(td))
            try:
                checks = self._verify(work, verification)
            finally:
                _git(self.repo, "worktree", "remove", "--force", str(work))
        if any(status != "pass" for _, status in checks):
            offender = self._first_failing_prefix(ordered, station_public_key, verification)
            self.observe({"event": "IntegrationVerificationFailed", "offending_receipt": offender})
            return IntegrationResult("VERIFY_FAILED", None, (), offender)
        fields = {"execution_plan_hash": ordered[0].execution_plan_hash,
                  "base_commit": ordered[0].input_commit,
                  "input_receipts": ordered_hashes, "output_tree": tree, "output_commit": commit,
                  "verification_results": checks, "resolutions": tuple(sorted((*auto, *human))),
                  "issued_at_ns": time.time_ns(), "station_key_id": self.identity.key_id}
        unsigned = {"schema_version": "factory-integration-receipt-v1", **fields}
        payload = {**unsigned, "input_receipts": list(fields["input_receipts"]),
                   "verification_results": [list(x) for x in fields["verification_results"]],
                   "resolutions": [list(x) for x in fields["resolutions"]]}
        payload_hash = hashlib.sha256(canonical(payload).encode()).hexdigest()
        signature = self.identity.sign_hash(payload_hash, domain=INTEGRATION_DOMAIN)
        receipt = IntegrationReceipt(**fields, station_signature=signature)
        if receipt.receipt_hash != payload_hash:
            raise IntegrationError("integration receipt canonicalization mismatch")
        self.observe({"event": "IntegrationReceiptIssued", "receipt_hash": receipt.receipt_hash,
                      "output_commit": commit, "output_tree": tree})
        return IntegrationResult("PASS", receipt)

    def _first_failing_prefix(self, ordered: tuple[WorkerReceipt, ...], public_key: bytes,
                              verification: tuple[VerificationCommand, ...]) -> str | None:
        lo, hi = 0, len(ordered) - 1
        candidate = None
        while lo <= hi:
            mid = (lo + hi) // 2
            subset = ordered[:mid + 1]
            choices, conflicts, _ = self._resolve_overlaps(subset, public_key)
            if conflicts:
                return None
            with tempfile.TemporaryDirectory(prefix="residual-bisect-") as td:
                work, _, _ = self._materialize(subset[0].input_commit, choices,
                                               tuple(r.receipt_hash for r in subset), Path(td))
                try:
                    failed = any(v != "pass" for _, v in self._verify(work, verification))
                finally:
                    _git(self.repo, "worktree", "remove", "--force", str(work))
            if failed:
                candidate = subset[-1].receipt_hash
                hi = mid - 1
            else:
                lo = mid + 1
        return candidate
