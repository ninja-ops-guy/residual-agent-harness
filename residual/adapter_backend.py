"""Fail-closed adapter binding from framework lifecycle events to the live RESIDUAL core.

This module deliberately does not invent a permissive gate. on_module_call requires
an evaluator backed by RESIDUAL core policy/verifier logic. With no evaluator, the
verdict is UNKNOWN and the run is aborted. run_harness binds an actual
residual.engine.Harness.run result and its verification ledger into the adapter
attestation stream.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .core import ContractError, Task, Verdict, canonical, digest

GENESIS_HASH = "0" * 64
VALID_VERDICTS = frozenset({"PASS", "FAIL", "UNKNOWN", "BLOCKED"})
_VALID_OUTCOMES = frozenset({"success", "error", "aborted"})


class CoreUnreachableError(RuntimeError):
    pass


class LedgerWriteError(RuntimeError):
    pass


class GateFiredError(RuntimeError):
    def __init__(self, gate_id: str, verdict: str, message: str = ""):
        super().__init__(message or f"{gate_id}: {verdict}")
        self.gate_id = gate_id
        self.verdict = verdict


class AttestationError(RuntimeError):
    pass


@dataclass(frozen=True)
class CoreGateDecision:
    """Typed bridge decision for core boundaries that include BLOCKED."""

    verdict: str
    gate_id: str
    evidence: dict

    def __post_init__(self) -> None:
        if self.verdict not in VALID_VERDICTS:
            raise ContractError("invalid adapter verdict")
        if not isinstance(self.gate_id, str) or not self.gate_id:
            raise ContractError("gate_id is required")
        canonical(self.evidence)


class LocalCoreTransport:
    """Health/write barrier used by the local core and deterministic chaos tests."""

    def ping(self) -> bool:
        return True

    def commit(self) -> None:
        return None


GateEvaluator = Callable[[str, str, str, str], Verdict | CoreGateDecision]


_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    run_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    event_id TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    digest TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    PRIMARY KEY(run_id, seq)
);
CREATE TABLE IF NOT EXISTS attestations (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    attestation_id TEXT NOT NULL UNIQUE,
    run_id TEXT NOT NULL UNIQUE,
    token_json TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
BEGIN SELECT RAISE(ABORT, 'append-only events'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
BEGIN SELECT RAISE(ABORT, 'append-only events'); END;
CREATE TRIGGER IF NOT EXISTS attest_no_update BEFORE UPDATE ON attestations
BEGIN SELECT RAISE(ABORT, 'append-only attestations'); END;
CREATE TRIGGER IF NOT EXISTS attest_no_delete BEFORE DELETE ON attestations
BEGIN SELECT RAISE(ABORT, 'append-only attestations'); END;
"""


def _canonical_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value) -> str:
    data = value if isinstance(value, bytes) else _canonical_bytes(value)
    return hashlib.sha256(data).hexdigest()


def recompute_attestation_id(token: dict) -> str:
    return _sha({k: v for k, v in token.items() if k != "attestation_id"})


def _normalize_repo_slug(url: str) -> str:
    """Reduce a git remote URL to owner/repo for comparison."""
    slug = url.strip()
    if slug.endswith(".git"):
        slug = slug[:-4]
    if ":" in slug and not slug.startswith(("http://", "https://")):
        slug = slug.split(":", 1)[1]  # scp-like syntax git@host:owner/repo
    else:
        slug = "/".join(slug.split("/")[-2:])
    return slug.lower()


