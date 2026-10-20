"""MS-00 run ledger — contract-test skeletons (G0/G1 design lane).

These tests encode the normative semantics of docs/architecture/MS-00-run-ledger.md:
I-1 exactly-one-terminal (CAS + storage uniqueness, never a watchdog), I-2 state+event
atomicity, I-3 projection reconstruction, I-4 idempotent admission, I-6 fail-closed
integrity, MS-08 fencing, and the crash matrix KP rows (§7).

They run green against the minimal reference implementation
(``docs/architecture/ms00/reference_ledger.py``). Binding to the future production
MS-00 implementation requires changing ONLY the ``ledger_factory`` fixture.

UNKNOWN/BLOCKED outcomes are never asserted as PASS; crash-window tests assert
post-recovery durable truth, not the crashed caller's view.
"""
from __future__ import annotations

import hashlib
import multiprocessing
import os
import sqlite3
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reference_ledger import (  # noqa: E402
    FencingError,
    JournalError,
    ReferenceLedger,
    TERMINAL_STATES,
    new_attempt_params,
)

PLAN = hashlib.sha256(b"plan").hexdigest()
WRITER = "writer-0"


@pytest.fixture
def ledger_factory(tmp_path):
    """Single binding point for the future production MS-00 implementation."""
    counter = {"n": 0}

    def make(name="ledger.sqlite3", *, control_plane_id="cp-0"):
        counter["n"] += 1
        return ReferenceLedger(tmp_path / name, control_plane_id=control_plane_id)

    return make


@pytest.fixture
def ledger(ledger_factory):
    lg = ledger_factory()
    lg.acquire_writer_lease(WRITER)
    return lg


def _token(ledger):
    row = ledger._read_one(
        "SELECT fencing_token FROM lease_generations"
        " WHERE plan_hash='__control__' AND task_id='writer'", ())
    return row[0]


def _claim(ledger, task_id="task-1", generation=1, prefix="t", token=None):
    params = new_attempt_params(prefix, PLAN, task_id, generation,
                                token if token is not None else _token(ledger),
                                writer=WRITER)
    ack = ledger.claim(**params)
    return params, ack


# --- I-1 exactly-one-terminal ---------------------------------------------

def test_second_terminal_is_rejected_by_storage(ledger):
    """KP row: second terminal write impossible (terminal_state IS NULL CAS)."""
    params, _ = _claim(ledger)
    tok = _token(ledger)
    ledger.started(params["attempt_id"], 1234, fencing_token=tok,
                   event_id=params["event_id"] + ":start", writer=WRITER)
    ack = ledger.finish(params["attempt_id"], "FAILED", fencing_token=tok,
                        event_id=params["event_id"] + ":fin1", writer=WRITER)
    assert ack.disposition == "accepted"
    with pytest.raises(JournalError):
        ledger.finish(params["attempt_id"], "VIOLATED", fencing_token=tok,
                      event_id=params["event_id"] + ":fin2", writer=WRITER)
    state, terminal, _ = ledger.attempt_state(params["attempt_id"])
    assert (state, terminal) == ("FAILED", "FAILED")
    finished = [e for e in ledger.events()
                if e["payload"].get("event") == "RuntimeAttemptFinished"]
    assert len(finished) == 1


def test_double_finish_race_exactly_one_winner(ledger):
    """KP-07: concurrent terminal writes; exactly one wins; never watchdog-mediated."""
    params, _ = _claim(ledger)
    tok = _token(ledger)
    ledger.started(params["attempt_id"], 1234, fencing_token=tok,
                   event_id=params["event_id"] + ":start", writer=WRITER)
    outcomes = []
    for interleaving in range(20):
        results = {}

        def fin(state):
            try:
                ledger.finish(params["attempt_id"], state, fencing_token=tok,
                              event_id=f"{params['event_id']}:race{interleaving}:{state}",
                              writer=WRITER)
                results[state] = "accepted"
            except JournalError:
                results[state] = "rejected"

        t1 = threading.Thread(target=fin, args=("FAILED",))
        t2 = threading.Thread(target=fin, args=("VIOLATED",))
        t1.start(); t2.start(); t1.join(); t2.join()
        outcomes.append(results)
        # reset for next interleaving via a fresh attempt
        if interleaving < 19:
            params, _ = _claim(ledger, task_id=f"task-r{interleaving}", prefix="r")
            ledger.started(params["attempt_id"], 1234, fencing_token=tok,
                           event_id=params["event_id"] + ":start", writer=WRITER)
    for results in outcomes:
        assert sorted(results.values()) == ["accepted", "rejected"]


