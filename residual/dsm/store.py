"""Distributed state store: admission, fencing, deterministic conflict
semantics, and crash/recovery (DSM-R1/R4/R5/R6/R8/R9).

An *event* is a proposed state transition:

    {"event_id", "domain", "entity", "value", "writer",
     "writer_holder", "fencing_token", "now_ms"   (task.lease domain only)}

Admission rules (evaluated in order, all fail closed):
  1. dedupe      — a previously journaled event_id is a duplicate (R4).
  2. ownership   — writer must be authoritative for the domain (R1).
  3. fencing     — task.lease writes need a live fencing token (R5).
  4. terminal    — task.terminal transitions must be legal; terminal
                   states are absorbing (R1/R6).

Accepted events are appended to the hash-chained journal *before* the
acknowledgement is returned. ``submit(crash_after="journal_write")``
simulates process death in exactly that window (R8).

Deduplication and projections are derived from the journal itself, never
from volatile in-memory state, so a retry after a crash — in a new process
or the same one — can never re-accept a journaled transition.

Conflict semantics (R6): every accepted event is durably ordered by its
journal seq. Concurrent conflicting values for the same (domain, entity)
are resolved by a deterministic total order — argmax of
(fencing_token, writer, event_id) — computed from the journal alone, so
live and replayed executions converge to identical projections without any
consensus protocol.
"""
from __future__ import annotations

import threading
from contextlib import nullcontext
from pathlib import Path

from residual.core import ContractError

from .journal import Journal
from .lease import LeaseManager
from .ownership import OwnershipRegistry, TERMINAL_TRANSITIONS, TERMINAL_STATES


class CrashError(RuntimeError):
    """Simulated process death at an injected crash point."""


class DistributedStateStore:
    def __init__(self, root, ownership=None, leases=None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.journal = Journal(self.root / "dsm.journal")
        self.ownership = ownership or OwnershipRegistry()
        # NOTE: lease state is intentionally injectable; durability of the
        # lease table requires a consensus service (see docs/swarm/dsm-004.md).
        self.leases = leases or LeaseManager()
        self._commit_lock = threading.RLock()

    # -- journal-derived views --------------------------------------------
    def _transition_records(self):
        return [r for r in self.journal.replay(-1) if r["kind"] == "transition"]

    def _find(self, event_id):
        for record in self._transition_records():
            if record["payload"]["event"]["event_id"] == event_id:
                return record
        return None

    @staticmethod
    def transition_key(event):
        """Global replay/idempotence key for an authoritative transition."""
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id.strip():
            raise ContractError("event_id must be a non-empty global transition key")
        return event_id

    # -- recovery ----------------------------------------------------------
    @classmethod
    def recover(cls, root, ownership=None, leases=None):
        """Rebuild a store purely from the retained journal (R8/R9)."""
        return cls(root, ownership=ownership, leases=leases)

    # -- admission ---------------------------------------------------------
    def submit(self, event, crash_after=None, time_ns=0):
        """Validate, journal, and acknowledge a proposed transition.

        Returns {"seq", "hash", "disposition"} where disposition is
        "accepted" or "duplicate". Raises a ContractError subclass on
        rejection (fail closed) and CrashError at the injected crash point.
        """
        with self._commit_lock:
            return self._submit_locked(event, crash_after=crash_after, time_ns=time_ns)

    def _submit_locked(self, event, crash_after=None, time_ns=0):
        for field in ("event_id", "domain", "entity", "value", "writer"):
            if field not in event:
                raise ContractError(f"event missing required field {field!r}")

        # 1. idempotency (R4): a retry of an already-journaled event is a
        #    duplicate, even if the first submit crashed before its ack.
        transition_key = self.transition_key(event)
        existing = self._find(transition_key)
        if existing is not None:
            if existing["payload"]["event"] != event:
                raise ContractError(
                    f"transition key collision for event_id {transition_key!r}"
                )
            return {"seq": existing["seq"], "hash": existing["hash"],
                    "disposition": "duplicate"}

        # 2. authoritative ownership (R1)
        self.ownership.check_writer(event["domain"], event["writer"])

        # 3. fencing (R5): lease-domain writes require a live fencing token
        lease_guard = nullcontext()
        if event["domain"] == "task.lease":
            lease_guard = self.leases.commit_guard(
                event["entity"], event["writer_holder"],
                event["fencing_token"], event["now_ms"])

        # 4. terminal transition legality (R1/R6)
        if event["domain"] == "task.terminal":
            current = self.current_value("task.terminal", event["entity"], default=None)
            allowed = TERMINAL_TRANSITIONS.get(current, set())
            if event["value"] not in allowed:
                raise ContractError(
                    f"illegal terminal transition {current!r} -> {event['value']!r}"
                )

        # The local fencing lock remains held through the durable append. A
        # renewal/reassignment therefore cannot race between validation and
        # the authoritative commit boundary.
        with lease_guard:
            record = self.journal.append("transition", {"event": event}, time_ns=time_ns)
        if crash_after == "journal_write":
            # Process dies after the durable write but before the ack. The
            # caller observes a crash, never an acknowledgement (R8).
            raise CrashError("process died between journal write and acknowledgement")
        return {"seq": record["seq"], "hash": record["hash"], "disposition": "accepted"}

    # -- deterministic projection (R6) -------------------------------------
    @staticmethod
    def _order_key(event):
        return (event.get("fencing_token") or 0, event["writer"], event["event_id"])

    def accepted_events(self, domain, entity):
        return [r["payload"]["event"] for r in self._transition_records()
                if r["payload"]["event"]["domain"] == domain
                and r["payload"]["event"]["entity"] == entity]

    def current_value(self, domain, entity, default=None):
        """Deterministic winner: argmax(fencing_token, writer, event_id)."""
        events = self.accepted_events(domain, entity)
        if not events:
            return default
        return max(events, key=self._order_key)["value"]

    def accepted_transitions(self):
        """All accepted transitions in journal order — the recovery proof set."""
        return [{"seq": r["seq"], "hash": r["hash"],
                 "event_id": (e := r["payload"]["event"])["event_id"],
                 "domain": e["domain"], "entity": e["entity"], "writer": e["writer"],
                 "value": e["value"], "fencing_token": e.get("fencing_token")}
                for r in self._transition_records()]

    def provenance(self, event_id):
        """Audit provenance for an accepted event: writer, fencing, hash link (R9)."""
        record = self._find(event_id)
        if record is None:
            raise ContractError(f"unknown accepted event {event_id!r}")
        return {"seq": record["seq"], "hash": record["hash"],
                "prev_hash": record["prev_hash"], "event": record["payload"]["event"]}


__all__ = ["DistributedStateStore", "CrashError", "TERMINAL_STATES", "ContractError"]
