"""MC-V1-001: durable conversation projections of Station-owned tasks.

No method in this module writes projects/tasks, claims work, renews a worker
lease, runs tools, or accepts evidence. Bindings are narrow capabilities minted
by the operator API, not agent identities inferred from message text.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import math
import re
import secrets
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Iterator

SCHEMA = "residual.mission-sync.v1"
MAX_TEXT = 8_000
MAX_PENDING = 256
MAX_PAYLOAD = 48_000
KINDS = frozenset({"message", "progress", "blocked", "completion_claim", "artifact_reference"})
ROUTES = frozenset({"inbound", "outbound", "bidirectional"})


class SyncError(ValueError):
    """A bounded, safe-to-display protocol rejection."""


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def text(value: Any, name: str, limit: int = 200, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()) or len(value) > limit:
        raise SyncError(f"Invalid {name}")
    if any(ord(ch) < 32 and ch not in "\n\t\r" for ch in value):
        raise SyncError(f"Invalid control character in {name}")
    return value


def integer(value: Any, name: str, minimum: int = 0, maximum: int = 2**53 - 1) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise SyncError(f"Invalid {name}")
    return value


def strict_json(raw: str | bytes) -> dict:
    if len(raw) > MAX_PAYLOAD:
        raise SyncError("Payload too large")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise SyncError("Duplicate JSON key")
            result[key] = value
        return result
    def constant(_):
        raise SyncError("Nonfinite JSON number")
    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
        if not isinstance(result, dict):
            raise SyncError("Expected a JSON object")
        if len(canonical(result)) > MAX_PAYLOAD:
            raise SyncError("Payload too large")
        return result
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise SyncError("Invalid or unbounded JSON") from exc


def exact(value: dict, required: set[str], optional: set[str] = frozenset()) -> None:
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - optional:
        raise SyncError("Missing or unknown fields")


class MissionSync:
    """Namespaced tables in the existing Station SQLite database.

    The host process and database owner are trusted. Hash chains detect changes
    relative to a retained checkpoint; they are not signatures or proof against
    an administrator rewriting the entire database.
    """

    def __init__(self, db: str | Path, *, clock=time.time):
        self.db = str(Path(db).resolve())
        self.clock = clock
        if not Path(self.db).is_file():
            raise SyncError("Initialize Station before mission sync")
        with self.connect() as c:
            names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"projects", "tasks"} <= names:
                raise SyncError("Not a Station database")
            c.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS ms_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS ms_bindings(
                    id TEXT PRIMARY KEY, project TEXT NOT NULL, task TEXT NOT NULL,
                    token_hash TEXT NOT NULL, value TEXT NOT NULL, inbound_seq INTEGER NOT NULL DEFAULT 0,
                    revoked INTEGER NOT NULL DEFAULT 0, snapshot_hash TEXT,
                    UNIQUE(project,task,id), FOREIGN KEY(project,task) REFERENCES tasks(project,id));
                CREATE TABLE IF NOT EXISTS ms_journal(
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
                    project TEXT NOT NULL, value TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS ms_journal_project ON ms_journal(project,seq);
                CREATE TABLE IF NOT EXISTS ms_reports(
                    binding TEXT NOT NULL, event_id TEXT NOT NULL, source_seq INTEGER NOT NULL,
                    fingerprint TEXT NOT NULL, receipt TEXT NOT NULL, value TEXT NOT NULL,
                    PRIMARY KEY(binding,event_id), UNIQUE(binding,source_seq));
                CREATE TABLE IF NOT EXISTS ms_outbox(
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
                    binding TEXT NOT NULL, value TEXT NOT NULL, hash TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'pending');
                CREATE INDEX IF NOT EXISTS ms_outbox_delivery ON ms_outbox(binding,state,seq);
            """)
            c.execute("INSERT OR IGNORE INTO ms_meta VALUES('schema',?)", (SCHEMA,))
            if c.execute("SELECT value FROM ms_meta WHERE key='schema'").fetchone()[0] != SCHEMA:
                raise SyncError("Unsupported mission-sync database version")

    @contextlib.contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        c = sqlite3.connect(self.db, timeout=15)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA synchronous=FULL")
        try:
            with c:
                yield c
        finally:
            c.close()

    @contextlib.contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            yield c

    def _now(self, c) -> int:
        value = self.clock()
        if type(value) not in (int, float) or not math.isfinite(value):
            raise SyncError("Invalid clock")
        prior = c.execute("SELECT value FROM ms_meta WHERE key='clock_high_water'").fetchone()
        if prior and value < float(prior[0]):
            raise SyncError("Clock rollback: operator investigation required")
        c.execute("INSERT OR REPLACE INTO ms_meta VALUES('clock_high_water',?)", (str(value),))
        return int(value * 1000)

    @staticmethod
    def _source(c, project: str, task: str) -> tuple[dict, dict]:
        p = c.execute("SELECT value FROM projects WHERE id=?", (project,)).fetchone()
        t = c.execute("SELECT value FROM tasks WHERE project=? AND id=?", (project, task)).fetchone()
        if not p or not t:
            raise SyncError("Mission or task not found")
        return json.loads(p[0]), json.loads(t[0])

    def _journal(self, c, project: str, kind: str, data: dict, now: float) -> dict:
        previous = c.execute("SELECT hash FROM ms_journal WHERE project=? ORDER BY seq DESC LIMIT 1", (project,)).fetchone()
        previous = previous[0] if previous else "0" * 64
        event = {"schema": SCHEMA, "id": uuid.uuid4().hex, "mission_id": project,
                 "kind": kind, "recorded_at": now, "data": data}
        root = digest({"previous": previous, "event": event})
        cursor = c.execute("INSERT INTO ms_journal(id,project,value,prev_hash,hash) VALUES(?,?,?,?,?)",
                           (event["id"], project, canonical(event), previous, root))
        return {"event_id": event["id"], "journal_seq": cursor.lastrowid, "hash": root, "prev_hash": previous}

    @staticmethod
    def _public_binding(row) -> dict:
        return {**json.loads(row["value"]), "revoked": bool(row["revoked"]), "last_source_seq": row["inbound_seq"]}

    def bind(self, definition: dict) -> dict:
        """Operator-only API. Return the scoped token once; never journal it."""
        exact(definition, {"mission_id", "task_id", "harness", "instance_id", "conversation_id", "agent_id"},
              {"direction", "share_messages", "ttl_seconds"})
        for name in ("mission_id", "task_id", "instance_id", "conversation_id", "agent_id"):
            text(definition[name], name)
        harness = text(definition["harness"], "harness", 60)
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", harness):
            raise SyncError("Invalid harness slug")
        direction = definition.get("direction", "bidirectional")
        if direction not in ROUTES:
            raise SyncError("Invalid direction")
        share = definition.get("share_messages", False)
        if type(share) is not bool:
            raise SyncError("share_messages must be boolean")
        ttl = integer(definition.get("ttl_seconds", 86_400), "ttl_seconds", 60, 604_800)
        with self.transaction() as c:
            now = self._now(c)
            p, t = self._source(c, definition["mission_id"], definition["task_id"])
            bid, token = uuid.uuid4().hex, secrets.token_urlsafe(32)
            value = {**{k: definition[k] for k in ("mission_id", "task_id", "harness", "instance_id", "conversation_id", "agent_id")},
                     "binding_id": bid, "schema": SCHEMA, "direction": direction,
                     "share_messages": share, "attempt": t["attempt"], "spec_hash": p["spec_hash"],
                     "created_at": now, "expires_at": now + ttl * 1000}
            c.execute("INSERT INTO ms_bindings(id,project,task,token_hash,value) VALUES(?,?,?,?,?)",
                      (bid, p["id"], t["id"], hashlib.sha256(token.encode()).hexdigest(), canonical(value)))
            self._journal(c, p["id"], "binding.created", value, now)
            return {"binding": value, "token": token}

    def revoke(self, binding_id: str) -> dict:
        with self.transaction() as c:
            now = self._now(c)
            row = c.execute("SELECT * FROM ms_bindings WHERE id=?", (binding_id,)).fetchone()
            if not row:
                raise SyncError("Binding not found")
            if not row["revoked"]:
                c.execute("UPDATE ms_bindings SET revoked=1 WHERE id=?", (binding_id,))
                # Retain undelivered records but no longer expose them to the revoked capability.
                self._journal(c, row["project"], "binding.revoked", {"binding_id": binding_id}, now)
            return {"revoked": True}

    def _auth(self, c, bid: str, token: str, now: float):
        text(bid, "binding_id", 64)
        text(token, "token", 128)
        row = c.execute("SELECT * FROM ms_bindings WHERE id=?", (bid,)).fetchone()
        supplied = hashlib.sha256(token.encode()).hexdigest()
        if not row or not secrets.compare_digest(row["token_hash"], supplied):
            raise PermissionError("Invalid mission binding capability")
        b = json.loads(row["value"])
        if row["revoked"] or now >= b["expires_at"]:
            raise PermissionError("Mission binding expired or revoked")
        p, t = self._source(c, row["project"], row["task"])
        if t["attempt"] != b["attempt"] or p["spec_hash"] != b["spec_hash"]:
            raise SyncError("Stale binding: operator must bind the current attempt/spec")
        return row, b, p, t

    @staticmethod
    def _projection(p: dict, t: dict, *, include_instruction: bool = False) -> dict:
        # Never serialize arbitrary source fields, leases, paths, settings or raw artifacts.
        task = {k: t.get(k) for k in ("id", "title", "state", "attempt", "owner", "depends_on", "base_commit", "head_commit")}
        if include_instruction:
            task["instruction"] = t.get("instruction", "")
        return {"mission": {"id": p["id"], "name": p.get("name", ""), "goal": p.get("goal", ""),
                            "spec_hash": p["spec_hash"], "paused": bool(p.get("paused", False))},
                "task": task, "state_source": "station", "acceptance_authority": "station_only",
                "conversation_reports_are": "untrusted_observations", "native_cancellation_proven": False}

    def _enqueue(self, c, bid: str, kind: str, data: dict, now: float) -> dict:
        pending = c.execute("SELECT count(*) FROM ms_outbox WHERE binding=? AND state!='acked'", (bid,)).fetchone()[0]
        if pending >= MAX_PENDING:
            raise SyncError("Delivery backlog full: drain or revoke the binding; nothing acknowledged")
        did = uuid.uuid4().hex
        payload = {"schema": SCHEMA, "delivery_id": did, "kind": kind, "recorded_at": now, "data": data}
        raw = canonical(payload)
        if len(raw) > 40_000:
            raise SyncError("Projection exceeds payload limit")
        c.execute("INSERT INTO ms_outbox(id,binding,value,hash) VALUES(?,?,?,?)", (did, bid, raw, digest(payload)))
        return payload

    def _refresh(self, c, row, p: dict, t: dict, now: float) -> bool:
        projection = self._projection(p, t, include_instruction=True)
        fingerprint = digest(projection)
        if row["snapshot_hash"] != fingerprint:
            if c.execute("SELECT count(*) FROM ms_outbox WHERE binding=? AND state!='acked'", (row["id"],)).fetchone()[0] >= MAX_PENDING:
                return False  # Existing deliveries must remain drainable under backpressure.
            self._enqueue(c, row["id"], "station.snapshot", projection, now)
            c.execute("UPDATE ms_bindings SET snapshot_hash=? WHERE id=?", (fingerprint, row["id"]))
        return True

    @staticmethod
    def _report(report: dict) -> dict:
        exact(report, {"schema", "event_id", "source_seq", "kind", "text"}, {"references", "echo_delivery_id"})
        if report["schema"] != SCHEMA or report["kind"] not in KINDS:
            raise SyncError("Unsupported report schema or kind")
        text(report["event_id"], "event_id", 128)
        integer(report["source_seq"], "source_seq", 1)
        text(report["text"], "report text", MAX_TEXT, empty=True)
        refs = report.get("references", [])
        if not isinstance(refs, list) or len(refs) > 16:
            raise SyncError("Invalid artifact references")
        for ref in refs:
            exact(ref, {"label", "sha256"})
            text(ref["label"], "reference label", 200)
            if not isinstance(ref["sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", ref["sha256"]):
                raise SyncError("Invalid reference hash")
        if "echo_delivery_id" in report:
            text(report["echo_delivery_id"], "echo_delivery_id", 64)
        # Sever caller-owned mutable references before any durable operation.
        return strict_json(canonical(report))

    def ingest(self, binding_id: str, token: str, report: dict) -> dict:
        report = self._report(report)
        fingerprint = digest(report)
        with self.transaction() as c:
            now = self._now(c)
            row, b, p, t = self._auth(c, binding_id, token, now)
            if b["direction"] == "outbound":
                raise PermissionError("Binding does not allow inbound reports")
            previous = c.execute("SELECT * FROM ms_reports WHERE binding=? AND event_id=?", (binding_id, report["event_id"])).fetchone()
            if previous:
                if previous["fingerprint"] != fingerprint:
                    raise SyncError("Event ID reused with different content")
                return json.loads(previous["receipt"])
            if report["source_seq"] != row["inbound_seq"] + 1:
                raise SyncError("Source sequence gap or replay: send the next durable event")
            echo = report.get("echo_delivery_id")
            if echo:
                delivered = c.execute("SELECT state FROM ms_outbox WHERE id=? AND binding=?", (echo, binding_id)).fetchone()
                if not delivered or delivered[0] == "pending":
                    raise SyncError("Unknown or unoffered echo delivery")
            observed = {"binding_id": binding_id, "harness": b["harness"], "instance_id": b["instance_id"],
                        "conversation_id": b["conversation_id"], "agent_id": b["agent_id"],
                        "task_id": t["id"], "attempt": t["attempt"], "spec_hash": p["spec_hash"],
                        "report": report, "trust": "untrusted", "authorizes_acceptance": False}
            journal = self._journal(c, p["id"], "conversation.report", observed, now)
            receipt = {"schema": SCHEMA, "recorded": True, "event_id": report["event_id"],
                       "source_seq": report["source_seq"], "fingerprint": fingerprint, "journal": journal,
                       "task_state": t["state"], "authorizes_acceptance": False,
                       "echo_suppressed": bool(echo)}
            c.execute("INSERT INTO ms_reports VALUES(?,?,?,?,?,?)", (binding_id, report["event_id"], report["source_seq"],
                      fingerprint, canonical(receipt), canonical(observed)))
            c.execute("UPDATE ms_bindings SET inbound_seq=? WHERE id=?", (report["source_seq"], binding_id))
            # Explicit source AND destination sharing consent. No implicit transcript broadcast.
            if b["share_messages"] and not echo:
                for dest in c.execute("SELECT * FROM ms_bindings WHERE project=? AND task=? AND id!=? AND revoked=0",
                                      (p["id"], t["id"], binding_id)).fetchall():
                    target = json.loads(dest["value"])
                    if (target["share_messages"] and target["direction"] != "inbound" and
                        target["attempt"] == t["attempt"] and target["spec_hash"] == p["spec_hash"] and now < target["expires_at"]):
                        self._enqueue(c, dest["id"], "conversation.observation", observed, now)
            return receipt

    def poll(self, binding_id: str, token: str, *, limit: int = 25) -> dict:
        integer(limit, "limit", 1, 100)
        with self.transaction() as c:
            now = self._now(c)
            row, b, p, t = self._auth(c, binding_id, token, now)
            if b["direction"] == "inbound":
                raise PermissionError("Binding does not allow outbound delivery")
            current_snapshot_queued = self._refresh(c, row, p, t, now)
            rows = c.execute("SELECT * FROM ms_outbox WHERE binding=? AND state!='acked' ORDER BY seq LIMIT ?", (binding_id, limit)).fetchall()
            for item in rows:
                c.execute("UPDATE ms_outbox SET state='offered' WHERE id=?", (item["id"],))
            return {"schema": SCHEMA, "binding_id": binding_id,
                    "deliveries": [{"payload": json.loads(r["value"]), "sha256": r["hash"]} for r in rows],
                    "delivery_semantics": "at_least_once", "last_source_seq": row["inbound_seq"],
                    "current_snapshot_queued": current_snapshot_queued}

    def acknowledge(self, binding_id: str, token: str, delivery_id: str, sha256: str) -> dict:
        text(delivery_id, "delivery_id", 64)
        text(sha256, "sha256", 64)
        with self.transaction() as c:
            now = self._now(c)
            _, b, p, _ = self._auth(c, binding_id, token, now)
            if b["direction"] == "inbound":
                raise PermissionError("Binding does not allow acknowledgements")
            row = c.execute("SELECT * FROM ms_outbox WHERE binding=? AND id=?", (binding_id, delivery_id)).fetchone()
            if not row or row["state"] == "pending" or not secrets.compare_digest(row["hash"], sha256):
                raise SyncError("Unknown, unoffered, or mismatched delivery")
            if row["state"] != "acked":
                c.execute("UPDATE ms_outbox SET state='acked' WHERE id=?", (delivery_id,))
                self._journal(c, p["id"], "delivery.acknowledged", {"binding_id": binding_id, "delivery_id": delivery_id,
                              "meaning": "adapter_durably_received_not_human_read_or_native_execution"}, now)
            return {"acknowledged": True, "delivery_id": delivery_id}

    def continuation(self, binding_id: str, token: str) -> dict:
        """Current task context, not instructions to execute or resume a lease."""
        with self.transaction() as c:
            now = self._now(c)
            _, b, p, t = self._auth(c, binding_id, token, now)
            if b["direction"] == "inbound":
                raise PermissionError("Binding does not allow context reads")
            packet = self._projection(p, t, include_instruction=True)
            packet.update(binding_id=binding_id, conversation_id=b["conversation_id"],
                          required_action="Obtain work through the existing Station worker API; this packet grants no lease.")
            return {"packet": packet, "sha256": digest(packet)}

    def overview(self) -> dict:
        """Operator-only task/agent view. Never return tokens or raw task dictionaries."""
        with self.transaction() as c:
            now = self._now(c)
            missions = []
            for pr in c.execute("SELECT id,value FROM projects ORDER BY rowid DESC").fetchall():
                p = json.loads(pr["value"])
                tasks = []
                for tr in c.execute("SELECT value FROM tasks WHERE project=? ORDER BY rowid", (pr["id"],)).fetchall():
                    t = json.loads(tr[0])
                    bindings = []
                    for row in c.execute("SELECT * FROM ms_bindings WHERE project=? AND task=?", (pr["id"], t["id"])).fetchall():
                        b = self._public_binding(row)
                        b["sync_state"] = ("REVOKED" if b["revoked"] else "EXPIRED" if now >= b["expires_at"] else
                                           "STALE" if b["attempt"] != t["attempt"] or b["spec_hash"] != p["spec_hash"] else "BOUND")
                        b["pending_deliveries"] = c.execute("SELECT count(*) FROM ms_outbox WHERE binding=? AND state!='acked'", (row["id"],)).fetchone()[0]
                        latest = c.execute("SELECT value,receipt FROM ms_reports WHERE binding=? ORDER BY source_seq DESC LIMIT 1", (row["id"],)).fetchone()
                        b["latest_report"] = json.loads(latest["value"]) if latest else None
                        bindings.append(b)
                    tasks.append({**self._projection(p, t)["task"], "conversations": bindings})
                missions.append({"id": p["id"], "name": p.get("name", ""), "goal": p.get("goal", ""),
                                 "spec_hash": p["spec_hash"], "paused": p.get("paused", False), "tasks": tasks})
            return {"schema": SCHEMA, "missions": missions, "acceptance_authority": "station_only"}

    def journal(self, mission_id: str, after: int = 0, limit: int = 100) -> dict:
        integer(after, "after")
        integer(limit, "limit", 1, 500)
        with self.connect() as c:
            if not c.execute("SELECT 1 FROM projects WHERE id=?", (mission_id,)).fetchone():
                raise SyncError("Mission not found")
            rows = c.execute("SELECT * FROM ms_journal WHERE project=? AND seq>? ORDER BY seq LIMIT ?", (mission_id, after, limit)).fetchall()
            return {"events": [{"seq": r["seq"], "event": json.loads(r["value"]), "prev_hash": r["prev_hash"], "hash": r["hash"]} for r in rows],
                    "next_after": rows[-1]["seq"] if rows else after}
