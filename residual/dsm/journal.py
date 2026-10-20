"""Durable, hash-chained, monotonic-sequence journal (DSM-R2/R3/R8/R9).

The journal is the single source of truth for accepted state transitions.
Every record is fsynced before the caller may acknowledge, carries a
monotonic ``seq`` and a hash link to its predecessor, and can be replayed
from any durable cursor for reconnect/catch-up.
"""
from __future__ import annotations

import os
from pathlib import Path

from residual.core import ContractError, canonical, digest, strict_json

GENESIS = "0" * 64


class JournalError(ContractError):
    pass


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()
        self._records = []
        self.head = GENESIS
        self.refresh()

    def _load(self):
        records = []
        previous = GENESIS
        for index, line in enumerate(self.path.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            record = strict_json(line)
            expected = record.get("hash")
            body = {k: v for k, v in record.items() if k != "hash"}
            if record["seq"] != index or record["prev_hash"] != previous or digest(body) != expected:
                raise JournalError(f"journal integrity mismatch at record {index}")
            records.append(record)
            previous = expected
        return records

    def refresh(self):
        """Reload and verify durable state from disk.

        ``DistributedStateStore`` calls this while holding its process-local
        path lock before admission/read projection.  The journal itself does
        not claim cross-process serialization; external writers still require
        a stronger lock/consensus adapter.
        """
        records = self._load()
        self._records = records
        self.head = records[-1]["hash"] if records else GENESIS
        return len(records)

    def __len__(self):
        return len(self._records)

    @property
    def cursor(self):
        """Durable cursor: the highest durably persisted sequence number."""
        return len(self._records) - 1

    def append(self, kind, payload, time_ns=0):
        """Append and fsync a record. Returns the full record.

        The record is durable on disk before this method returns; callers must
        not acknowledge a transition whose append has not returned. Callers
        sharing this path must serialize and refresh before append.
        """
        body = {
            "seq": len(self._records),
            "kind": kind,
            "time_ns": time_ns,
            "prev_hash": self.head,
            "payload": payload,
        }
        record = {**body, "hash": digest(body)}
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(canonical(record) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._records.append(record)
        self.head = record["hash"]
        return record

    def replay(self, from_seq=0):
        """Yield records with seq > from_seq for reconnect/catch-up (DSM-R3)."""
        for record in self._records:
            if record["seq"] > from_seq:
                yield record

    def verify(self):
        """Re-verify the on-disk chain from scratch."""
        return len(self._load())
