#!/usr/bin/env python3
"""G1 reconciler adversarial lifecycle vector runner.

Executes the machine-readable corpus in ``vectors/g1_adversarial_vectors.json``
against the CURRENT RuntimeJournal / Station Store / DSM store where the
normative semantic already exists. Vectors with no current implementation
binding are reported UNKNOWN (pending_implementation) -- never as PASS.

Stdlib-only; usable as a plain script or importable by a pytest wrapper.

Usage:
    python tests/reconciler/run_vectors.py [--report PATH] [--vector ID ...]

Exit code: 0 when no vector FAILs (PASS/UNKNOWN/BLOCKED reported as such);
1 when any vector FAILs; 2 on harness error. UNKNOWN/BLOCKED are never PASS.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from residual.core import ContractError  # noqa: E402
from residual.factory.runtime_journal import JournalError, RuntimeJournal  # noqa: E402
from residual.factory.worker_contract import WorkerContract  # noqa: E402
from residual.dsm.store import CrashError, DistributedStateStore  # noqa: E402
from residual.dsm.delivery import Inbox, Outbox  # noqa: E402
from residual.station.store import Store as StationStore  # noqa: E402

CORPUS = Path(__file__).resolve().parent / "vectors" / "g1_adversarial_vectors.json"

PLAN = "ab" * 32  # 64 hex chars
COMMIT = "cd" * 20  # 40 hex chars (valid git object id form)


def make_contract(tmp: str, tag: str, *, task: str = "task-1", generation: int = 1,
                  worker: str | None = None, lease: str | None = None,
                  workspace: str | None = None, plan: str = PLAN) -> WorkerContract:
    return WorkerContract(
        task_id=task,
        worker_id=worker or f"worker-{tag}",
        swarm_id="swarm-g1v",
        execution_plan_hash=plan,
        attempt_id=f"attempt-{tag}",
        lease_id=lease or f"lease-{tag}",
        lease_generation=generation,
        input_commit=COMMIT,
        workspace_root=workspace or f"/ws/{tag}",
        inputs=("in.txt",),
        allowed_outputs=("out.txt",),
        forbidden=(),
        requirements=("req-1",),
        acceptance=("acc-1",),
        dependencies=(),
        allowed_tools=(),
        forbidden_tools=(),
        token_budget=1000,
        wall_clock_budget_s=60.0,
        max_tool_calls=10,
        max_file_writes=10,
        memory_limit_mb=256,
    )


def new_journal(tmp: str, trace_id: str = "trace-g1v") -> RuntimeJournal:
    return RuntimeJournal(Path(tmp) / "runtime.journal", trace_id=trace_id)


def claim(tmp: str, tag: str, journal: RuntimeJournal | None = None, **kw):
    journal = journal or new_journal(tmp)
    contract = make_contract(tmp, tag, **kw)
    journal.claim(contract, source_hash="0" * 64, approval={"by": "g1v-harness"})
    return journal, contract


def events_payloads(journal: RuntimeJournal, event_name: str) -> list[dict]:
    return [o.payload for o in journal.observations() if o.payload.get("event") == event_name]


def ok(detail: dict | None = None) -> dict:
    return {"status": "PASS", "detail": detail or {}}


def fail(msg: str, detail: dict | None = None) -> dict:
    return {"status": "FAIL", "detail": {"reason": msg, **(detail or {})}}


# ---------------------------------------------------------------- G1V-01
def g1v01_stale_generation_claim() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        journal, c1 = claim(tmp, "v01-a", generation=2)
        journal.finish(c1, "FAILED")
        events_before = len(journal.observations())
        attempts_before = len(journal.attempts())
        c2 = make_contract(tmp, "v01-b", generation=2)
        try:
            journal.claim(c2, source_hash="0" * 64, approval={})
        except JournalError as exc:
            if "lease generation must increase" not in str(exc):
                return fail(f"unexpected message: {exc}")
        else:
            return fail("stale-generation claim was accepted")
        if len(journal.observations()) != events_before or len(journal.attempts()) != attempts_before:
            return fail("rejected claim mutated the journal")
        return ok({"rejection": "JournalError", "events_appended": 0, "attempts_added": 0})


# ---------------------------------------------------------------- G1V-02
def g1v02_claim_while_active() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        journal, _c1 = claim(tmp, "v02-a", generation=1)
        c2 = make_contract(tmp, "v02-b", generation=2)
        try:
            journal.claim(c2, source_hash="0" * 64, approval={})
        except JournalError as exc:
            if "active or quarantined" not in str(exc):
                return fail(f"unexpected message: {exc}")
        else:
            return fail("second claim for a task with an active attempt was accepted")
        return ok({"rejection": "JournalError: task already has an active or quarantined attempt"})


# ---------------------------------------------------------------- G1V-03
def g1v03_identity_uniqueness() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        journal, c1 = claim(tmp, "v03-a")
        rejections = {}
        for field, kw in (
            ("worker_id", {"worker": c1.worker_id}),
            ("lease_id", {"lease": c1.lease_id}),
            ("workspace", {"workspace": c1.workspace_root}),
        ):
            dup = make_contract(tmp, f"v03-dup-{field}", task=f"task-{field}", **kw)
            try:
                journal.claim(dup, source_hash="0" * 64, approval={})
            except JournalError as exc:
                rejections[field] = str(exc)
                if "identity was already used" not in str(exc):
                    return fail(f"{field}: unexpected message: {exc}")
            else:
                return fail(f"{field}: duplicate identity accepted")
        if len(journal.attempts()) != 1:
            return fail("partial rows committed by rejected claims")
        return ok({"rejections": rejections})


# ---------------------------------------------------------------- G1V-04
def g1v04_started_after_revoke() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        journal, c1 = claim(tmp, "v04-a")
        journal.revoke(c1.attempt_id)
        try:
            journal.started(c1, pid=1234)
        except JournalError as exc:
            if "not reserved or has been revoked" not in str(exc):
                return fail(f"unexpected message: {exc}")
        else:
            return fail("started() accepted on a revoked attempt")
        # variant: started twice on a live attempt
        _j2, c2 = claim(tmp, "v04-b", journal=journal, task="task-2")
        journal.started(c2, pid=1235)
        try:
            journal.started(c2, pid=1236)
        except JournalError:
            pass
        else:
            return fail("second started() on a RUNNING attempt was accepted")
        spawns = events_payloads(journal, "RuntimeProcessSpawned")
        if len(spawns) != 1 or spawns[0]["attempt_id"] != c2.attempt_id:
            return fail("unexpected RuntimeProcessSpawned events", {"spawns": spawns})
        return ok({"spawn_events": 1})


# ---------------------------------------------------------------- G1V-05
def g1v05_dsm_commit_before_ack() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        store = DistributedStateStore(tmp)
        event = {"event_id": "e1", "domain": "task.terminal", "entity": "task-1",
                 "value": "succeeded", "writer": "orchestrator"}
        try:
            store.submit(event, crash_after="journal_write")
        except CrashError:
            pass
        else:
            return fail("crash_after='journal_write' did not raise CrashError")
        recovered = DistributedStateStore.recover(tmp)
        second = recovered.submit(event)
        if second["disposition"] != "duplicate":
            return fail("resubmit after crash was not a duplicate", {"got": second})
        transitions = recovered.accepted_transitions()
        if len(transitions) != 1:
            return fail("expected exactly one durable journal record", {"count": len(transitions)})
        if (second["seq"], second["hash"]) != (transitions[0]["seq"], transitions[0]["hash"]):
            return fail("duplicate ack does not carry the original (seq, hash)")
        if recovered.current_value("task.terminal", "task-1") != "succeeded":
            return fail("terminal value not reconstructed from the journal")
        return ok({"seq": second["seq"], "journal_records": 1})


# ---------------------------------------------------------------- G1V-06
_CHILD = r"""
import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
tmp = sys.argv[2]
from residual.factory.runtime_journal import RuntimeJournal
from residual.factory.worker_contract import WorkerContract