def _git_identity(implementation_repo: str) -> tuple[str, str]:
    root = Path(__file__).resolve().parents[1]
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()
        tree = subprocess.run(
            ["git", "rev-parse", "HEAD^{tree}"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()
        remote = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"], cwd=root,
            check=False, capture_output=True, text=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=normal"], cwd=root,
            check=True, capture_output=True, text=True
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ContractError(
            "implementation commit/tree unavailable; pass impl_commit_sha and impl_tree_sha explicitly"
        ) from exc
    if len(commit) != 40 or len(tree) != 40:
        raise ContractError("invalid git implementation identity")
    # Auto-detected identity must come from the declared implementation repo;
    # an ambient unrelated checkout is never attestation authority. A checkout
    # without an origin remote cannot be proven either way and is rejected.
    if not remote or _normalize_repo_slug(remote) != _normalize_repo_slug(implementation_repo):
        raise ContractError(
            "git auto-detection does not match implementation_repo; "
            "pass impl_commit_sha and impl_tree_sha explicitly"
        )
    # A clean commit/tree pair is only authoritative when it identifies the
    # executable bytes actually running. Refuse ambient dirty/untracked state
    # rather than minting an attestation for HEAD while executing other bytes.
    if dirty.strip():
        raise ContractError(
            "git worktree is dirty; implementation identity would not bind the "
            "executed bytes. Commit/stash changes or pass an externally verified "
            "immutable implementation identity from a clean build."
        )
    return commit, tree


class LiveCoreResidualBackend:
    """Adapter backend whose authority comes from RESIDUAL core decisions."""

    def __init__(
        self,
        db_path: str = ":memory:",
        *,
        spec_version: str,
        spec_head_sha: str,
        gate_version: str = "residual-core@1",
        evaluator_id: str = "residual-core",
        gate_evaluator: GateEvaluator | None = None,
        transport: LocalCoreTransport | None = None,
        implementation_repo: str = "ninja-ops-guy/residual-agent-harness",
        impl_commit_sha: str | None = None,
        impl_tree_sha: str | None = None,
        issuer: str = "residual-agent-harness/live-core",
    ):
        if len(spec_head_sha) != 40:
            raise ContractError("spec_head_sha must be a 40-character git commit")
        if (impl_commit_sha is None) != (impl_tree_sha is None):
            raise ContractError("implementation commit/tree must be supplied together")
        if impl_commit_sha is None:
            impl_commit_sha, impl_tree_sha = _git_identity(implementation_repo)
        assert impl_tree_sha is not None
        if len(impl_commit_sha) != 40 or len(impl_tree_sha) != 40:
            raise ContractError("implementation commit/tree must be 40-character git ids")

        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self._lock = threading.RLock()

        self.spec_version = spec_version
        self.spec_head_sha = spec_head_sha
        self.gate_version = gate_version
        self.evaluator_id = evaluator_id
        self.gate_evaluator = gate_evaluator
        self.transport = transport or LocalCoreTransport()
        self.implementation_repo = implementation_repo
        self.impl_commit_sha = impl_commit_sha
        self.impl_tree_sha = impl_tree_sha
        self.issuer = issuer
        self._started: set[str] = set()
        self._terminal: set[str] = set()
        self._verdicts: dict[str, dict[str, str]] = {}
        self._verify_event_chains()
        self._verify_attestations()
        self._restore_runtime_state()

    def _verify_attestations(self) -> None:
        """Re-derive every stored attestation from the event ledger.

        Triggers block UPDATE/DELETE through SQLite, but a byte-level edit or a
        restored backup can still leave token_json inconsistent with the events
        table. On open, recompute each token's content address, its evidence
        manifest against the events actually recorded, and the cross-run
        attestation chain. Any mismatch fails closed: the backend refuses to
        serve potentially fabricated evidence.
        """
        rows = self._conn.execute(
            "SELECT seq,attestation_id,run_id,token_json FROM attestations ORDER BY seq"
        ).fetchall()
        prev_id = GENESIS_HASH
        for _seq, attestation_id, run_id, token_json in rows:
            token = json.loads(token_json)
            if token.get("attestation_id") != attestation_id:
                raise LedgerWriteError(f"attestation id/key mismatch for run {run_id}")
            if recompute_attestation_id(token) != attestation_id:
                raise LedgerWriteError(f"attestation content address invalid for run {run_id}")
            if token.get("prev_attestation_hash") != prev_id:
                raise LedgerWriteError(f"attestation chain broken at run {run_id}")
            recorded = [e for e in self.events(run_id) if e["kind"] != "attestation.issued"]
            if _sha({"run_id": run_id, "events": recorded}) != token.get("evidence_manifest_hash"):
                raise LedgerWriteError(f"evidence manifest mismatch for run {run_id}")
            prev_id = attestation_id

    @property
    def gate_set_hash(self) -> str:
        return _sha({"gate_version": self.gate_version, "evaluator_id": self.evaluator_id})

    def _verify_event_chains(self) -> None:
        rows = self._conn.execute(
            "SELECT run_id,seq,event_id,domain,kind,payload_json,digest,prev_hash "
            "FROM events ORDER BY run_id,seq"
        ).fetchall()
        heads: dict[str, str] = {}
        seqs: dict[str, int] = {}
        for run_id, seq, event_id, domain, kind, payload_json, event_digest, prev_hash in rows:
            expected_prev = heads.get(run_id, GENESIS_HASH)
            expected_seq = seqs.get(run_id, 0) + 1
            body = {
                "domain": domain,
                "event_id": event_id,
                "kind": kind,
                "payload": json.loads(payload_json),
                "prev_hash": expected_prev,
                "run_id": run_id,
                "seq": expected_seq,
            }
            if seq != expected_seq or prev_hash != expected_prev or _sha(body) != event_digest:
                raise LedgerWriteError(f"hash-chain verification failed for {run_id} at seq {seq}")
            heads[run_id] = event_digest
            seqs[run_id] = seq

    def _restore_runtime_state(self) -> None:
        rows = self._conn.execute(
            "SELECT run_id,kind,payload_json FROM events ORDER BY run_id,seq"
        ).fetchall()
        for run_id, kind, payload_json in rows:
            payload = json.loads(payload_json)
            if kind == "run.started":
                self._started.add(run_id)
            elif kind == "module.called":
                gate_id = payload.get("gate_id")
                verdict = payload.get("verdict")
                if gate_id and verdict in VALID_VERDICTS:
                    self._verdicts.setdefault(run_id, {})[gate_id] = verdict
            elif kind == "gate.fired":
                gate_id = payload.get("gate_id")
                verdict = payload.get("verdict")
                if gate_id and verdict in VALID_VERDICTS:
                    self._verdicts.setdefault(run_id, {})[gate_id] = verdict
            elif kind == "run.completed":
                self._terminal.add(run_id)
                outcome = payload.get("outcome")
                if outcome in _VALID_OUTCOMES:
                    self._verdicts.setdefault(run_id, {})["CORE-RUN-OUTCOME"] = {
                        "success": "PASS", "error": "FAIL", "aborted": "BLOCKED"
                    }[outcome]

    def _append_event(
        self, run_id: str, domain: str, kind: str, payload: dict, *, event_id: str | None = None
    ) -> str:
        event_id = event_id or str(uuid.uuid4())
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                row = self._conn.execute(
                    "SELECT seq,digest FROM events WHERE run_id=? ORDER BY seq DESC LIMIT 1",
                    (run_id,),
                ).fetchone()
                prev_hash = row[1] if row else GENESIS_HASH
                seq = (row[0] if row else 0) + 1
                body = {
                    "domain": domain,
                    "event_id": event_id,
                    "kind": kind,
                    "payload": payload,
                    "prev_hash": prev_hash,
                    "run_id": run_id,
                    "seq": seq,
                }
                event_digest = _sha(body)
                self._conn.execute(
                    "INSERT INTO events(run_id,seq,event_id,domain,kind,payload_json,digest,prev_hash) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (run_id, seq, event_id, domain, kind, canonical(payload), event_digest, prev_hash),
                )
                self.transport.commit()
                self._conn.commit()
                return event_digest
            except sqlite3.IntegrityError:
                self._conn.rollback()
                row = self._conn.execute(
                    "SELECT digest,run_id,domain,kind,payload_json FROM events WHERE event_id=?",
                    (event_id,),
                ).fetchone()
                if row is None:
                    raise LedgerWriteError(f"event admission failed: {event_id}")
                # Idempotent admission is only valid for content-identical replays.
                # Chain position (seq/prev_hash) is excluded: a legitimate retry may
                # re-arrive after the ledger advanced. A reused event_id carrying
                # divergent content is evidence corruption and must fail closed.
                _, st_run, st_domain, st_kind, st_payload = row
                if (st_run, st_domain, st_kind) != (run_id, domain, kind) or (
                    json.loads(st_payload) != payload
                ):
                    raise LedgerWriteError(
                        f"event_id collision with divergent payload: {event_id}"
                    )
                return row[0]
            except Exception as exc:
                self._conn.rollback()
                if isinstance(exc, LedgerWriteError):
                    raise
                raise LedgerWriteError(f"ledger write failed for {kind}: {exc}") from exc

    def _decision(self, run_id: str, module: str, call_id: str, inputs_digest: str) -> CoreGateDecision:
        if self.gate_evaluator is None:
            return CoreGateDecision(
                "UNKNOWN",
                f"CORE:{module}",
                {"reason": "no_core_evaluator_bound", "module": module},
            )
        try:
            raw = self.gate_evaluator(run_id, module, call_id, inputs_digest)
        except Exception as exc:
            return CoreGateDecision(
                "UNKNOWN",
                f"CORE:{module}",
                {"reason": "core_evaluator_error", "error_type": type(exc).__name__},
            )
        if isinstance(raw, CoreGateDecision):
            return raw
        if not isinstance(raw, Verdict):
            return CoreGateDecision(
                "UNKNOWN",
                f"CORE:{module}",
                {"reason": "invalid_core_verdict_type", "type": type(raw).__name__},
            )
        return CoreGateDecision(
            {"pass": "PASS", "fail": "FAIL", "unknown": "UNKNOWN"}[raw.status],
            f"CORE:{module}",
            {"core_status": raw.status, "core_code": raw.code, "core_message": raw.message},
        )

    def on_run_start(self, run_id: str, spec_id: str, metadata: dict | None = None) -> None:
        try:
            if not self.transport.ping():
                raise CoreUnreachableError("core health check returned false")
        except CoreUnreachableError:
            raise
        except Exception as exc:
            raise CoreUnreachableError(f"core unreachable: {exc}") from exc
        if run_id in self._started or run_id in self._terminal:
            raise LedgerWriteError(f"duplicate run start: {run_id}")
        self._append_event(run_id, "run", "run.started", {"spec_id": spec_id, "metadata": metadata or {}})
        self._started.add(run_id)

    def _record_module_decision(
        self,
        run_id: str,
        module: str,
        call_id: str,
        inputs_digest: str,
        decision: CoreGateDecision,
        *,
        propagate: bool,
    ) -> str:
        if run_id not in self._started or run_id in self._terminal:
            raise LedgerWriteError(f"run not open: {run_id}")
        self._append_event(
            run_id,
            "module",
            "module.called",
            {
                "module": module,
                "call_id": call_id,
                "inputs_digest": inputs_digest,
                "gate_id": decision.gate_id,
                "verdict": decision.verdict,
                "core_evidence": decision.evidence,
            },
        )
        self._verdicts.setdefault(run_id, {})[decision.gate_id] = decision.verdict
        if decision.verdict != "PASS":
            self._append_event(
                run_id,
                "gate",
                "gate.fired",
                {"gate_id": decision.gate_id, "module": module, "verdict": decision.verdict},
            )
            if propagate:
                self.on_run_complete(run_id, "aborted")
                raise GateFiredError(decision.gate_id, decision.verdict)
        return decision.verdict

    def on_module_call(self, run_id: str, module: str, call_id: str, inputs_digest: str) -> str:
        decision = self._decision(run_id, module, call_id, inputs_digest)
        return self._record_module_decision(
            run_id, module, call_id, inputs_digest, decision, propagate=True
        )

    def on_run_complete(self, run_id: str, outcome: str) -> None:
        if outcome not in _VALID_OUTCOMES:
            raise LedgerWriteError(f"invalid outcome: {outcome}")
        if run_id not in self._started or run_id in self._terminal:
            raise LedgerWriteError(f"run not open: {run_id}")
        run_verdict = {"success": "PASS", "error": "FAIL", "aborted": "BLOCKED"}[outcome]
        self._verdicts.setdefault(run_id, {})["CORE-RUN-OUTCOME"] = run_verdict
        self._append_event(run_id, "run", "run.completed", {"outcome": outcome})
        self._terminal.add(run_id)
        self._issue_attestation(run_id)

    def _issue_attestation(self, run_id: str) -> None:
        # Serialize predecessor selection with admission. Without this lock,
        # concurrent completions can both observe the same predecessor and fork
        # the global attestation chain even though their INSERTs later serialize.
        with self._lock:
            events = self.events(run_id)
            evidence_manifest_hash = _sha({"run_id": run_id, "events": events})
            prev = self._conn.execute(
                "SELECT token_json FROM attestations ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            prev_hash = json.loads(prev[0])["attestation_id"] if prev else GENESIS_HASH
            token = {
                "spec_version": self.spec_version,
                "spec_head_sha": self.spec_head_sha,
                "gate_version": self.gate_version,
                "gate_set_hash": self.gate_set_hash,
                "implementation": {
                    "repo": self.implementation_repo,
                    "commit_sha": self.impl_commit_sha,
                    "tree_sha": self.impl_tree_sha,
                },
                "evidence_manifest_hash": evidence_manifest_hash,
                "verdicts": dict(self._verdicts.get(run_id, {})),
                "issued_ns": time.time_ns(),
                "issuer": self.issuer,
                "prev_attestation_hash": prev_hash,
            }
            token["attestation_id"] = recompute_attestation_id(token)
    
            # AT-3 is one transaction: the token and its ledger admission either
            # both become durable or neither does.
            with self._lock:
                try:
                    self._conn.execute("BEGIN IMMEDIATE")
                    row = self._conn.execute(
                        "SELECT seq,digest FROM events WHERE run_id=? ORDER BY seq DESC LIMIT 1",
                        (run_id,),
                    ).fetchone()
                    event_prev = row[1] if row else GENESIS_HASH
                    seq = (row[0] if row else 0) + 1
                    event_body = {
                        "domain": "attestation",
                        "event_id": token["attestation_id"],
                        "kind": "attestation.issued",
                        "payload": {"attestation_id": token["attestation_id"]},
                        "prev_hash": event_prev,
                        "run_id": run_id,
                        "seq": seq,
                    }
                    event_digest = _sha(event_body)
                    self._conn.execute(
                        "INSERT INTO attestations(attestation_id,run_id,token_json) VALUES(?,?,?)",
                        (token["attestation_id"], run_id, canonical(token)),
                    )
                    self._conn.execute(
                        "INSERT INTO events(run_id,seq,event_id,domain,kind,payload_json,digest,prev_hash) "
                        "VALUES(?,?,?,?,?,?,?,?)",
                        (
                            run_id,
                            seq,
                            token["attestation_id"],
                            "attestation",
                            "attestation.issued",
                            canonical({"attestation_id": token["attestation_id"]}),
                            event_digest,
                            event_prev,
                        ),
                    )
                    self.transport.commit()
                    self._conn.commit()
                except Exception as exc:
                    self._conn.rollback()
                    raise LedgerWriteError(f"attestation admission failed atomically: {exc}") from exc
    
    def get_attestation(self, run_id: str) -> dict:
        row = self._conn.execute(
            "SELECT token_json FROM attestations WHERE run_id=?", (run_id,)
        ).fetchone()
        if row is None:
            raise AttestationError(f"no attestation for run {run_id}")
        return json.loads(row[0])

    def events(self, run_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT seq,event_id,run_id,domain,kind,payload_json,digest,prev_hash "
            "FROM events WHERE run_id=? ORDER BY seq",
            (run_id,),
        ).fetchall()
        return [
            {
                "seq": seq,
                "event_id": event_id,
                "run_id": rid,
                "domain": domain,
                "kind": kind,
                "payload": json.loads(payload_json),
                "digest": event_digest,
                "prev_hash": prev_hash,
            }
            for seq, event_id, rid, domain, kind, payload_json, event_digest, prev_hash in rows
        ]

    def run_harness(self, harness, task: Task, *, run_id: str | None = None, spec_id: str | None = None):
        """Execute the actual Harness and attest exactly the verdicts it produced."""
        run_id = run_id or str(uuid.uuid4())
        spec_id = spec_id or f"residual-spec@{self.spec_version}"
        self.on_run_start(run_id, spec_id, {"task_id": task.id, "binding": "Harness.run"})
        try:
            result = harness.run(task)
        except Exception as exc:
            self._verdicts.setdefault(run_id, {})["CORE-EXECUTION"] = "FAIL"
            self._append_event(
                run_id,
                "gate",
                "gate.fired",
                {
                    "gate_id": "CORE-EXECUTION",
                    "module": "Harness.run",
                    "verdict": "FAIL",
                    "error_type": type(exc).__name__,
                },
            )
            self.on_run_complete(run_id, "error")
            raise

        verification: dict[str, dict] = {}
        for event in getattr(getattr(harness, "ledger", None), "events", []):
            if event.get("kind") == "verification":
                data = event.get("data", {})
                if "obligation_id" in data:
                    verification[data["obligation_id"]] = data

        decisions: list[tuple[str, CoreGateDecision]] = []
        station_receipts = result.get("station_receipts", {})
        unresolved = result.get("unresolved", {})
        for obligation in task.obligations:
            ev = verification.get(obligation.id)
            if ev is not None:
                verdict = {"pass": "PASS", "fail": "FAIL", "unknown": "UNKNOWN"}.get(
                    ev.get("status"), "UNKNOWN"
                )
                evidence = {
                    "source": "Harness.ledger.verification",
                    "status": ev.get("status"),
                    "code": ev.get("code"),
                    "trace_root": result.get("trace_root"),
                }
            elif obligation.id in station_receipts:
                verdict = "PASS"
                evidence = {
                    "source": "StationReceipt",
                    "receipt_hash": station_receipts[obligation.id].get("receipt_hash"),
                    "trace_root": result.get("trace_root"),
                }
            else:
                code = unresolved.get(obligation.id, {}).get("code")
                verdict = "BLOCKED" if code == "dependency_blocked" else "UNKNOWN"
                evidence = {
                    "source": "Harness.result.unresolved",
                    "code": code,
                    "trace_root": result.get("trace_root"),
                }
            decisions.append(
                (
                    obligation.id,
                    CoreGateDecision(verdict, f"CORE-OBLIGATION:{obligation.id}", evidence),
                )
            )

        for obligation_id, decision in decisions:
            self._append_event(
                run_id,
                "module",
                "module.called",
                {
                    "module": f"obligation:{obligation_id}",
                    "call_id": f"harness:{obligation_id}",
                    "inputs_digest": digest({"task_id": task.id, "obligation_id": obligation_id}),
                    "gate_id": decision.gate_id,
                    "verdict": decision.verdict,
                    "core_evidence": decision.evidence,
                },
            )
            self._verdicts.setdefault(run_id, {})[decision.gate_id] = decision.verdict

        for obligation_id, decision in decisions:
            if decision.verdict != "PASS":
                self._append_event(
                    run_id,
                    "gate",
                    "gate.fired",
                    {
                        "gate_id": decision.gate_id,
                        "module": f"obligation:{obligation_id}",
                        "verdict": decision.verdict,
                    },
                )

        self._append_event(
            run_id,
            "core",
            "core.run.bound",
            {
                "task_id": task.id,
                "result_status": result.get("status"),
                "result_success": bool(result.get("success")),
                "trace_root": result.get("trace_root"),
                "station_receipt_count": len(station_receipts),
            },
        )
        # Terminal outcome preserves the core's distinction: a definitive
        # verifier FAIL is "error" (CORE-RUN-OUTCOME=FAIL); BLOCKED is reserved
        # for dependency-blocked or otherwise unresolved runs.
        if result.get("success"):
            outcome = "success"
        elif any(decision.verdict == "FAIL" for _, decision in decisions):
            outcome = "error"
        else:
            outcome = "aborted"
        self.on_run_complete(run_id, outcome)
        return result, self.get_attestation(run_id)

    def close(self) -> None:
        self._conn.close()


__all__ = [
    "AttestationError",
    "CoreGateDecision",
    "CoreUnreachableError",
    "GateFiredError",
    "LedgerWriteError",
    "LiveCoreResidualBackend",
    "LocalCoreTransport",
    "recompute_attestation_id",
]
