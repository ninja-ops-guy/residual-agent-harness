"""Durable acknowledgement + idempotent delivery (DSM-R2/R3/R4).

Outbox: a message is not considered delivered until its ack is durably
persisted. Unacked messages are replayed on reconnect, giving
at-least-once delivery. Inbox: duplicate deliveries are deduplicated by
``event_id`` against a durable dedupe log, making delivery idempotent.
Catch-up uses the journal's monotonic sequence cursor.
"""
from __future__ import annotations

from .journal import Journal


class AckLog:
    """Durable set of acknowledged event ids, persisted in its own journal."""

    def __init__(self, path):
        self.journal = Journal(path)
        self._acked = {r["payload"]["event_id"] for r in self.journal.replay(-1)}

    def is_acked(self, event_id):
        return event_id in self._acked

    def ack(self, event_id, time_ns=0):
        if event_id in self._acked:
            return False
        self.journal.append("ack", {"event_id": event_id}, time_ns=time_ns)
        self._acked.add(event_id)
        return True

    def __len__(self):
        return len(self._acked)


class Outbox:
    """Publisher side of durable-ack delivery (DSM-R2)."""

    def __init__(self, path):
        self.journal = Journal(path)
        self.acks = AckLog(path.with_name(path.stem + ".acks"))
        self._sent = {r["payload"]["event"]["event_id"]: r["payload"]["event"]
                      for r in self.journal.replay(-1) if r["kind"] == "send"}

    def publish(self, event, time_ns=0):
        """Durably record intent to deliver; idempotent by event_id."""
        eid = event["event_id"]
        if eid not in self._sent:
            self.journal.append("send", {"event": event}, time_ns=time_ns)
            self._sent[eid] = event
        return eid

    def pending(self):
        """Events sent but not yet durably acked — replayed on reconnect (R3)."""
        return [event for eid, event in sorted(self._sent.items())
                if not self.acks.is_acked(eid)]

    def ack(self, event_id, time_ns=0):
        return self.acks.ack(event_id, time_ns=time_ns)


class Inbox:
    """Receiver side: duplicate delivery is idempotent (DSM-R4)."""

    def __init__(self, path):
        self.journal = Journal(path)
        self._seen = {}
        for r in self.journal.replay(-1):
            if r["kind"] == "deliver":
                self._seen[r["payload"]["event"]["event_id"]] = r["payload"]["disposition"]

    def deliver(self, event, time_ns=0):
        """Returns 'accepted' exactly once per event_id; 'duplicate' after."""
        eid = event["event_id"]
        if eid in self._seen:
            return "duplicate"
        self.journal.append("deliver", {"event": event, "disposition": "accepted"},
                            time_ns=time_ns)
        self._seen[eid] = "accepted"
        return "accepted"

    def seen(self, event_id):
        return event_id in self._seen
