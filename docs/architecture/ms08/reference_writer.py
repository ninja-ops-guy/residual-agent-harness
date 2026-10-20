"""Minimal in-process reference implementation of the MS-08 writer service.

DESIGN SKELETON ONLY (Swarm G) — binds the contract in docs/architecture/
MS-08-writer-service.md. Not a production store. Stdlib-only, in-memory ledger
with a hash-chained journal so the contract tests can prove:

  * commit-before-ack (ack only after COMMIT returns)
  * idempotent retry (crash between write and ack resolves as duplicate)
  * stale-fencing rejection (durable, monotonic fencing tokens)
  * takeover / reconciliation gating
  * outbox redelivery dedupe and emergency-journal drain

Single-host scope; multi-host is explicitly unsupported.
"""

from __future__ import annotations

import hashlib
import json
import threading


class FencingError(Exception):
    """Stale or foreign fencing token presented to the writer."""


class LeaseUnavailableError(Exception):
    """Lease/fencing state unreadable -> fenced-off recovery epoch (FENCING_UNAVAILABLE)."""


class WriterUnavailableError(Exception):
    """Writer has no valid lease (e.g. scheduler unavailable) and cannot accept proposals."""


class Rejected(Exception):
    """Validation/CAS/legality rejection; carries a typed reason."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class CrashInjected(Exception):
    """Test hook: simulated process crash at a marked point."""


def _hash(prev_hash: str, event_id: str, payload: dict) -> str:
    body = json.dumps({"prev": prev_hash, "event_id": event_id, "payload": payload},
                      sort_keys=True).encode()
    return "sha256:" + hashlib.sha256(body).hexdigest()


class InProcessLedger:
    """Stand-in for the shared authoritative control store (single host)."""

    def __init__(self):
        self.journal = []            # accepted events, seq order
        self.by_event_id = {}        # idempotency index
        self.state = {}              # key -> (value, generation)
        self.highest_token = 0       # durable fencing token (never resets)
        self.lease_holder = None
        self.lock = threading.RLock()

    @property
    def head_hash(self) -> str:
        return self.journal[-1]["hash"] if self.journal else "sha256:genesis"


class WriterService:
    """The dedicated MS-08 writer. Holds the lease; only writer of the ledger."""

    def __init__(self, ledger: InProcessLedger, writer_id: str):
        self.ledger = ledger
        self.writer_id = writer_id
        self.token = None            # fencing token, None until lease held
        self.crash_after_commit = False  # test hook: crash between COMMIT and ack
        self.reconciled = False

    # -- lease -----------------------------------------------------------

    def acquire_lease(self, now_ms: int = 0) -> int:
        with self.ledger.lock:
            # claim CAS: durable token is strictly monotonic, survives restart
            self.ledger.highest_token += 1
            self.token = self.ledger.highest_token
            self.ledger.lease_holder = self.writer_id
            return self.token

    def renew_lease(self, now_ms: int = 0) -> int:
        self._require_holder()
        with self.ledger.lock:
            # SF-04: renewal bumps the token, invalidating pre-renew in-flight writes
            self.ledger.highest_token += 1
            self.token = self.ledger.highest_token
            return self.token

    def _require_holder(self):
        if self.token is None or self.ledger.lease_holder != self.writer_id:
            raise WriterUnavailableError("no valid writer lease")

    # -- startup reconciliation gate -------------------------------------

    def reconcile(self):
        """Must run before accepting proposals after (re)acquiring the lease."""
        self._require_holder()
        with self.ledger.lock:
            # Step 0 (hash chain verify) is trivially true for the in-memory ledger;
            # Steps 2-5 rebuild/classify; Step 6 appends the checkpoint event.
            self._append("control.reconciled", {"writer": self.writer_id})
            self.reconciled = True

    # -- propose: the normative pipeline ---------------------------------

    def propose(self, event_id: str, key: str, value, expected_generation=None,
                fencing_token=None) -> dict:
        token = self.token if fencing_token is None else fencing_token
        with self.ledger.lock:
            # fencing first (§4.3): a stale token is rejected as stale_fencing
            # even when the stale writer has also lost the lease
            if token is not None and token < self.ledger.highest_token:
                raise FencingError(
                    f"stale fencing token {token}; current: {self.ledger.highest_token}")
        self._require_holder()
        if not self.reconciled:
            raise WriterUnavailableError("reconciliation required before proposals")
        with self.ledger.lock:
            # 1. validate (schema stand-in)
            if not event_id or not isinstance(event_id, str):
                raise Rejected("schema")
            # 2. dedupe
            prior = self.ledger.by_event_id.get(event_id)
            if prior is not None:
                return {"seq": prior["seq"], "hash": prior["hash"],
                        "disposition": "duplicate", "fencing_token": self.token,
                        "reason": None}
            # CAS precondition
            current = self.ledger.state.get(key)
            cur_gen = current[1] if current else 0
            if expected_generation is not None and expected_generation != cur_gen:
                raise Rejected("cas_conflict")
            # 3. write: state CAS + event append in one transaction (atomic here)
            event = self._append("mutation", {"key": key, "value": value},
                                 event_id=event_id)
            self.ledger.state[key] = (value, cur_gen + 1)
        # 4. commit-before-ack: COMMIT returned above; only now may we ack.
        if self.crash_after_commit:
            raise CrashInjected("crash between COMMIT and ack")
        return {"seq": event["seq"], "hash": event["hash"],
                "disposition": "accepted", "fencing_token": self.token,
                "reason": None}

    def _append(self, kind: str, payload: dict, event_id: str = None) -> dict:
        eid = event_id or f"auto-{len(self.ledger.journal) + 1}"
        rec = {"seq": len(self.ledger.journal) + 1, "event_id": eid, "kind": kind,
               "payload": payload,
               "hash": _hash(self.ledger.head_hash, eid, {"kind": kind, **payload})}
        self.ledger.journal.append(rec)
        self.ledger.by_event_id[eid] = rec
        return rec

    # -- outbox / drain ----------------------------------------------------

    def outbox_since(self, seq: int):
        """At-least-once replay of committed events for shards/consumers."""
        return [r for r in self.ledger.journal if r["seq"] > seq]

    def drain(self, events):
        """Drain a local emergency journal; each event dedupes by event_id."""
        return [self.propose(e["event_id"], e["key"], e["value"]) for e in events]


class EmergencyJournal:
    """Local append-only buffer used while the writer is unavailable."""

    def __init__(self):
        self.events = []

    def append(self, event_id: str, key: str, value):
        self.events.append({"event_id": event_id, "key": key, "value": value})