journal = RuntimeJournal(Path(tmp) / "runtime.journal", trace_id="trace-g1v06")
c = WorkerContract(task_id="task-1", worker_id="worker-v06", swarm_id="swarm-g1v",
                   execution_plan_hash="ab" * 32, attempt_id="attempt-v06",
                   lease_id="lease-v06", lease_generation=1, input_commit="cd" * 20,
                   workspace_root="/ws/v06", inputs=("in.txt",), allowed_outputs=("out.txt",),
                   forbidden=(), requirements=("r",), acceptance=("a",), dependencies=(),
                   allowed_tools=(), forbidden_tools=(), token_budget=1000,
                   wall_clock_budget_s=60.0, max_tool_calls=10, max_file_writes=10,
                   memory_limit_mb=256)
journal.claim(c, source_hash="0" * 64, approval={})

orig = RuntimeJournal._open_write_transaction

class KillAfterCommit:
    def __init__(self, db):
        self._db = db
    def execute(self, sql, *a):
        cur = self._db.execute(sql, *a)
        if sql.strip().upper().startswith("COMMIT"):
            os._exit(42)  # simulated SIGKILL after durable COMMIT, before ack
        return cur
    def __getattr__(self, name):
        return getattr(self._db, name)

def patched(self, deadline):
    return KillAfterCommit(orig(self, deadline))

