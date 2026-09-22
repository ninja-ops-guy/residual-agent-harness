"""Durable enrollment, messaging, replay and status for the Station mesh.

MeshState owns no task-transition authority. It uses Store transactions so message
admission and the mirrored Station event commit atomically.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import asdict

from residual.core import ContractError, canonical
from .mesh import (
    EnrollmentRequest,
    MeshEnvelope,
    MAX_PAGE,
    MAX_REPLAY_AGE_S,
    STATUS_SCHEMA,
)


def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class MeshState:
    def __init__(self, store):
        self.store = store
        with store.transaction() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS mesh_workers(
                worker_id TEXT PRIMARY KEY,
                token_hash TEXT NOT NULL,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS mesh_messages(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT NOT NULL,
                sender TEXT NOT NULL,
                kind TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                digest TEXT NOT NULL,
                value TEXT NOT NULL,
                receipt_time REAL NOT NULL,
                station_event_seq INTEGER NOT NULL,
                UNIQUE(project,sender,kind,idempotency_key)
            );
            CREATE INDEX IF NOT EXISTS mesh_messages_project_seq
                ON mesh_messages(project,seq);
            CREATE TABLE IF NOT EXISTS mesh_cursors(
                worker_id TEXT NOT NULL,
                project TEXT NOT NULL,
                seq INTEGER NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY(worker_id,project)
            );
            CREATE TABLE IF NOT EXISTS mesh_dead_letters(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id TEXT,
                project TEXT,
                operation TEXT NOT NULL,
                reason TEXT NOT NULL,
                digest TEXT,
                created_at REAL NOT NULL,
                value TEXT
            );
            """)

    def _load_worker(self, c, worker_id):
        row = c.execute("SELECT value FROM mesh_workers WHERE worker_id=?", (worker_id,)).fetchone()
        if not row:
            raise ContractError("Mesh worker is not enrolled")
        return json.loads(row["value"])

    def _write_worker(self, c, worker):
        c.execute("UPDATE mesh_workers SET value=? WHERE worker_id=?",
                  (canonical(worker), worker["worker_id"]))

    def enroll(self, request, *, allowed_capabilities, actor="operator"):
        req = EnrollmentRequest.parse(request)
        allowed_capabilities = set(allowed_capabilities)
        if not set(req.capabilities).issubset(allowed_capabilities):
            raise ContractError("Enrollment requests capabilities not permitted by policy")
        token = secrets.token_urlsafe(32)
        now = time.time()
        worker = {
            "schema": "residual.sc.mesh.enrollment/1",
            **asdict(req),
            "project_ids": list(req.project_ids),
            "capabilities": list(req.capabilities),
            "topics": list(req.topics),
            "state": "ENROLLED",
            "generation_seen": {},
            "created_at": now,
            "updated_at": now,
            "revoked_at": None,
            "last_seen": None,
        }
        with self.store.transaction() as c:
            for pid in req.project_ids:
                self.store._project(c, pid)
            c.execute(
                "INSERT INTO mesh_workers(worker_id,token_hash,value) VALUES(?,?,?)",
                (req.worker_id, _hash_token(token), canonical(worker)),
            )
            for pid in req.project_ids:
                project = self.store._project(c, pid)
                self.store._event(c, project, "mesh.worker.enrolled", actor,
                                  data={"worker_id": req.worker_id, "host_id": req.host_id,
                                        "adapter": req.adapter, "adapter_version": req.adapter_version,
                                        "capabilities": list(req.capabilities)})
        return {"worker": worker, "token": token}

    def authenticate(self, token):
        if not isinstance(token, str) or not token:
            raise ContractError("Mesh enrollment token is required")
        digest = _hash_token(token)
        with self.store.connect() as c:
            row = c.execute("SELECT value FROM mesh_workers WHERE token_hash=?", (digest,)).fetchone()
        if not row:
            raise ContractError("Mesh enrollment token is invalid")
        worker = json.loads(row["value"])
        now = time.time()
        if worker["state"] == "REVOKED" or worker["expires_at"] <= now:
            raise ContractError("Mesh enrollment is revoked or expired")
        return worker

    def authorize(self, worker, project_id, *, require_ready=True):
        if project_id not in worker["project_ids"]:
            raise ContractError("Worker is not authorized for this project")
        with self.store.connect() as c:
            current = self._load_worker(c, worker["worker_id"])
            project = self.store._project(c, project_id)
        if current["state"] == "REVOKED" or current["expires_at"] <= time.time():
            raise ContractError("Mesh enrollment is revoked or expired")
        if require_ready and current["state"] != "READY":
            raise ContractError("Worker must synchronize before authority-bearing operations")
        generation = int(project.get("generation", 1))
        if require_ready and current.get("generation_seen", {}).get(project_id) != generation:
            raise ContractError("Worker generation is stale; synchronize before continuing")
        if project.get("stopped", False):
            raise ContractError("Project is stopped")
        return current, project

    def revoke(self, worker_id, *, actor="operator"):
        now = time.time()
        with self.store.transaction() as c:
            worker = self._load_worker(c, worker_id)
            if worker["state"] != "REVOKED":
                worker.update(state="REVOKED", revoked_at=now, updated_at=now)
                self._write_worker(c, worker)
                for pid in worker["project_ids"]:
                    project = self.store._project(c, pid)
                    self.store._event(c, project, "mesh.worker.revoked", actor,
                                      data={"worker_id": worker_id})
        return {"worker_id": worker_id, "state": "REVOKED"}

    def begin_sync(self, worker):
        now = time.time()
        with self.store.transaction() as c:
            current = self._load_worker(c, worker["worker_id"])
            if current["state"] == "REVOKED":
                raise ContractError("Revoked workers require explicit re-enrollment")
            current.update(state="SYNCING", last_seen=now, updated_at=now)
            self._write_worker(c, current)
            return current

    def snapshot(self, worker, project_id):
        if project_id not in worker["project_ids"]:
            raise ContractError("Worker is not authorized for this project")
        with self.store.transaction() as c:
            current = self._load_worker(c, worker["worker_id"])
            if current["state"] not in {"ENROLLED", "SYNCING", "DISCONNECTED", "READY"}:
                raise ContractError("Worker cannot synchronize from its current lifecycle state")
            project = self.store._project(c, project_id)
            generation = int(project.get("generation", 1))
            policy_revision = int(project.get("policy_revision", 1))
            rows = c.execute("SELECT value FROM tasks WHERE project=? ORDER BY rowid", (project_id,)).fetchall()
            tasks = [json.loads(r["value"]) for r in rows]
            maxrow = c.execute("SELECT COALESCE(MAX(seq),0) n FROM mesh_messages WHERE project=?", (project_id,)).fetchone()
            cursor = int(maxrow["n"])
            leases = [{
                "task_id": t["id"],
                "attempt": t["attempt"],
                "owner": t.get("owner"),
                "lease_until": t.get("lease_until", 0),
                "fencing_token": t.get("fencing_token", 0),
                "state": t["state"],
            } for t in tasks if t["state"] == "running"]
            current.setdefault("generation_seen", {})[project_id] = generation
            current.update(state="READY", last_seen=time.time(), updated_at=time.time())
            self._write_worker(c, current)
            c.execute(
                "INSERT INTO mesh_cursors(worker_id,project,seq,updated_at) VALUES(?,?,?,?) "
                "ON CONFLICT(worker_id,project) DO UPDATE SET seq=excluded.seq,updated_at=excluded.updated_at",
                (current["worker_id"], project_id, cursor, time.time()),
            )
            return {
                "schema": "residual.sc.mesh.snapshot/1",
                "project_id": project_id,
                "generation": generation,
                "policy_revision": policy_revision,
                "paused": bool(project.get("paused", False)),
                "stopped": bool(project.get("stopped", False)),
                "tasks": [{
                    "id": t["id"], "state": t["state"], "attempt": t["attempt"],
                    "depends_on": t["depends_on"], "route": t["route"],
                    "capabilities": t.get("capabilities", []),
                    "fencing_token": t.get("fencing_token", 0),
                } for t in tasks],
                "active_leases": leases,
                "cursor": cursor,
            }

    def presence(self, worker, *, project_id=None):
        now = time.time()
        with self.store.transaction() as c:
            current = self._load_worker(c, worker["worker_id"])
            if current["state"] == "REVOKED":
                raise ContractError("Worker is revoked")
            if project_id is not None and project_id not in current["project_ids"]:
                raise ContractError("Worker is not authorized for this project")
            current.update(last_seen=now, updated_at=now)
            self._write_worker(c, current)
            return {"worker_id": current["worker_id"], "state": current["state"], "last_seen": now}

    def disconnect(self, worker_id):
        now = time.time()
        with self.store.transaction() as c:
            current = self._load_worker(c, worker_id)
            if current["state"] != "REVOKED":
                current.update(state="DISCONNECTED", updated_at=now)
                self._write_worker(c, current)
            return current

    def _task_authority(self, c, worker, envelope):
        if envelope.task_id is None:
            return
        task = self.store._task(c, envelope.project_id, envelope.task_id)
        if task["state"] != "running":
            raise ContractError("Task-scoped message has no current running authority")
        if task["attempt"] != envelope.attempt:
            raise ContractError("Task-scoped message attempt is stale")
        if task.get("fencing_token", 0) != envelope.fencing_token:
            raise ContractError("Task-scoped message fencing token is stale")
        if not task.get("lease") or not secrets.compare_digest(task["lease"], envelope.lease_id):
            raise ContractError("Task-scoped message lease does not match current authority")
        if task.get("lease_until", 0) <= time.time():
            raise ContractError("Task-scoped message lease has expired")
        expected_owner = "mesh:" + worker["worker_id"]
        if task.get("owner") != expected_owner:
            raise ContractError("Task-scoped message belongs to another worker")

    def admit_message(self, worker, value):
        envelope = MeshEnvelope.parse(value)
        if envelope.sender != worker["worker_id"]:
            raise ContractError("Authenticated worker does not match envelope sender")
        if envelope.project_id not in worker["project_ids"]:
            raise ContractError("Worker is not authorized for this project")
        if worker["state"] != "READY":
            raise ContractError("Worker must synchronize before sending mesh messages")
        digest = hashlib.sha256(canonical(envelope.to_dict()).encode("utf-8")).hexdigest()
        now = time.time()
        with self.store.transaction() as c:
            project = self.store._project(c, envelope.project_id)
            if bool(project.get("stopped", False)):
                raise ContractError("Project is stopped")
            generation = int(project.get("generation", 1))
            if envelope.generation != generation:
                raise ContractError("Mesh envelope generation is stale")
            self._task_authority(c, worker, envelope)
            previous = c.execute(
                "SELECT digest,value,receipt_time,station_event_seq,seq FROM mesh_messages "
                "WHERE project=? AND sender=? AND kind=? AND idempotency_key=?",
                (envelope.project_id, envelope.sender, envelope.kind, envelope.idempotency_key),
            ).fetchone()
            if previous:
                if previous["digest"] != digest:
                    raise ContractError("Mesh idempotency key conflicts with a different payload")
                return {
                    "seq": previous["seq"],
                    "station_event_seq": previous["station_event_seq"],
                    "receipt_time": previous["receipt_time"],
                    "digest": previous["digest"],
                    "duplicate": True,
                }
            event = self.store._event(
                c, project, "mesh.message", "mesh:" + worker["worker_id"],
                self.store._task(c, envelope.project_id, envelope.task_id) if envelope.task_id else None,
                {"message_id": envelope.message_id, "kind": envelope.kind,
                 "recipient": envelope.recipient, "payload_digest": envelope.payload_digest,
                 "generation": envelope.generation, "idempotency_key": envelope.idempotency_key},
            )
            cur = c.execute(
                "INSERT INTO mesh_messages(project,sender,kind,idempotency_key,digest,value,receipt_time,station_event_seq) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (envelope.project_id, envelope.sender, envelope.kind, envelope.idempotency_key,
                 digest, canonical(envelope.to_dict()), now, event["seq"]),
            )
            return {
                "seq": cur.lastrowid,
                "station_event_seq": event["seq"],
                "receipt_time": now,
                "digest": digest,
                "duplicate": False,
            }

    def receipt(self, worker, project_id, idempotency_key, *, kind=None):
        if project_id not in worker["project_ids"]:
            raise ContractError("Worker is not authorized for this project")
        with self.store.connect() as c:
            if kind:
                row = c.execute(
                    "SELECT * FROM mesh_messages WHERE project=? AND sender=? AND kind=? AND idempotency_key=?",
                    (project_id, worker["worker_id"], kind, idempotency_key),
                ).fetchone()
            else:
                rows = c.execute(
                    "SELECT * FROM mesh_messages WHERE project=? AND sender=? AND idempotency_key=?",
                    (project_id, worker["worker_id"], idempotency_key),
                ).fetchall()
                if len(rows) > 1:
                    raise ContractError("Operation kind is required for an ambiguous idempotency key")
                row = rows[0] if rows else None
        if not row:
            return None
        return {"seq": row["seq"], "station_event_seq": row["station_event_seq"],
                "receipt_time": row["receipt_time"], "digest": row["digest"]}

    def messages(self, worker, project_id, *, after=0, limit=100):
        if project_id not in worker["project_ids"]:
            raise ContractError("Worker is not authorized for this project")
        if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= MAX_PAGE:
            raise ContractError("Invalid mesh replay cursor/page")
        with self.store.connect() as c:
            rows = c.execute(
                "SELECT seq,value,receipt_time,station_event_seq FROM mesh_messages "
                "WHERE project=? AND seq>? ORDER BY seq LIMIT ?",
                (project_id, after, limit + 1),
            ).fetchall()
        visible = []
        topics = set(worker["topics"])
        now = time.time()
        for row in rows[:limit]:
            envelope = json.loads(row["value"])
            recipient = envelope["recipient"]
            if recipient not in {"all", worker["worker_id"]}:
                if not recipient.startswith("topic:") or recipient[6:] not in topics:
                    continue
            if envelope["expires_at"] < now - MAX_REPLAY_AGE_S:
                continue
            visible.append({
                "seq": row["seq"], "receipt_time": row["receipt_time"],
                "station_event_seq": row["station_event_seq"], "envelope": envelope,
            })
        return {"messages": visible, "has_more": len(rows) > limit,
                "next_cursor": rows[min(len(rows), limit) - 1]["seq"] if rows else after}

    def acknowledge(self, worker, project_id, seq):
        if project_id not in worker["project_ids"]:
            raise ContractError("Worker is not authorized for this project")
        if type(seq) is not int or seq < 0:
            raise ContractError("Invalid mesh cursor")
        with self.store.transaction() as c:
            maxrow = c.execute("SELECT COALESCE(MAX(seq),0) n FROM mesh_messages WHERE project=?", (project_id,)).fetchone()
            if seq > maxrow["n"]:
                raise ContractError("Cannot acknowledge beyond the durable mesh head")
            c.execute(
                "INSERT INTO mesh_cursors(worker_id,project,seq,updated_at) VALUES(?,?,?,?) "
                "ON CONFLICT(worker_id,project) DO UPDATE SET seq=max(seq,excluded.seq),updated_at=excluded.updated_at",
                (worker["worker_id"], project_id, seq, time.time()),
            )
        return {"project_id": project_id, "cursor": seq}

    def dead_letter(self, *, worker_id, project_id, operation, reason, value=None):
        digest = hashlib.sha256(canonical(value).encode()).hexdigest() if value is not None else None
        with self.store.transaction() as c:
            cur = c.execute(
                "INSERT INTO mesh_dead_letters(worker_id,project,operation,reason,digest,created_at,value) "
                "VALUES(?,?,?,?,?,?,?)",
                (worker_id, project_id, operation, reason[:300], digest, time.time(),
                 canonical(value) if value is not None else None),
            )
        return {"id": cur.lastrowid, "digest": digest}

    def status(self):
        now = time.time()
        with self.store.connect() as c:
            workers = [json.loads(r["value"]) for r in c.execute("SELECT value FROM mesh_workers ORDER BY worker_id")]
            messages = c.execute("SELECT count(*) n, COALESCE(min(receipt_time),0) oldest FROM mesh_messages").fetchone()
            dead = c.execute("SELECT count(*) n FROM mesh_dead_letters").fetchone()["n"]
            cursors = [dict(r) for r in c.execute("SELECT worker_id,project,seq,updated_at FROM mesh_cursors ORDER BY worker_id,project")]
        return {
            "schema": STATUS_SCHEMA,
            "at": now,
            "workers": [{
                "worker_id": w["worker_id"], "host_id": w["host_id"], "adapter": w["adapter"],
                "adapter_version": w["adapter_version"], "state": w["state"],
                "project_count": len(w["project_ids"]), "capabilities": w["capabilities"],
                "last_seen": w["last_seen"], "expires_at": w["expires_at"],
            } for w in workers],
            "message_count": messages["n"],
            "oldest_message_age_s": max(0, now - messages["oldest"]) if messages["n"] else 0,
            "dead_letter_count": dead,
            "cursors": cursors,
            "qualification": "health_only_not_mesh_qualification",
        }