def test_revoked_attempt_cannot_produce_candidate(ledger):
    """KP-08 ordered leg: revoke first ⇒ CANDIDATE rejected."""
    params, _ = _claim(ledger)
    tok = _token(ledger)
    ledger.started(params["attempt_id"], 1234, fencing_token=tok,
                   event_id=params["event_id"] + ":start", writer=WRITER)
    ledger.revoke(params["attempt_id"], fencing_token=tok,
                  event_id=params["event_id"] + ":rev", writer=WRITER)
    with pytest.raises(JournalError):
        ledger.finish(params["attempt_id"], "CANDIDATE", fencing_token=tok,
                      event_id=params["event_id"] + ":fin", writer=WRITER)
    state, terminal, revoked = ledger.attempt_state(params["attempt_id"])
    assert terminal is None and revoked == 1 and state == "RUNNING"


def test_terminal_first_then_revoke_rejected(ledger):
    """KP-08 ordered leg: finish first ⇒ revoke rejected; terminal absorbing."""
    params, _ = _claim(ledger)
    tok = _token(ledger)
    ledger.started(params["attempt_id"], 99, fencing_token=tok,
                   event_id=params["event_id"] + ":start", writer=WRITER)
    ledger.finish(params["attempt_id"], "FAILED", fencing_token=tok,
                  event_id=params["event_id"] + ":fin", writer=WRITER)
    with pytest.raises(JournalError):
        ledger.revoke(params["attempt_id"], fencing_token=tok,
                      event_id=params["event_id"] + ":rev", writer=WRITER)


# --- claim-time CAS (KP-01..04) ---------------------------------------------

def test_stale_generation_claim_rejected(ledger):
    """KP-01: generation CAS fail-closed; zero rows and zero events added."""
    _claim(ledger, task_id="task-g", generation=2, prefix="g")
    tok = _token(ledger)
    before = len(ledger.events())
    params = new_attempt_params("g2", PLAN, "task-g", 2, tok, writer=WRITER)
    with pytest.raises(JournalError):
        ledger.claim(**params)
    assert len(ledger.events()) == before
    assert all(a["task_id"] != "task-g" or a["generation"] == 2
               for a in ledger.attempts())


def test_claim_while_active_rejected(ledger):
    """KP-02: one non-terminal attempt per (plan_hash, task_id)."""
    _claim(ledger, task_id="task-a", generation=1, prefix="a1")
    params = new_attempt_params("a2", PLAN, "task-a", 2, _token(ledger), writer=WRITER)
    with pytest.raises(JournalError):
        ledger.claim(**params)


def test_duplicate_identity_rejected(ledger):
    """KP-03: storage uniqueness on worker_id/lease_id/workspace."""
    p1, _ = _claim(ledger, task_id="task-i1", generation=1, prefix="i1")
    for field in ("worker_id", "lease_id", "workspace"):
        p2 = new_attempt_params("i2", PLAN, "task-i2", 1, _token(ledger), writer=WRITER)
        p2[field] = p1[field]
        with pytest.raises(JournalError):
            ledger.claim(**p2)


def test_started_requires_reserved_and_not_revoked(ledger):
    """KP-04: started() CAS rowcount contract."""
    params, _ = _claim(ledger, task_id="task-s", prefix="s")
    tok = _token(ledger)
    ledger.started(params["attempt_id"], 1, fencing_token=tok,
                   event_id=params["event_id"] + ":s1", writer=WRITER)
    with pytest.raises(JournalError):  # second started
        ledger.started(params["attempt_id"], 2, fencing_token=tok,
                       event_id=params["event_id"] + ":s2", writer=WRITER)
    params2, _ = _claim(ledger, task_id="task-s2", prefix="s2")
    ledger.revoke(params2["attempt_id"], fencing_token=tok,
                  event_id=params2["event_id"] + ":rev", writer=WRITER)
    with pytest.raises(JournalError):  # revoked attempt
        ledger.started(params2["attempt_id"], 3, fencing_token=tok,
                       event_id=params2["event_id"] + ":s1", writer=WRITER)


