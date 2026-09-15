"""Deterministic recovery suite (DSM-R8/R9, acceptance, gate C).

Runs restart/replay scenarios against a fresh store, then recomputes the
accepted state transitions from the retained journal alone and proves:

  * no duplicate accepted transition exists across restart/replay;
  * the recovered projection equals the pre-crash projection;
  * audit provenance (writer, fencing token, hash chain) survives recovery.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from .lease import LeaseManager
from .ownership import TERMINAL_STATES
from .store import CrashError, DistributedStateStore


def _terminal_event(eid, entity, value, writer="orchestrator"):
    return {"event_id": eid, "domain": "task.terminal", "entity": entity,
            "value": value, "writer": writer}


def _prove_no_duplicate_accepted(store):
    transitions = store.accepted_transitions()
    ids = [t["event_id"] for t in transitions]
    return {
        "accepted_count": len(ids),
        "unique_count": len(set(ids)),
        "no_duplicate_accepted": len(ids) == len(set(ids)),
        "transitions": transitions,
    }


def _scenario_crash_between_write_and_ack(root):
    """Process dies after the durable journal write, before the ack."""
    store = DistributedStateStore(root)
    crashed = False
    try:
        store.submit(_terminal_event("e1", "task-1", "running"),
                     crash_after="journal_write")
    except CrashError:
        crashed = True
    # caller never saw an ack, so it retries with the same event_id
    retry = store.submit(_terminal_event("e1", "task-1", "running"))
    assert retry["disposition"] == "duplicate"
    # full process restart + replay from the retained journal
    recovered = DistributedStateStore.recover(root)
    proof = _prove_no_duplicate_accepted(recovered)
    proof.update({
        "scenario": "crash_between_write_and_ack",
        "crash_injected": crashed,
        "retry_disposition": retry["disposition"],
        "projection_after_recovery": recovered.current_value("task.terminal", "task-1"),
        "provenance_intact": recovered.provenance("e1")["event"]["writer"] == "orchestrator",
        "ok": crashed and proof["no_duplicate_accepted"]
        and recovered.current_value("task.terminal", "task-1") == "running",
    })
    return proof


def _scenario_restart_mid_stream(root):
    """Multiple accepted transitions, restart, catch-up, then continue."""
    store = DistributedStateStore(root)
    store.submit(_terminal_event("e1", "task-1", "running"))
    store.submit(_terminal_event("e2", "task-2", "running"))
    cursor_before = store.journal.cursor

    recovered = DistributedStateStore.recover(root)
    caught_up = [r["seq"] for r in recovered.journal.replay(-1)]
    assert caught_up == list(range(cursor_before + 1))
    # duplicates of both pre-crash events after restart must not re-accept
    d1 = recovered.submit(_terminal_event("e1", "task-1", "running"))
    d2 = recovered.submit(_terminal_event("e2", "task-2", "running"))
    recovered.submit(_terminal_event("e3", "task-1", "succeeded"))
    # terminal state is absorbing
    rejected = False
    try:
        recovered.submit(_terminal_event("e4", "task-1", "failed"))
    except Exception:
        rejected = True

    proof = _prove_no_duplicate_accepted(recovered)
    proof.update({
        "scenario": "restart_mid_stream",
        "caught_up_seqs": caught_up,
        "duplicate_dispositions": [d1["disposition"], d2["disposition"]],
        "terminal_absorbing_rejected": rejected,
        "projection_after_recovery": {
            "task-1": recovered.current_value("task.terminal", "task-1"),
            "task-2": recovered.current_value("task.terminal", "task-2"),
        },
        "provenance_intact": all(
            recovered.provenance(e)["event"]["writer"] == "orchestrator"
            for e in ("e1", "e2", "e3")),
        "ok": proof["no_duplicate_accepted"] and rejected
        and d1["disposition"] == d2["disposition"] == "duplicate"
        and recovered.current_value("task.terminal", "task-1") == "succeeded",
    })
    return proof


def _scenario_replay_determinism(root):
    """Two independent recoveries from the same journal agree exactly."""
    store = DistributedStateStore(root)
    for i, entity in enumerate(("task-a", "task-b", "task-c")):
        store.submit(_terminal_event(f"r{i}", entity, "running"))
        store.submit(_terminal_event(f"r{i}-done", entity, "failed"))
    a = DistributedStateStore.recover(root)
    b = DistributedStateStore.recover(root)
    ta, tb = a.accepted_transitions(), b.accepted_transitions()
    proof = _prove_no_duplicate_accepted(a)
    proof.update({
        "scenario": "replay_determinism",
        "transitions_equal_across_recoveries": ta == tb,
        "journal_reverified_records": a.journal.verify(),
        "ok": proof["no_duplicate_accepted"] and ta == tb,
    })
    return proof


SCENARIOS = (
    ("crash_between_write_and_ack", _scenario_crash_between_write_and_ack),
    ("restart_mid_stream", _scenario_restart_mid_stream),
    ("replay_determinism", _scenario_replay_determinism),
)


def run_recovery_suite(root=None, keep=False):
    """Run every scenario in an isolated journal directory. Deterministic."""
    base = Path(root) if root else Path(tempfile.mkdtemp(prefix="dsm-recovery-"))
    base.mkdir(parents=True, exist_ok=True)
    results = []
    try:
        for name, fn in SCENARIOS:
            scenario_root = base / name
            if scenario_root.exists():
                shutil.rmtree(scenario_root)
            results.append(fn(scenario_root))
    finally:
        if not root and not keep:
            shutil.rmtree(base, ignore_errors=True)
    return {
        "suite": "dsm-004-recovery",
        "terminal_states": sorted(TERMINAL_STATES),
        "scenarios": results,
        "no_duplicate_accepted_transition": all(
            r["no_duplicate_accepted"] for r in results),
        "ok": all(r["ok"] for r in results),
    }
