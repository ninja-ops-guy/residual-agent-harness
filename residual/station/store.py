"""Transactional LDD event admission, task leases, projections and evidence."""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
import secrets
import sqlite3
import threading
import time
import uuid
from pathlib import Path

from residual.core import ContractError, canonical
from .contracts import TRANSITIONS, event_validate, sha
from .observability import ObservationStore


MAX_TASK_ATTEMPTS = 5


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


class Store(ObservationStore):
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            self.root.chmod(0o700)
        except OSError:
            pass
        self.db = self.root / "station.sqlite3"
        self.lock = threading.RLock()
        with self.connect() as c:
            c.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS tasks(project TEXT, id TEXT, value TEXT NOT NULL, PRIMARY KEY(project,id));
            CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE,
                project TEXT, value TEXT, prev_hash TEXT, hash TEXT);
            CREATE INDEX IF NOT EXISTS event_project ON events(project,seq);
            CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY, project TEXT, name TEXT, size INTEGER, kind TEXT);
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS settings(id TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS cursors(project TEXT, reader TEXT, seq INTEGER, PRIMARY KEY(project,reader));
            CREATE TABLE IF NOT EXISTS submissions(id TEXT PRIMARY KEY, value TEXT);
            """)
            self.init_observations(c)
        self.settings({"session_token": secrets.token_urlsafe(32), "worker_token": secrets.token_urlsafe(32)}, defaults=True)

    @contextlib.contextmanager
    def connect(self):
        """Yield one SQLite connection and always close the OS handle.

        sqlite3.Connection.__exit__ commits/rolls back but deliberately does not
        close the connection. Relying on CPython refcount cleanup made Station
        data appear leak-free on POSIX while keeping station.sqlite3 locked on
        Windows. Every Store connection is scoped, so make that lifetime explicit.
        """
        c = sqlite3.connect(self.db, timeout=15)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    @contextlib.contextmanager
    def transaction(self):
        with self.lock, self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            yield c

    def settings(self, values=None, defaults=False):
        with self.transaction() as c:
            if values:
                for k, v in values.items():
                    c.execute(("INSERT OR IGNORE" if defaults else "INSERT OR REPLACE") + " INTO settings VALUES (?,?)", (k, canonical(v)))
            return {r["id"]: json.loads(r["value"]) for r in c.execute("SELECT * FROM settings")}

    def _project(self, c, pid):
        row = c.execute("SELECT value FROM projects WHERE id=?", (pid,)).fetchone()
        if not row:
            raise ContractError("Project was not found")
        return json.loads(row[0])

    def _task(self, c, pid, tid):
        row = c.execute("SELECT value FROM tasks WHERE project=? AND id=?", (pid, tid)).fetchone()
        if not row:
            raise ContractError("Task was not found")
        return json.loads(row[0])

    def _write_task(self, c, pid, task):
        task["updated_at"] = now()
        c.execute("UPDATE tasks SET value=? WHERE project=? AND id=?", (canonical(task), pid, task["id"]))

    def _event(self, c, project, event_type, actor, task=None, data=None):
        event = {"schema_version": 1, "event_id": uuid.uuid4().hex, "event_type": event_type,
                 "timestamp": now(), "project_id": project["id"], "task_id": task["id"] if task else None,
                 "actor": actor, "attempt": task["attempt"] if task else 0,
                 "spec_hash": project["spec_hash"], "data": data or {}}
        event_validate(event)
        prev = c.execute("SELECT hash FROM events WHERE project=? ORDER BY seq DESC LIMIT 1", (project["id"],)).fetchone()
        prev = prev[0] if prev else "0" * 64
        root = sha({"previous": prev, "event": event})
        cur = c.execute("INSERT INTO events(event_id,project,value,prev_hash,hash) VALUES(?,?,?,?,?)",
                        (event["event_id"], project["id"], canonical(event), prev, root))
        self.observe_workflow(c, event, root)
        return {**event, "seq": cur.lastrowid, "hash": root, "prev_hash": prev}

    def create_project(self, manifest, markdown, repo, mode="live", allow_cloud=False, commands=False):
        pid = "p-" + uuid.uuid4().hex[:12]
        project = {"id": pid, "name": manifest["name"], "goal": manifest["goal"], "spec": markdown,
                   "spec_hash": sha(manifest), "created_at": now(), "repo": str(repo), "mode": mode,
                   "allow_cloud": bool(allow_cloud), "commands": bool(commands), "paused": False,
                   "generation": 1, "policy_revision": 1, "stopped": False,
                   "mesh_assignments_reserved": 0, "mesh_cloud_assignments_reserved": 0,
                   "call_limit": 100, "cloud_call_limit": 30, "request_byte_limit": 5_000_000}
        with self.transaction() as c:
            c.execute("INSERT INTO projects VALUES(?,?)", (pid, canonical(project)))
            for definition in manifest["tasks"]:
                task = {**definition, "state": "proposed", "attempt": 0, "owner": None, "lease": None,
                        "lease_until": 0, "fencing_token": 0, "mesh_budget_reserved": False, "mesh_execution_budget": None,
                        "base_commit": None, "head_commit": None,
                        "checks_result": [], "baseline": [], "findings": [], "artifacts": [], "updated_at": now()}
                c.execute("INSERT INTO tasks VALUES(?,?,?)", (pid, task["id"], canonical(task)))
            self._event(c, project, "project.created", "operator", data={"name": project["name"], "tasks": len(manifest["tasks"]), "mode": mode})
        return pid

    def project(self, pid):
        with self.connect() as c:
            p = self._project(c, pid)
            p["tasks"] = [json.loads(r[0]) for r in c.execute("SELECT value FROM tasks WHERE project=? ORDER BY rowid", (pid,))]
        for t in p["tasks"]:
            t.pop("lease", None)
        return p

    def list_projects(self):
        with self.connect() as c:
            ids = [r[0] for r in c.execute("SELECT id FROM projects ORDER BY rowid DESC")]
        return [self.project(pid) for pid in ids]

    def task(self, pid, tid):
        with self.connect() as c:
            return self._task(c, pid, tid)

    def project_update(self, pid, **fields):
        with self.transaction() as c:
            p = self._project(c, pid)
            p.update(fields)
            c.execute("UPDATE projects SET value=? WHERE id=?", (canonical(p), pid))

    def pause(self, pid, paused):
        with self.transaction() as c:
            p = self._project(c, pid)
            p["paused"] = bool(paused)
            c.execute("UPDATE projects SET value=? WHERE id=?", (canonical(p), pid))
            self._event(c, p, "project.paused" if paused else "project.resumed", "operator")

    def advance_generation(self, pid, reason, actor="operator"):
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 300:
            raise ContractError("Generation change requires a bounded reason")
        with self.transaction() as c:
            p = self._project(c, pid)
            p["generation"] = int(p.get("generation", 1)) + 1
            c.execute("UPDATE projects SET value=? WHERE id=?", (canonical(p), pid))
            self._event(c, p, "mesh.generation.advanced", actor,
                        data={"generation": p["generation"], "reason": reason.strip()})
            return p["generation"]

    def mesh_stop(self, pid, actor="operator"):
        """Fail closed: stop new claims and revoke currently running mesh leases."""
        with self.transaction() as c:
            p = self._project(c, pid)
            p["stopped"] = True
            p["paused"] = True
            p["generation"] = int(p.get("generation", 1)) + 1
            c.execute("UPDATE projects SET value=? WHERE id=?", (canonical(p), pid))
            affected = []
            for row in c.execute("SELECT id,value FROM tasks WHERE project=?", (pid,)).fetchall():
                t = json.loads(row["value"])
                if t["state"] == "running" and (t.get("owner") or "").startswith("mesh:"):
                    affected.append({"task_id": t["id"], "owner": t.get("owner"),
                                     "fencing_token": t.get("fencing_token", 0)})
                    self._release_mesh_assignment(c, pid, t, p)
                    t.update(state="blocked", owner=None, lease=None, lease_until=0,
                             findings=["Mesh stop revoked execution authority; reconcile before retrying."])
                    self._write_task(c, pid, t)
            self._event(c, p, "mesh.stop.requested", actor,
                        data={"generation": p["generation"], "revoked_leases": affected})
            return {"generation": p["generation"], "revoked_leases": affected}

    def _release_mesh_assignment(self, c, pid, task, project=None):
        if not task.get("mesh_budget_reserved", False):
            return project
        p = project or self._project(c, pid)
        p["mesh_assignments_reserved"] = max(0, int(p.get("mesh_assignments_reserved", 0)) - 1)
        if task.get("route") == "cloud":
            p["mesh_cloud_assignments_reserved"] = max(0, int(p.get("mesh_cloud_assignments_reserved", 0)) - 1)
        task["mesh_budget_reserved"] = False
        c.execute("UPDATE projects SET value=? WHERE id=?", (canonical(p), pid))
        return p

    def transition(self, pid, tid, state, actor="coordinator", fields=None, lease=None, fencing_token=None):
        with self.transaction() as c:
            p, task = self._project(c, pid), self._task(c, pid, tid)
            if state not in TRANSITIONS[task["state"]]:
                raise ContractError(f"Cannot move {task['state']} to {state}")
            if task["state"] == "running":
                if not lease or not secrets.compare_digest(lease, task.get("lease") or "") or task["lease_until"] < time.time():
                    raise ContractError("Task lease has expired or belongs to another worker")
                if fencing_token is not None and task.get("fencing_token", 0) != fencing_token:
                    raise ContractError("Task fencing token is stale")
            prior = task["state"]
            task.update(fields or {})
            task["state"] = state
            if prior == "running":
                self._release_mesh_assignment(c, pid, task, p)
                task.update(lease=None, lease_until=0)
            self._write_task(c, pid, task)
            self._event(c, p, "task.transition", actor, task, {"from": prior, "to": state, "findings": task.get("findings", [])[:5]})
            return task

    def update_task(self, pid, tid, **fields):
        # Internal evidence updates only; state and ownership cannot bypass transitions.
        if set(fields) & {"state", "owner", "lease", "lease_until", "attempt"}:
            raise ContractError("Use the state transition/claim API")
        with self.transaction() as c:
            t = self._task(c, pid, tid)
            t.update(fields)
            self._write_task(c, pid, t)

    def claim(self, pid, owner, tid=None, routes=None, capabilities=None, reserve_budget=False):
        with self.transaction() as c:
            p = self._project(c, pid)
            if p["paused"] or p.get("stopped", False):
                return None
            routes = set(routes) if routes is not None else None
            capabilities = None if capabilities is None else set(capabilities)
            tasks = [json.loads(r[0]) for r in c.execute("SELECT value FROM tasks WHERE project=? ORDER BY rowid", (pid,))]
            states = {t["id"]: t["state"] for t in tasks}
            for t in tasks:
                if (tid and t["id"] != tid) or t["state"] not in {"ready", "repair_required"}:
                    continue
                if routes is not None and t["route"] not in routes:
                    continue
                if capabilities is not None and not set(t.get("capabilities", ())).issubset(capabilities):
                    continue
                if any(states[d] != "integrated" for d in t["depends_on"]):
                    continue
                if t["attempt"] >= MAX_TASK_ATTEMPTS:
                    continue
                if reserve_budget:
                    held = int(p.get("mesh_assignments_reserved", 0))
                    used = int(p.get("calls_reserved", 0))
                    if used + held >= int(p["call_limit"]):
                        continue
                    if t["route"] == "cloud":
                        cloud_held = int(p.get("mesh_cloud_assignments_reserved", 0))
                        cloud_used = int(p.get("cloud_calls_reserved", 0))
                        if cloud_used + cloud_held >= int(p["cloud_call_limit"]) or not p["allow_cloud"]:
                            continue
                    p["mesh_assignments_reserved"] = held + 1
                    if t["route"] == "cloud":
                        p["mesh_cloud_assignments_reserved"] = int(p.get("mesh_cloud_assignments_reserved", 0)) + 1
                    c.execute("UPDATE projects SET value=? WHERE id=?", (canonical(p), pid))
                t.update(state="running", owner=owner, attempt=t["attempt"] + 1,
                         lease=secrets.token_urlsafe(24), lease_until=time.time() + 900,
                         fencing_token=t.get("fencing_token", 0) + 1,
                         mesh_budget_reserved=bool(reserve_budget))
                self._write_task(c, pid, t)
                self._event(c, p, "task.claimed", owner, t,
                            {"route": t["route"], "lease_seconds": 900, "fencing_token": t["fencing_token"]})
                return t
            return None

    def reserve_mesh_execution(self, pid, tid, lease, fencing_token, generation, attempts):
        """Reserve the complete bounded provider-attempt plan before opaque claw execution."""
        from .contracts import task_execution_policy
        if not isinstance(attempts, list) or not 1 <= len(attempts) <= 5:
            raise ContractError("Execution admission requires one to five provider attempts")
        normalized = []
        for item in attempts:
            if not isinstance(item, dict) or set(item) != {"placement", "model", "request_bytes"}:
                raise ContractError("Provider attempt plan fields are invalid")
            placement, model, size = item["placement"], item["model"], item["request_bytes"]
            if placement not in {"local", "remote"}:
                raise ContractError("Invalid provider placement")
            if not isinstance(model, str) or not model or len(model) > 200 or any(ord(ch) < 33 for ch in model):
                raise ContractError("Invalid provider model ID")
            if type(size) is not int or size < 0:
                raise ContractError("Invalid provider request size")
            normalized.append({"placement": placement, "model": model, "request_bytes": size})
        with self.transaction() as c:
            p = self._project(c, pid)
            t = self._task(c, pid, tid)
            if int(p.get("generation", 1)) != generation:
                raise ContractError("Execution generation is stale")
            if t["state"] != "running" or t["lease_until"] < time.time() or not secrets.compare_digest(t.get("lease") or "", lease or ""):
                raise ContractError("Stale task lease")
            if t.get("fencing_token", 0) != fencing_token:
                raise ContractError("Stale task fencing token")
            if t.get("mesh_execution_budget") is not None:
                raise ContractError("Execution budget was already admitted for this task attempt")
            policy = task_execution_policy(t)
            if len(normalized) > policy["max_provider_attempts"]:
                raise ContractError("Provider attempt plan exceeds task approval")
            placements = [x["placement"] for x in normalized]
            if any(x not in policy["placements"] for x in placements):
                raise ContractError("Provider attempt placement is outside task approval")
            if len(set(placements)) > 1 and not policy["cross_placement"]:
                raise ContractError("Cross-placement fallback is not approved for this task")
            if any(x == "remote" for x in placements) and not p["allow_cloud"]:
                raise ContractError("Cloud sharing is disabled for this project")
            if policy["models"] and any(x["model"] not in policy["models"] for x in normalized):
                raise ContractError("Provider model is outside task approval")
            count = len(normalized)
            cloud_count = sum(x["placement"] == "remote" for x in normalized)
            byte_count = sum(x["request_bytes"] for x in normalized)
            held = int(bool(t.get("mesh_budget_reserved", False)))
            held_cloud = int(held and t["route"] == "cloud")
            calls_after = int(p.get("calls_reserved", 0)) + count
            cloud_after = int(p.get("cloud_calls_reserved", 0)) + cloud_count
            bytes_after = int(p.get("request_bytes_reserved", 0)) + byte_count
            # The assignment hold is separate from consumed call counters, so remove
            # it from outstanding holds before checking total committed capacity.
            outstanding = int(p.get("mesh_assignments_reserved", 0)) - held
            cloud_outstanding = int(p.get("mesh_cloud_assignments_reserved", 0)) - held_cloud
            if calls_after + outstanding > int(p["call_limit"]):
                raise ContractError("Project model-call budget is exhausted")
            if cloud_after + cloud_outstanding > int(p["cloud_call_limit"]):
                raise ContractError("Project cloud model-call budget is exhausted")
            if bytes_after > int(p["request_byte_limit"]):
                raise ContractError("Project request-byte budget is exhausted")
            if held:
                self._release_mesh_assignment(c, pid, t, p)
                p = self._project(c, pid)
            p["calls_reserved"] = int(p.get("calls_reserved", 0)) + count
            p["cloud_calls_reserved"] = int(p.get("cloud_calls_reserved", 0)) + cloud_count
            p["request_bytes_reserved"] = int(p.get("request_bytes_reserved", 0)) + byte_count
            t["mesh_execution_budget"] = {
                "attempts": normalized, "reserved_calls": count,
                "reserved_cloud_calls": cloud_count, "reserved_bytes": byte_count,
                "reconciled": False,
            }
            c.execute("UPDATE projects SET value=? WHERE id=?", (canonical(p), pid))
            self._write_task(c, pid, t)
            return dict(t["mesh_execution_budget"])

    def reconcile_mesh_execution(self, pid, tid, lease, fencing_token, provider_attempts):
        """Release only demonstrably unused conservative reservations."""
        if provider_attempts is None:
            return {"reconciled": False, "reason": "provider_attempts_unknown"}
        if not isinstance(provider_attempts, list) or len(provider_attempts) > 5:
            raise ContractError("Invalid provider attempt evidence")
        with self.transaction() as c:
            p = self._project(c, pid)
            t = self._task(c, pid, tid)
            if t["state"] != "running" or not secrets.compare_digest(t.get("lease") or "", lease or ""):
                raise ContractError("Stale task lease")
            if t.get("fencing_token", 0) != fencing_token:
                raise ContractError("Stale task fencing token")
            budget = t.get("mesh_execution_budget")
            if not isinstance(budget, dict) or budget.get("reconciled"):
                raise ContractError("No unreconciled execution budget exists")
            planned = budget["attempts"]
            if len(provider_attempts) > len(planned):
                raise ContractError("Observed provider attempts exceed the admitted plan")
            actual_bytes = 0
            actual_cloud = 0
            for index, observed in enumerate(provider_attempts):
                allowed = {"placement", "model", "request_bytes", "status", "reason", "usage_known"}
                if not isinstance(observed, dict) or set(observed) - allowed:
                    raise ContractError("Invalid provider attempt evidence fields")
                plan = planned[index]
                for key in ("placement", "model"):
                    if observed.get(key) != plan[key]:
                        raise ContractError("Observed provider route does not match the admitted plan")
                size = observed.get("request_bytes")
                if type(size) is not int or size < 0 or size > plan["request_bytes"]:
                    raise ContractError("Observed request bytes exceed the admitted bound")
                if observed.get("status") not in {"completed", "failed", "uncertain"}:
                    raise ContractError("Invalid provider attempt status")
                if type(observed.get("usage_known")) is not bool:
                    raise ContractError("usage_known must be boolean")
                actual_bytes += size
                actual_cloud += int(observed["placement"] == "remote")
            unused_calls = len(planned) - len(provider_attempts)
            unused_cloud = budget["reserved_cloud_calls"] - actual_cloud
            unused_bytes = budget["reserved_bytes"] - actual_bytes
            p["calls_reserved"] = max(0, int(p.get("calls_reserved", 0)) - unused_calls)
            p["cloud_calls_reserved"] = max(0, int(p.get("cloud_calls_reserved", 0)) - unused_cloud)
            p["request_bytes_reserved"] = max(0, int(p.get("request_bytes_reserved", 0)) - unused_bytes)
            budget["reconciled"] = True
            budget["observed_attempts"] = provider_attempts
            budget["uncertain_usage"] = any(not x["usage_known"] or x["status"] == "uncertain" for x in provider_attempts)
            t["mesh_execution_budget"] = budget
            c.execute("UPDATE projects SET value=? WHERE id=?", (canonical(p), pid))
            self._write_task(c, pid, t)
            return {"reconciled": True, "uncertain_usage": budget["uncertain_usage"],
                    "calls_reserved": p["calls_reserved"], "request_bytes_reserved": p["request_bytes_reserved"]}

    def reserve_mesh_attempt(self, pid, tid, lease, fencing_token, placement, request_bytes):
        if placement not in {"local", "remote"}:
            raise ContractError("Invalid provider placement")
        if type(request_bytes) is not int or request_bytes < 0:
            raise ContractError("Invalid provider request size")
        with self.transaction() as c:
            p = self._project(c, pid)
            t = self._task(c, pid, tid)
            if t["state"] != "running" or t["lease_until"] < time.time() or not secrets.compare_digest(t.get("lease") or "", lease or ""):
                raise ContractError("Stale task lease")
            if t.get("fencing_token", 0) != fencing_token:
                raise ContractError("Stale task fencing token")
            required = "local" if t["route"] == "local" else "remote"
            if placement != required:
                raise ContractError("Cross-placement fallback is not approved for this task")
            if placement == "remote" and not p["allow_cloud"]:
                raise ContractError("Cloud sharing is disabled for this project")
            held = bool(t.get("mesh_budget_reserved", False))
            calls = int(p.get("calls_reserved", 0))
            cloud = int(p.get("cloud_calls_reserved", 0))
            sent = int(p.get("request_bytes_reserved", 0))
            effective_calls = calls + int(p.get("mesh_assignments_reserved", 0)) - int(held)
            effective_cloud = cloud + int(p.get("mesh_cloud_assignments_reserved", 0)) - int(held and t["route"] == "cloud")
            if effective_calls >= int(p["call_limit"]):
                raise ContractError("Project model-call budget is exhausted")
            if placement == "remote" and effective_cloud >= int(p["cloud_call_limit"]):
                raise ContractError("Project cloud model-call budget is exhausted")
            if sent + request_bytes > int(p["request_byte_limit"]):
                raise ContractError("Project request-byte budget is exhausted")
            if held:
                self._release_mesh_assignment(c, pid, t, p)
                p = self._project(c, pid)
            p["calls_reserved"] = int(p.get("calls_reserved", 0)) + 1
            p["cloud_calls_reserved"] = int(p.get("cloud_calls_reserved", 0)) + int(placement == "remote")
            p["request_bytes_reserved"] = int(p.get("request_bytes_reserved", 0)) + request_bytes
            c.execute("UPDATE projects SET value=? WHERE id=?", (canonical(p), pid))
            self._write_task(c, pid, t)
            return {"calls_reserved": p["calls_reserved"],
                    "cloud_calls_reserved": p["cloud_calls_reserved"],
                    "request_bytes_reserved": p["request_bytes_reserved"]}

    def validate_lease(self, pid, tid, lease, fencing_token=None):
        with self.connect() as c:
            t = self._task(c, pid, tid)
        if t["state"] != "running" or t["lease_until"] < time.time() or not secrets.compare_digest(t.get("lease") or "", lease or ""):
            raise ContractError("Stale task lease")
        if fencing_token is not None and t.get("fencing_token", 0) != fencing_token:
            raise ContractError("Stale task fencing token")
        return t

    def heartbeat(self, pid, tid, lease, fencing_token=None, renew=True):
        with self.transaction() as c:
            t = self._task(c, pid, tid)
            if t["state"] != "running" or t["lease_until"] < time.time() or not secrets.compare_digest(t.get("lease") or "", lease or ""):
                raise ContractError("Stale task lease")
            if fencing_token is not None and t.get("fencing_token", 0) != fencing_token:
                raise ContractError("Stale task fencing token")
            if renew:
                t["lease_until"] = time.time() + 900
                self._write_task(c, pid, t)
            return t

    def recover(self, startup=False):
        with self.transaction() as c:
            for row in c.execute("SELECT project,value FROM tasks").fetchall():
                t = json.loads(row["value"])
                expired = t["state"] == "running" and (t["lease_until"] < time.time() or (startup and not (t.get("owner") or "").startswith("remote:")))
                interrupted = startup and t["state"] in {"triaging", "local_verified"}
                if not (expired or interrupted):
                    continue
                prior = t["state"]
                if t["state"] == "running":
                    self._release_mesh_assignment(c, row["project"], t)
                t.update(state="blocked", owner=None, lease=None, lease_until=0,
                         findings=["Interrupted work requires re-triage. Existing evidence is retained."])
                self._write_task(c, row["project"], t)
                self._event(c, self._project(c, row["project"]), "worker.expired", "coordinator", t, {"from": prior})
            if startup:
                for r in c.execute("SELECT id,value FROM jobs").fetchall():
                    j = json.loads(r["value"])
                    if j["state"] in {"queued", "running"}:
                        j.update(state="interrupted", detail="The station restarted; start this operation again.")
                        c.execute("UPDATE jobs SET value=? WHERE id=?", (canonical(j), r["id"]))

    def event(self, pid, event_type, data, tid=None, actor="coordinator"):
        with self.transaction() as c:
            return self._event(c, self._project(c, pid), event_type, actor, self._task(c, pid, tid) if tid else None, data)

    def events(self, pid, after=0, limit=300):
        with self.connect() as c:
            rows = c.execute("SELECT * FROM events WHERE project=? AND seq>? ORDER BY seq LIMIT ?", (pid, after, limit))
            return [{**json.loads(r["value"]), "seq": r["seq"], "hash": r["hash"], "prev_hash": r["prev_hash"]} for r in rows]

    def add_artifact(self, pid, name, content, kind="text"):
        if isinstance(content, str):
            content = content.encode()
        if len(content) > 50_000_000:
            raise ContractError("Artifact exceeds 50 MB")
        aid = hashlib.sha256(content).hexdigest()
        directory = self.root / "artifacts" / pid
        directory.mkdir(parents=True, exist_ok=True)
        (directory / aid).write_bytes(content)
        key = pid + ":" + aid
        with self.transaction() as c:
            c.execute("INSERT OR IGNORE INTO artifacts VALUES(?,?,?,?,?)", (key, pid, name, len(content), kind))
        return {"id": key, "sha256": aid, "name": name, "size": len(content), "kind": kind}

    def artifact(self, aid):
        with self.connect() as c:
            row = c.execute("SELECT * FROM artifacts WHERE id=?", (aid,)).fetchone()
        if not row:
            raise ContractError("Artifact was not found")
        data = (self.root / "artifacts" / row["project"] / aid.split(":")[1]).read_bytes()
        if hashlib.sha256(data).hexdigest() != aid.split(":")[1]:
            raise ContractError("Artifact integrity check failed")
        return dict(row), data

    def job(self, kind, pid=None):
        j = {"id": uuid.uuid4().hex[:16], "kind": kind, "project": pid, "state": "queued", "created_at": now(), "detail": "Queued", "progress": None}
        with self.transaction() as c:
            c.execute("INSERT INTO jobs VALUES(?,?)", (j["id"], canonical(j)))
        return j["id"]

    def job_update(self, jid, **fields):
        with self.transaction() as c:
            row = c.execute("SELECT value FROM jobs WHERE id=?", (jid,)).fetchone()
            j = json.loads(row[0]); j.update(fields, updated_at=now())
            c.execute("UPDATE jobs SET value=? WHERE id=?", (canonical(j), jid))

    def jobs(self):
        with self.connect() as c:
            return [json.loads(r[0]) for r in c.execute("SELECT value FROM jobs ORDER BY rowid DESC LIMIT 40")]

    def reserve_call(self, pid, role, placement, request_bytes, task_id=None):
        with self.transaction() as c:
            p = self._project(c, pid)
            calls = p.setdefault("calls_reserved", 0)
            cloud = p.setdefault("cloud_calls_reserved", 0)
            sent = p.setdefault("request_bytes_reserved", 0)
            if calls >= p["call_limit"] or (placement == "remote" and cloud >= p["cloud_call_limit"]) or sent + request_bytes > p["request_byte_limit"]:
                raise ContractError("Project model-call budget is exhausted")
            if placement == "remote" and not p["allow_cloud"]:
                raise ContractError("Cloud sharing is disabled for this project")
            p.update(calls_reserved=calls + 1, cloud_calls_reserved=cloud + int(placement == "remote"), request_bytes_reserved=sent + request_bytes)
            c.execute("UPDATE projects SET value=? WHERE id=?", (canonical(p), pid))

    def report(self, pid, reader="cloud-review", acknowledge=False):
        project = self.project(pid)
        with self.connect() as c:
            row = c.execute("SELECT seq FROM cursors WHERE project=? AND reader=?", (pid, reader)).fetchone()
        after = row[0] if row else 0
        events = self.events(pid, after, limit=1000)
        # Factual delta; no inference, no logs or raw source copied into the shared feed.
        changes = [{"seq": e["seq"], "task": e["task_id"], "event": e["event_type"], "data": e["data"]}
                   for e in events if e["event_type"] not in {"usage.recorded", "report.generated"}]
        report = {"schema_version": 1, "project": pid, "goal": project["goal"], "spec_hash": project["spec_hash"],
                  "from_seq": after, "through_seq": events[-1]["seq"] if events else after,
                  "tasks": [{**{k: t[k] for k in ("id", "title", "state", "depends_on", "head_commit", "findings")},
                    **({"receipt_hash": t["verification_receipt"]["receipt"]["receipt_hash"]} if t.get("verification_receipt") else {})}
                    for t in project["tasks"]],
                  "changes": changes}
        if acknowledge:
            self.acknowledge(pid, reader, report["through_seq"])
        return report

    def acknowledge(self, pid, reader, seq):
        with self.transaction() as c:
            c.execute("INSERT INTO cursors VALUES(?,?,?) ON CONFLICT(project,reader) DO UPDATE SET seq=max(seq,excluded.seq)", (pid, reader, seq))

    def markdown(self, pid):
        p = self.project(pid)
        lines = [f"# {p['name']}", "", p["goal"], "", f"Spec SHA-256: `{p['spec_hash']}`", "",
                 "| Task | State | Attempt | Commit | Receipt |", "|---|---|---:|---|---|"]
        for t in p["tasks"]:
            receipt = t.get("verification_receipt", {}).get("receipt", {}).get("receipt_hash", "—")
            lines.append(f"| {t['id']} | {t['state']} | {t['attempt']} | {(t['head_commit'] or '—')[:12]} | {receipt[:12]} |")
        if p.get("last_run"):
            lines += ["", "## Run control", "", "```json", json.dumps(p["last_run"], indent=2), "```"]
        lines += ["", "## State snapshot", "", "```json", json.dumps(self.report(pid, "markdown"), indent=2), "```", "",
                  "## Original specification", "", p["spec"]]
        return "\n".join(lines)