# --- I-4 idempotent admission -----------------------------------------------

def test_duplicate_event_id_returns_duplicate_disposition(ledger):
    """KP-05 replay leg: retry after ambiguous commit dedupes with same (seq, hash)."""
    params, _ = _claim(ledger)
    tok = _token(ledger)
    ledger.started(params["attempt_id"], 7, fencing_token=tok,
                   event_id=params["event_id"] + ":start", writer=WRITER)
    first = ledger.finish(params["attempt_id"], "FAILED", fencing_token=tok,
                          event_id=params["event_id"] + ":fin", writer=WRITER)
    # Same event_id, same state: idempotent replay (client retry after crash).
    second = ledger.finish(params["attempt_id"], "FAILED", fencing_token=tok,
                           event_id=params["event_id"] + ":fin", writer=WRITER)
    assert second.disposition == "duplicate"
    assert (second.seq, second.hash) == (first.seq, first.hash)


# --- MS-08 fencing -------------------------------------------------------------

def test_stale_fencing_token_rejected(ledger):
    """A new writer's token fences the stale writer out of terminal writes."""
    params, _ = _claim(ledger, task_id="task-f", prefix="f")
    stale = _token(ledger)
    ledger.acquire_writer_lease("writer-1")  # token bump fences `stale`
    fresh = _token(ledger)
    assert fresh > stale
    ledger.started(params["attempt_id"], 5, fencing_token=fresh,
                   event_id=params["event_id"] + ":start", writer="writer-1")
    with pytest.raises(FencingError):
        ledger.finish(params["attempt_id"], "FAILED", fencing_token=stale,
                      event_id=params["event_id"] + ":fin", writer=WRITER)
    assert ledger.attempt_state(params["attempt_id"])[1] is None


# --- crash window (KP-06) -------------------------------------------------------

def _child_finish(path, aid, token, event_id, queue):
    import sys as _s
    _s.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from reference_ledger import ReferenceLedger
    lg = ReferenceLedger(path, control_plane_id="cp-0")
    lg.finish(aid, "FAILED", fencing_token=token, event_id=event_id, writer=WRITER)
    os._exit(0)  # simulate death immediately after COMMIT returns (no cleanup)


def test_crash_between_commit_and_ack(tmp_path, ledger_factory):
    """KP-06: SIGKILL-class death after COMMIT, before caller ack.

    Post-recovery durable truth: exactly one terminal event; re-finish rejected;
    chain verifies. The crashed caller's view is never consulted.
    """
    lg = ledger_factory()
    lg.acquire_writer_lease(WRITER)
    params, _ = _claim(lg, task_id="task-c", prefix="c")
    tok = _token(lg)
    lg.started(params["attempt_id"], 4242, fencing_token=tok,
               event_id=params["event_id"] + ":start", writer=WRITER)
    ctx = multiprocessing.get_context("fork")
    q = ctx.Queue()
    proc = ctx.Process(target=_child_finish,
                       args=(str(lg.path), params["attempt_id"], tok,
                             params["event_id"] + ":fin", q))
    proc.start()
    proc.join(30)
    assert proc.exitcode == 0  # child committed then died without acking caller
    reopened = ledger_factory(name="ledger.sqlite3")  # same file, new instance
    reopened.verify_chain()  # I-6: reopen succeeds on intact chain
    state, terminal, _ = reopened.attempt_state(params["attempt_id"])
    assert (state, terminal) == ("FAILED", "FAILED")
    finished = [e for e in reopened.events()
                if e["payload"].get("event") == "RuntimeAttemptFinished"]
    assert len(finished) == 1
    with pytest.raises(JournalError):
        reopened.finish(params["attempt_id"], "VIOLATED", fencing_token=tok,
                        event_id=params["event_id"] + ":fin2", writer=WRITER)


# --- I-2 state+event atomicity ---------------------------------------------------