RuntimeJournal._open_write_transaction = patched
journal.finish(c, "FAILED")
os._exit(3)  # must not reach here
"""


def g1v06_sqlite_commit_kill() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ)
        proc = subprocess.run([sys.executable, "-c", _CHILD, str(REPO_ROOT), tmp],
                              capture_output=True, text=True, timeout=60, env=env)
        if proc.returncode != 42:
            return fail("child did not die at the injected commit window",
                        {"returncode": proc.returncode, "stderr": proc.stderr[-800:]})
        journal = new_journal(tmp, trace_id="trace-g1v06")  # constructor chain check must pass
        rows = [a for a in journal.attempts() if a["attempt_id"] == "attempt-v06"]
        if len(rows) != 1 or rows[0]["state"] != "FAILED":
            return fail("expected exactly one FAILED terminal row after restart", {"rows": rows})
        finishes = events_payloads(journal, "RuntimeAttemptFinished")
        if len(finishes) != 1:
            return fail("expected exactly one RuntimeAttemptFinished event", {"count": len(finishes)})
        contract = make_contract(tmp, "v06", generation=1)
        try:
            journal.finish(contract, "VIOLATED")
        except JournalError as exc:
            if "already terminal or unknown" not in str(exc):
                return fail(f"unexpected refinish message: {exc}")
        else:
            return fail("refinish after writer death was accepted")
        return ok({"child_exit": 42, "terminal_count": 1, "refinish": "JournalError"})


# ---------------------------------------------------------------- G1V-07
def g1v07_concurrent_finish() -> dict:
    interleavings = 20
    for i in range(interleavings):
        with tempfile.TemporaryDirectory() as tmp:
            journal, c = claim(tmp, f"v07-{i}")
            journal.started(c, pid=1000 + i)
            outcomes: list[str] = []

            def racer(state: str) -> None:
                try:
                    journal.finish(c, state)
                    outcomes.append("win")
                except JournalError:
                    outcomes.append("lose")

            t1 = threading.Thread(target=racer, args=("FAILED",))
            t2 = threading.Thread(target=racer, args=("VIOLATED",))
            t1.start(); t2.start(); t1.join(); t2.join()
            if sorted(outcomes) != ["lose", "win"]:
                return fail("race did not produce exactly one winner", {"outcomes": outcomes})
            finishes = events_payloads(journal, "RuntimeAttemptFinished")
            if len(finishes) != 1:
                return fail("more than one terminal event committed", {"count": len(finishes)})
            row = [a for a in journal.attempts() if a["attempt_id"] == c.attempt_id][0]
            if row["state"] not in {"FAILED", "VIOLATED"}:
                return fail("final row not terminal", {"state": row["state"]})
    return ok({"interleavings": interleavings, "winners_per_race": 1})


# ---------------------------------------------------------------- G1V-08
def g1v08_revoke_vs_finish() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        journal, c1 = claim(tmp, "v08-a")
        journal.started(c1, pid=2001)
        journal.revoke(c1.attempt_id)
        try:
            journal.finish(c1, "CANDIDATE")
        except JournalError as exc:
            if "revoked attempt cannot produce a candidate" not in str(exc):
                return fail(f"unexpected message: {exc}")
        else:
            return fail("revoked attempt produced a candidate")
        _j, c2 = claim(tmp, "v08-b", journal=journal, task="task-2")
        journal.started(c2, pid=2002)
        journal.finish(c2, "FAILED")
        try:
            journal.revoke(c2.attempt_id)
        except JournalError as exc:
            if "only an active attempt can be revoked" not in str(exc):
                return fail(f"unexpected message: {exc}")
        else:
            return fail("terminal attempt was revoked (terminal must be absorbing)")
        return ok({"revoke_then_candidate": "JournalError", "finish_then_revoke": "JournalError"})


# ---------------------------------------------------------------- G1V-09
def _station_running_task(store: StationStore) -> tuple[str, str, str]:
    pid = store.create_project(
        {"name": "g1v09", "goal": "vector fixture",
         "tasks": [{"id": "t1", "route": "local", "depends_on": []}]},
        "spec", REPO_ROOT)
    store.transition(pid, "t1", "triaging")
    store.transition(pid, "t1", "ready")
    task = store.claim(pid, "local-runner")
    return pid, "t1", task["lease"]


def _rewind_lease(store: StationStore, pid: str, tid: str) -> None:
    # Fixture-only setup: force deterministic expiry via the store's own
    # transaction machinery (test fixture, not a production mutation path).
    with store.transaction() as c:
        task = store._task(c, pid, tid)
        task["lease_until"] = time.time() - 10
        store._write_task(c, pid, task)


def g1v09_stale_lease() -> dict:
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        store = StationStore(tmp)
        # variant 1: expired lease transition
        pid, tid, lease = _station_running_task(store)
        before = store.task(pid, tid)
        _rewind_lease(store, pid, tid)
        try:
            store.transition(pid, tid, "local_verified", lease=lease)
        except ContractError as exc:
            results["expired"] = str(exc)
        else:
            return fail("transition with expired lease accepted")
        if store.task(pid, tid)["state"] != before["state"]:
            return fail("stale projection mutated task state")
        # variant 2: forged token of identical length on a fresh running task
        pid2, tid2, lease2 = _station_running_task(store)
        forged = ("A" if lease2[0] != "A" else "B") + lease2[1:]
        try:
            store.transition(pid2, tid2, "local_verified", lease=forged)
        except ContractError:
            results["forged_same_length"] = "ContractError"
        else:
            return fail("forged same-length lease token accepted")
        # variant 3: stale heartbeat
        try:
            store.heartbeat(pid, tid, lease)
        except ContractError as exc:
            results["stale_heartbeat"] = str(exc)
        else:
            return fail("heartbeat with stale lease accepted")
    return ok(results)


# ---------------------------------------------------------------- G1V-10
def g1v10_duplicate_delivery() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "inbox.journal"
        event = {"event_id": "e-dup", "domain": "task.terminal", "entity": "t1",
                 "value": "failed", "writer": "orchestrator"}
        inbox = Inbox(path)
        first = inbox.deliver(event)
        second = inbox.deliver(event)
        inbox2 = Inbox(path)  # simulated receiver restart
        third = inbox2.deliver(event)
        if [first, second, third] != ["accepted", "duplicate", "duplicate"]:
            return fail("unexpected disposition sequence",
                        {"got": [first, second, third]})
        records = [r for r in inbox2.journal.replay(-1) if r["kind"] == "deliver"]
        if len(records) != 1:
            return fail("expected exactly one deliver journal record", {"count": len(records)})
        return ok({"dispositions": [first, second, third], "journal_records": 1})


# ---------------------------------------------------------------- G1V-11
def g1v11_writer_restart_outbox() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "outbox.journal"
        outbox = Outbox(path)
        for i in range(1, 6):
            outbox.publish({"event_id": f"E{i}"})
        outbox.acks.ack("E1")
        outbox.acks.ack("E2")
        restarted = Outbox(path)  # writer restart
        pending = [e["event_id"] for e in restarted.pending()]
        if pending != ["E3", "E4", "E5"]:
            return fail("pending set not reconstructed from durable journals", {"pending": pending})
        restarted.publish({"event_id": "E1"})  # idempotent retry
        if [e["event_id"] for e in restarted.pending()] != ["E3", "E4", "E5"]:
            return fail("re-publish of a known event was not a no-op")
        if restarted.acks.ack("E1") is not False:
            return fail("re-ack of an acked event did not return False")
        return ok({"pending": pending})


# ---------------------------------------------------------------- G1V-12
def g1v12_scheduler_unavailable_recovery() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        store = StationStore(tmp)
        pid = store.create_project(
            {"name": "g1v12", "goal": "vector fixture",
             "tasks": [{"id": "t1", "route": "local", "depends_on": []}]},
            "spec", REPO_ROOT)
        store.transition(pid, "t1", "triaging")
        store.transition(pid, "t1", "ready")
        task = store.claim(pid, "local-runner")  # running, lease valid 900s
        assert task and task["state"] == "running"
        store.job("integration", pid=pid)  # queued job
        with store.transaction() as c:  # fixture: mark the job running
            row = c.execute("SELECT id,value FROM jobs").fetchone()
            j = json.loads(row["value"]); j["state"] = "running"
            c.execute("UPDATE jobs SET value=? WHERE id=?",
                      (json.dumps(j, sort_keys=True), row["id"]))
        store.recover(startup=True)  # coordinator restart; scheduler plane absent
        after = store.task(pid, "t1")
        if after["state"] != "blocked":
            return fail("in-flight local task was not force-blocked", {"state": after["state"]})
        if after["owner"] is not None or after["lease"] is not None:
            return fail("owner/lease not cleared by recovery")
        events = store.events(pid)
        if not any(e["event_type"] == "worker.expired" for e in events):
            return fail("no worker.expired event recorded")
        if any(e["event_type"] == "task.transition" and e["data"].get("to") in
               {"local_verified", "review_ready", "approved", "integrated"} for e in events):
            return fail("a terminal-success transition was recorded for a lost scheduler context")
        with store.connect() as c:
            job = json.loads(c.execute("SELECT value FROM jobs").fetchone()["value"])
        if job["state"] != "interrupted":
            return fail("running job not interrupted by startup recovery", {"state": job["state"]})
        return ok({"task_state": after["state"], "event": "worker.expired",
                   "job_state": job["state"], "no_terminal_success": True})


# ---------------------------------------------------------------- G1V-13
def g1v13_lease_read_tristate() -> dict:
    states = {}
    # mode: deadline exhausted
    with tempfile.TemporaryDirectory() as tmp:
        journal, c = claim(tmp, "v13-deadline")
        read = journal.lease_read(c, deadline=time.monotonic() - 1)
        if read.state != "unknown" or read.diag != ("read_budget_exhausted", 0):
            return fail("deadline-exhausted read not unknown with bounded diag",
                        {"read": tuple(read)})
        states["deadline_exhausted"] = f"{read.state}:{read.diag}"
    # mode: row deleted out-of-band
    with tempfile.TemporaryDirectory() as tmp:
        journal, c = claim(tmp, "v13-rowdel")
        with sqlite3.connect(journal.path) as db:
            db.execute("DELETE FROM attempts WHERE attempt_id=?", (c.attempt_id,))
        read = journal.lease_read(c)
        if read.state != "revoked":
            return fail("missing row must read as revoked, never unknown", {"read": tuple(read)})
        states["row_deleted"] = read.state
    # mode: revoked flag flipped out-of-band
    with tempfile.TemporaryDirectory() as tmp:
        journal, c = claim(tmp, "v13-oob")
        with sqlite3.connect(journal.path) as db:
            db.execute("UPDATE attempts SET revoked=1 WHERE attempt_id=?", (c.attempt_id,))
        read = journal.lease_read(c)
        if read.state != "revoked":
            return fail("out-of-band revoked row must read as revoked", {"read": tuple(read)})
        states["revoked_oob"] = read.state
    # mode: corrupt DB file
    with tempfile.TemporaryDirectory() as tmp:
        journal, c = claim(tmp, "v13-corrupt")
        del journal  # drop writer before fixture corrupts the file
        Path(tmp, "runtime.journal").write_bytes(b"\x00\xffgarbage-not-sqlite" * 64)
        # lease_read opens its own connection; corruption must surface as 'unknown'.
        # Build a bare probe without the constructor (which correctly refuses a
        # corrupt chain) since lease_read is a watchdog-facing bounded read.
        import residual.factory.runtime_journal as rj_mod
        probe = object.__new__(rj_mod.RuntimeJournal)
        probe.path = Path(tmp) / "runtime.journal"
        read = probe.lease_read(c)
        if read.state != "unknown":
            return fail("corrupt store must read as unknown, never revoked/pass",
                        {"read": tuple(read)})
        diag = read.diag
        if not (isinstance(diag, tuple) and len(diag) == 2 and isinstance(diag[0], str)
                and isinstance(diag[1], int)):
            return fail("unknown diag must be (exc_type, sqlite_errorcode) only", {"diag": diag})
        states["db_corrupt"] = f"{read.state}:{diag}"
    return ok(states)


# ---------------------------------------------------------------- G1V-15
def g1v15_mark_purged_active() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        journal, c = claim(tmp, "v15")
        try:
            journal.mark_purged(c.attempt_id)
        except JournalError as exc:
            if "active attempts cannot be purged" not in str(exc):
                return fail(f"unexpected message: {exc}")
        else:
            return fail("active attempt was purged")
        journal.finish(c, "FAILED")
        journal.mark_purged(c.attempt_id)
        row = [a for a in journal.attempts() if a["attempt_id"] == c.attempt_id][0]
        if row["state"] != "PURGED":
            return fail("post-terminal purge did not apply", {"state": row["state"]})
        observation = None
        try:
            journal.mark_purged(c.attempt_id)  # second purge: currently allowed
            observation = ("second purge re-applied PURGED (currently allowed; "
                           "predicted FAIL if once-only purge is ratified normative)")
        except JournalError:
            observation = "second purge rejected (once-only semantics)"
        return ok({"active_purge": "JournalError", "post_terminal_purge": "PURGED",
                   "observation": observation})


# ---------------------------------------------------------------- G1V-16
def g1v16_first_failure_retention() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        journal, c = claim(tmp, "v16")
        journal.started(c, pid=3001)
        journal.finish(c, "FAILED")  # first failure commits
        try:
            journal.finish(c, "CANDIDATE")
        except JournalError:
            pass
        else:
            return fail("conflicting second terminal was accepted by the journal")
        finishes = events_payloads(journal, "RuntimeAttemptFinished")
        if len(finishes) != 1 or finishes[0]["state"] != "FAILED":
            return fail("first failure not retained verbatim", {"events": finishes})
        store = DistributedStateStore(Path(tmp) / "dsm")
        e1 = {"event_id": "t1-first", "domain": "task.terminal", "entity": "task-9",
              "value": "failed", "writer": "orchestrator"}
        e2 = {"event_id": "t1-second", "domain": "task.terminal", "entity": "task-9",
              "value": "succeeded", "writer": "orchestrator"}
        if store.submit(e1)["disposition"] != "accepted":
            return fail("first DSM terminal not accepted")
        try:
            store.submit(e2)
        except ContractError:
            pass
        else:
            return fail("DSM accepted a transition out of an absorbing terminal state")
        if store.current_value("task.terminal", "task-9") != "failed":
            return fail("DSM terminal value overwritten by later event")
        return ok({"journal_retained": "FAILED", "dsm_retained": "failed",
                   "second_finish": "JournalError", "second_submit": "ContractError"})


# ---------------------------------------------------------------- G1V-17
def g1v17_projection_reconstruction() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        journal, c1 = claim(tmp, "v17-a", generation=1)
        journal.finish(c1, "FAILED")
        del journal  # writer restart
        journal2 = new_journal(tmp)  # same trace_id; constructor chain check
        rows = [a for a in journal2.attempts() if a["attempt_id"] == c1.attempt_id]
        if len(rows) != 1 or rows[0]["state"] != "FAILED":
            return fail("terminal state not reconstructed after restart", {"rows": rows})
        c2 = make_contract(tmp, "v17-b", generation=1)
        try:
            journal2.claim(c2, source_hash="0" * 64, approval={})
        except JournalError as exc:
            if "lease generation must increase" not in str(exc):
                return fail(f"unexpected message: {exc}")
        else:
            return fail("stale-generation retry accepted after restart")
        c3 = make_contract(tmp, "v17-b", generation=2)
        journal2.claim(c3, source_hash="0" * 64, approval={})  # fresh lease: accepted
        try:
            new_journal(tmp, trace_id="trace-foreign")
        except JournalError as exc:
            if "belongs to another run" not in str(exc):
                return fail(f"unexpected foreign-open message: {exc}")
        else:
            return fail("journal opened by a foreign run (RESTART:refused expected)")
        return ok({"state_retained": "FAILED", "retry_gen1": "JournalError",
                   "fresh_gen2": "accepted", "foreign_trace_id": "JournalError"})


EXECUTORS = {
    "g1v01_stale_generation_claim": g1v01_stale_generation_claim,
    "g1v02_claim_while_active": g1v02_claim_while_active,
    "g1v03_identity_uniqueness": g1v03_identity_uniqueness,
    "g1v04_started_after_revoke": g1v04_started_after_revoke,
    "g1v05_dsm_commit_before_ack": g1v05_dsm_commit_before_ack,
    "g1v06_sqlite_commit_kill": g1v06_sqlite_commit_kill,
    "g1v07_concurrent_finish": g1v07_concurrent_finish,
    "g1v08_revoke_vs_finish": g1v08_revoke_vs_finish,
    "g1v09_stale_lease": g1v09_stale_lease,
    "g1v10_duplicate_delivery": g1v10_duplicate_delivery,
    "g1v11_writer_restart_outbox": g1v11_writer_restart_outbox,
    "g1v12_scheduler_unavailable_recovery": g1v12_scheduler_unavailable_recovery,
    "g1v13_lease_read_tristate": g1v13_lease_read_tristate,
    "g1v15_mark_purged_active": g1v15_mark_purged_active,
    "g1v16_first_failure_retention": g1v16_first_failure_retention,
    "g1v17_projection_reconstruction": g1v17_projection_reconstruction,
}


def run(base_sha: str | None = None, only: set[str] | None = None) -> dict:
    corpus = json.loads(CORPUS.read_text())
    results = []
    counts = {"PASS": 0, "FAIL": 0, "UNKNOWN": 0, "BLOCKED": 0}
    for vector in corpus["vectors"]:
        vid = vector["id"]
        if only and vid not in only:
            continue
        execution = vector.get("execution", {})
        binding = execution.get("binding")
        entry = {"id": vid, "title": vector["title"], "category": vector["category"],
                 "normative_reference": vector["normative_reference"],
                 "execution_status": execution.get("status")}
        if execution.get("status") != "executable" or binding not in EXECUTORS:
            # No current implementation binding: expected-unknown, NEVER pass.
            entry["status"] = "UNKNOWN"
            entry["detail"] = {"reason": execution.get(
                "pending_reason", "no current implementation binding")}
            counts["UNKNOWN"] += 1
            results.append(entry)
            continue
        started = time.monotonic()
        try:
            outcome = EXECUTORS[binding]()
        except Exception as exc:  # harness defect: BLOCKED, never PASS
            outcome = {"status": "BLOCKED",
                       "detail": {"reason": f"executor raised {type(exc).__name__}: {exc}"}}
        entry["status"] = outcome["status"]
        entry["detail"] = outcome.get("detail", {})
        entry["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        counts[entry["status"]] += 1
        results.append(entry)
    counts["pending_implementation"] = sum(
        1 for r in results if r["execution_status"] == "pending_implementation")
    counts["executable"] = sum(1 for r in results if r["execution_status"] == "executable")
    return {"suite": corpus["suite"], "corpus_version": corpus["version"],
            "base_sha": base_sha or corpus.get("base_sha"),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "counts": counts, "results": results}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", help="write machine-readable JSON report to PATH")
    parser.add_argument("--vector", action="append", help="run only the given vector id(s)")
    args = parser.parse_args(argv)
    report = run(only=set(args.vector) if args.vector else None)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.report:
        Path(args.report).write_text(text + "\n")
    print(text)
    return 1 if report["counts"]["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