def test_event_append_failure_rolls_back_state(ledger, monkeypatch):
    """KP-16: failure between CAS and append rolls back the whole transaction."""
    params, _ = _claim(ledger, task_id="task-x", prefix="x")
    tok = _token(ledger)

    def boom(db, event_id, writer, token, payload):
        raise RuntimeError("injected append failure")

    monkeypatch.setattr(ledger, "_append", boom)
    with pytest.raises(RuntimeError):
        ledger.finish(params["attempt_id"], "FAILED", fencing_token=tok,
                      event_id=params["event_id"] + ":fin", writer=WRITER)
    state, terminal, _ = ledger.attempt_state(params["attempt_id"])
    assert (state, terminal) == ("RESERVED", None)  # nothing committed
    monkeypatch.undo()
    ledger.finish(params["attempt_id"], "FAILED", fencing_token=tok,
                  event_id=params["event_id"] + ":fin", writer=WRITER)


# --- I-6 fail-closed integrity (KP-17) --------------------------------------------

def test_hash_chain_tamper_refuses_reopen(tmp_path, ledger_factory):
    lg = ledger_factory()
    lg.acquire_writer_lease(WRITER)
    _claim(lg, task_id="task-t", prefix="t")
    # out-of-band tamper beneath SQL (simulates disk-level corruption): the
    # append-only trigger is removed first because corruption is not a writer.
    db = sqlite3.connect(lg.path, isolation_level=None)
    db.execute("DROP TRIGGER immutable_event_update")
    db.execute("UPDATE events SET record = replace(record, 'attempt', 'attempX')"
               " WHERE seq = 1")
    db.close()
    with pytest.raises(JournalError):
        ledger_factory(name="ledger.sqlite3")


def test_control_plane_mismatch_refused(tmp_path, ledger_factory):
    ledger_factory()
    with pytest.raises(JournalError):
        ledger_factory(name="ledger.sqlite3", control_plane_id="cp-other")


# --- reconciliation (§8; KP-12/KP-18 attempt-side) ---------------------------------

def test_reconcile_orphans_to_failed_and_is_idempotent(tmp_path, ledger_factory):
    """Interrupted attempts become truthful terminal FAILED; re-run is a no-op."""
    lg = ledger_factory()
    lg.acquire_writer_lease(WRITER)
    p1, _ = _claim(lg, task_id="task-o1", prefix="o1")
    p2, _ = _claim(lg, task_id="task-o2", prefix="o2")
    tok = _token(lg)
    lg.finish(p2["attempt_id"], "VIOLATED", fencing_token=tok,
              event_id=p2["event_id"] + ":fin", writer=WRITER)

    class RestartedWriter:
        pass

    # Simulate writer restart: new process identity takes the write lease.
    new_token = lg.acquire_writer_lease("writer-restart")
    report1 = lg.reconcile(writer_id="writer-restart", fencing_token=new_token,
                           event_id="reconcile-1")
    assert report1["orphaned_attempts"] == 1
    assert lg.attempt_state(p1["attempt_id"])[:2] == ("FAILED", "FAILED")
    assert lg.attempt_state(p2["attempt_id"])[:2] == ("VIOLATED", "VIOLATED")  # untouched
    report2 = lg.reconcile(writer_id="writer-restart", fencing_token=new_token,
                           event_id="reconcile-1")
    assert report2["orphaned_attempts"] == 0
    assert (report2["seq"], report2["hash"]) == (report1["seq"], report1["hash"])


def test_projection_reconstruction_matches_tables(ledger):
    """I-3: projection rebuilt from events alone agrees with attempts table."""
    p1, _ = _claim(ledger, task_id="task-p1", prefix="p1")
    p2, _ = _claim(ledger, task_id="task-p2", prefix="p2")
    tok = _token(ledger)
    ledger.started(p1["attempt_id"], 11, fencing_token=tok,
                   event_id=p1["event_id"] + ":start", writer=WRITER)
    ledger.finish(p1["attempt_id"], "FAILED", fencing_token=tok,
                  event_id=p1["event_id"] + ":fin", writer=WRITER)
    projected = ledger.project_attempt_states()
    for a in ledger.attempts():
        assert projected[a["attempt_id"]] == a["state"]


def test_reconcile_respects_stale_fencing(ledger):
    """Reconciliation from a fenced-off writer is rejected, not silently applied."""
    _claim(ledger, task_id="task-rs", prefix="rs")
    stale = _token(ledger)
    ledger.acquire_writer_lease("writer-new")
    with pytest.raises(FencingError):
        ledger.reconcile(writer_id=WRITER, fencing_token=stale)
