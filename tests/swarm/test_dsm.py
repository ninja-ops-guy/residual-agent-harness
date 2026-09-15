"""SPEC-SWARM-DSM-004 — Distributed State Maturity.

Requirement -> test traceability (mirrors docs/swarm/dsm-004.md):

  R1  authoritative ownership     test_r1_*
  R2  durable acknowledgements    test_r2_*
  R3  reconnect/catch-up          test_r3_*
  R4  idempotent duplicates       test_r4_*
  R5  fencing tokens fail closed  test_r5_*
  R6  deterministic conflicts     test_r6_*
  R7  consensus boundary          test_r7_*
  R8  crash/restart/replay        test_r8_*
  R9  audit provenance            test_r9_*
  R10 fault matrix                test_r10_*
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from residual.core import ContractError
from residual.dsm import (
    CrashError, DistributedStateStore, Fault, FaultSchedule, FencingError,
    Inbox, Journal, LeaseManager, Outbox, OwnershipRegistry, owner_of,
    run_recovery_suite, simulate,
)
from residual.dsm.evidence import generate_evidence, run_fault_matrix
from residual.dsm.ownership import DOMAINS


def terminal(eid, entity, value, writer="orchestrator"):
    return {"event_id": eid, "domain": "task.terminal", "entity": entity,
            "value": value, "writer": writer}


def receipt(eid, entity, value, writer="verifier"):
    return {"event_id": eid, "domain": "receipt.publication", "entity": entity,
            "value": value, "writer": writer}


# ---------------------------------------------------------------- DSM-R1
def test_r1_ownership_domains_are_defined():
    assert set(DOMAINS) == {"task.lease", "receipt.publication",
                            "integration.intent", "task.terminal"}
    for domain in DOMAINS:
        assert owner_of(domain) == DOMAINS[domain]


def test_r1_non_authoritative_writer_rejected(tmp_path):
    store = DistributedStateStore(tmp_path)
    with pytest.raises(ContractError):
        store.submit(terminal("x1", "t1", "running", writer="worker-7"))
    with pytest.raises(ContractError):
        store.submit(receipt("x2", "t1", {"ok": True}, writer="orchestrator"))
    assert store.accepted_transitions() == []


def test_r1_authoritative_writer_accepted_per_domain(tmp_path):
    store = DistributedStateStore(tmp_path)
    leases = store.leases
    lease = leases.acquire("t1", "sched-1", ttl_ms=1000, now_ms=0)
    assert store.submit({"event_id": "l1", "domain": "task.lease", "entity": "t1",
                         "value": "sched-1", "writer": "scheduler",
                         "writer_holder": "sched-1",
                         "fencing_token": lease["fencing_token"],
                         "now_ms": 1})["disposition"] == "accepted"
    assert store.submit(receipt("r1", "t1", {"ok": True}))["disposition"] == "accepted"
    assert store.submit({"event_id": "i1", "domain": "integration.intent",
                         "entity": "t1", "value": "merge", "writer": "integrator"}
                        )["disposition"] == "accepted"
    assert store.submit(terminal("t1", "t1", "running"))["disposition"] == "accepted"
    with pytest.raises(ContractError):
        OwnershipRegistry().owner_of("nonexistent.domain")


# ---------------------------------------------------------------- DSM-R2
def test_r2_ack_is_durable_and_gates_delivery(tmp_path):
    outbox = Outbox(tmp_path / "out.journal")
    event = receipt("e1", "t1", {"ok": True})
    outbox.publish(event)
    assert outbox.pending() == [event]          # not acked -> still pending
    outbox.ack("e1")
    assert outbox.pending() == []
    # restart: ack state survives
    outbox2 = Outbox(tmp_path / "out.journal")
    assert outbox2.pending() == []
    assert outbox2.acks.is_acked("e1")


def test_r2_unacked_message_resent_after_reconnect(tmp_path):
    outbox = Outbox(tmp_path / "out.journal")
    for i in range(3):
        outbox.publish(receipt(f"e{i}", "t", {"seq": i}))
    outbox.ack("e0")
    # simulate process restart before e1/e2 acks arrived
    outbox = Outbox(tmp_path / "out.journal")
    assert [e["event_id"] for e in outbox.pending()] == ["e1", "e2"]


# ---------------------------------------------------------------- DSM-R3
def test_r3_catchup_from_monotonic_cursor(tmp_path):
    journal = Journal(tmp_path / "j.journal")
    for i in range(5):
        journal.append("transition", {"i": i})
    assert journal.cursor == 4
    assert [r["seq"] for r in journal.replay(2)] == [3, 4]
    assert [r["seq"] for r in journal.replay(-1)] == [0, 1, 2, 3, 4]


def test_r3_catchup_across_reopen(tmp_path):
    journal = Journal(tmp_path / "j.journal")
    journal.append("transition", {"i": 0})
    journal.append("transition", {"i": 1})
    reopened = Journal(tmp_path / "j.journal")
    assert reopened.cursor == 1
    assert reopened.verify() == 2
    assert [r["payload"]["i"] for r in reopened.replay(0)] == [1]


# ---------------------------------------------------------------- DSM-R4
def test_r4_duplicate_submit_is_idempotent(tmp_path):
    store = DistributedStateStore(tmp_path)
    first = store.submit(terminal("e1", "t1", "running"))
    second = store.submit(terminal("e1", "t1", "running"))
    assert first["disposition"] == "accepted"
    assert second["disposition"] == "duplicate" and second["seq"] == first["seq"]
    assert len(store.accepted_transitions()) == 1


def test_r4_duplicate_inbox_delivery_idempotent_across_restart(tmp_path):
    inbox = Inbox(tmp_path / "in.journal")
    event = receipt("e1", "t1", {"ok": True})
    assert inbox.deliver(event) == "accepted"
    assert inbox.deliver(event) == "duplicate"
    inbox2 = Inbox(tmp_path / "in.journal")
    assert inbox2.deliver(event) == "duplicate"


def test_r4_duplicate_survives_store_recovery(tmp_path):
    store = DistributedStateStore(tmp_path)
    store.submit(terminal("e1", "t1", "running"))
    recovered = DistributedStateStore.recover(tmp_path)
    assert recovered.submit(terminal("e1", "t1", "running"))["disposition"] == "duplicate"
    assert len(recovered.accepted_transitions()) == 1


# ---------------------------------------------------------------- DSM-R5
def test_r5_stale_fencing_token_fails_closed(tmp_path):
    leases = LeaseManager()
    first = leases.acquire("task-1", "worker-a", ttl_ms=1000, now_ms=0)
    second = leases.acquire("task-1", "worker-b", ttl_ms=1000, now_ms=1100)
    assert second["fencing_token"] > first["fencing_token"]
    store = DistributedStateStore(tmp_path, leases=leases)
    stale = {"event_id": "w1", "domain": "task.lease", "entity": "task-1",
             "value": "worker-a", "writer": "scheduler", "writer_holder": "worker-a",
             "fencing_token": first["fencing_token"], "now_ms": 1200}
    with pytest.raises(FencingError):
        store.submit(stale)
    assert store.accepted_transitions() == []


def test_r5_expired_and_foreign_tokens_fail_closed():
    leases = LeaseManager()
    lease = leases.acquire("r", "a", ttl_ms=100, now_ms=0)
    with pytest.raises(FencingError):
        leases.check("r", "a", lease["fencing_token"], now_ms=101)   # expired
    with pytest.raises(FencingError):
        leases.check("r", "b", lease["fencing_token"], now_ms=1)     # foreign holder
    with pytest.raises(FencingError):
        leases.check("r", "a", lease["fencing_token"] - 1, now_ms=1)  # stale token
    with pytest.raises(FencingError):
        leases.acquire("r", "b", ttl_ms=10, now_ms=1)                 # contended
    assert leases.check("r", "a", lease["fencing_token"], now_ms=1)


def test_r5_current_holder_write_accepted(tmp_path):
    leases = LeaseManager()
    lease = leases.acquire("task-1", "worker-a", ttl_ms=1000, now_ms=0)
    store = DistributedStateStore(tmp_path, leases=leases)
    result = store.submit({"event_id": "w1", "domain": "task.lease",
                           "entity": "task-1", "value": "worker-a",
                           "writer": "scheduler", "writer_holder": "worker-a",
                           "fencing_token": lease["fencing_token"], "now_ms": 5})
    assert result["disposition"] == "accepted"


# ---------------------------------------------------------------- DSM-R6
def test_r6_concurrent_writers_deterministic_winner(tmp_path):
    store = DistributedStateStore(tmp_path)
    # two authoritative receipts race for the same entity
    store.submit(receipt("b-evt", "t1", {"ok": False}, writer="verifier"))
    store.submit(receipt("a-evt", "t1", {"ok": True}, writer="verifier"))
    live = store.current_value("receipt.publication", "t1")
    # winner is argmax(fencing, writer, event_id) -> "b-evt" > "a-evt"
    assert live == {"ok": False}
    # replay from the journal converges to the identical winner
    recovered = DistributedStateStore.recover(tmp_path)
    assert recovered.current_value("receipt.publication", "t1") == live


def test_r6_journal_order_is_total_and_replay_stable(tmp_path):
    store = DistributedStateStore(tmp_path)
    for i in range(10):
        store.submit(receipt(f"e{i:02d}", f"t{i % 3}", {"seq": i}))
    a = DistributedStateStore.recover(tmp_path).accepted_transitions()
    b = DistributedStateStore.recover(tmp_path).accepted_transitions()
    assert a == b == store.accepted_transitions()
    assert [t["seq"] for t in a] == sorted(t["seq"] for t in a)


def test_r6_terminal_states_are_absorbing(tmp_path):
    store = DistributedStateStore(tmp_path)
    store.submit(terminal("e1", "t1", "running"))
    store.submit(terminal("e2", "t1", "succeeded"))
    for value in ("running", "failed", "rejected", "unknown"):
        with pytest.raises(ContractError):
            store.submit(terminal(f"e-{value}", "t1", value))
    assert store.current_value("task.terminal", "t1") == "succeeded"


# ---------------------------------------------------------------- DSM-R7
def test_r7_consensus_boundary_documented():
    doc = (Path(__file__).resolve().parents[2] / "docs" / "swarm" / "dsm-004.md")
    text = doc.read_text(encoding="utf-8").lower()
    assert "without consensus" in text
    assert "require consensus" in text or "requires a consensus" in text
    for term in ("split-brain", "fencing", "linearizab"):
        assert term in text


# ---------------------------------------------------------------- DSM-R8
def test_r8_crash_between_write_and_ack_no_duplicate(tmp_path):
    store = DistributedStateStore(tmp_path)
    with pytest.raises(CrashError):
        store.submit(terminal("e1", "t1", "running"), crash_after="journal_write")
    # the write is durable even though the caller never saw an ack
    assert len(list(Journal(tmp_path / "dsm.journal").replay(-1))) == 1
    retry = store.submit(terminal("e1", "t1", "running"))
    assert retry["disposition"] == "duplicate"
    recovered = DistributedStateStore.recover(tmp_path)
    assert len(recovered.accepted_transitions()) == 1
    assert recovered.current_value("task.terminal", "t1") == "running"


def test_r8_recovery_suite_all_scenarios(tmp_path):
    result = run_recovery_suite(tmp_path / "suite", keep=True)
    assert result["ok"]
    assert result["no_duplicate_accepted_transition"]
    assert {s["scenario"] for s in result["scenarios"]} == {
        "crash_between_write_and_ack", "restart_mid_stream", "replay_determinism"}
    for scenario in result["scenarios"]:
        ids = [t["event_id"] for t in scenario["transitions"]]
        assert len(ids) == len(set(ids)), scenario["scenario"]


def test_r8_journal_integrity_verified_after_replay(tmp_path):
    store = DistributedStateStore(tmp_path)
    for i in range(4):
        store.submit(receipt(f"e{i}", f"t{i}", {"i": i}))
    assert Journal(tmp_path / "dsm.journal").verify() == 4
    # corrupt the journal -> verification fails closed
    lines = (tmp_path / "dsm.journal").read_text().splitlines()
    record = json.loads(lines[2])
    record["payload"]["event"]["value"] = {"tampered": True}
    lines[2] = json.dumps(record)
    (tmp_path / "dsm.journal").write_text("\n".join(lines) + "\n")
    with pytest.raises(Exception):
        Journal(tmp_path / "dsm.journal")


# ---------------------------------------------------------------- DSM-R9
def test_r9_provenance_preserved_across_recovery(tmp_path):
    store = DistributedStateStore(tmp_path)
    leases = store.leases
    lease = leases.acquire("t1", "w1", ttl_ms=1000, now_ms=0)
    store.submit({"event_id": "l1", "domain": "task.lease", "entity": "t1",
                  "value": "w1", "writer": "scheduler", "writer_holder": "w1",
                  "fencing_token": lease["fencing_token"], "now_ms": 1})
    before = store.provenance("l1")
    recovered = DistributedStateStore.recover(tmp_path)
    after = recovered.provenance("l1")
    assert before == after
    assert after["event"]["writer"] == "scheduler"
    assert after["event"]["fencing_token"] == lease["fencing_token"]
    assert after["prev_hash"] == "0" * 64  # hash link to genesis preserved


def test_r9_provenance_chain_links(tmp_path):
    store = DistributedStateStore(tmp_path)
    store.submit(receipt("a", "t", 1))
    store.submit(receipt("b", "t", 2))
    recovered = DistributedStateStore.recover(tmp_path)
    pa, pb = recovered.provenance("a"), recovered.provenance("b")
    assert pb["prev_hash"] == pa["hash"]
    with pytest.raises(ContractError):
        recovered.provenance("never-accepted")


# ---------------------------------------------------------------- DSM-R10
SCHEDULES = {
    "duplicate": FaultSchedule.of(Fault(at=1, kind="duplicate")),
    "delayed": FaultSchedule.of(Fault(at=0, kind="delay", param=2)),
    "reordered": FaultSchedule.of(Fault(at=1, kind="reorder")),
    "lost": FaultSchedule.of(Fault(at=2, kind="loss")),
    "combined": FaultSchedule.of(Fault(at=0, kind="delay", param=2),
                                 Fault(at=1, kind="duplicate"),
                                 Fault(at=3, kind="reorder"),
                                 Fault(at=4, kind="loss")),
}


def test_r10_fault_simulation_is_deterministic():
    messages = [{"event_id": f"m{i}"} for i in range(6)]
    for schedule in SCHEDULES.values():
        assert simulate(messages, schedule) == simulate(messages, schedule)
    dup = simulate(messages, SCHEDULES["duplicate"])
    assert [m["event_id"] for m in dup].count("m1") == 2
    lost = simulate(messages, SCHEDULES["lost"])
    assert "m2" not in [m["event_id"] for m in lost]
    reordered = simulate(messages, SCHEDULES["reordered"])
    # fault at send index 1 swaps messages 1 and 2 in the source stream
    assert [m["event_id"] for m in reordered[:3]] == ["m0", "m2", "m1"]


def test_r10_fault_matrix_converges_with_retransmission(tmp_path):
    result = run_fault_matrix(tmp_path)
    assert result["ok"], json.dumps(result, indent=2)
    names = {c["schedule"] for c in result["matrix"]}
    assert {"duplicate", "delayed", "reordered", "lost", "combined", "clean"} == names
    for case in result["matrix"]:
        assert case["converged"] and case["idempotent"], case["schedule"]


def test_r10_fault_matrix_end_to_end_state_identical(tmp_path):
    """Final accepted state under faults equals the no-fault state."""
    events = [receipt(f"m{i}", f"t{i}", {"seq": i}) for i in range(5)]

    def run(schedule, root):
        outbox = Outbox(Path(root) / "out.journal")
        inbox = Inbox(Path(root) / "in.journal")
        store = DistributedStateStore(Path(root) / "state")
        for e in events:
            outbox.publish(e)
        for _ in range(2):  # initial pass + one retransmission pass
            for e in simulate(outbox.pending(), schedule):
                if inbox.deliver(e) == "accepted":
                    store.submit(e)
                    outbox.ack(e["event_id"])
            schedule = FaultSchedule()  # retransmission rides a clean channel
        # final state = projection per entity + the set of accepted event ids
        # (delivery order may differ under faults; the state must not)
        return (
            {f"t{i}": store.current_value("receipt.publication", f"t{i}")
             for i in range(5)},
            sorted(t["event_id"] for t in store.accepted_transitions()),
        )

    clean = run(FaultSchedule(), tmp_path / "clean")
    for name, schedule in SCHEDULES.items():
        assert run(schedule, tmp_path / name) == clean, name


# ---------------------------------------------------------------- gates B/C
def test_gate_b_evidence_artifact_regenerates_identically(tmp_path):
    repo = Path(__file__).resolve().parents[2]
    p1, h1 = generate_evidence(tmp_path / "a", repo)
    p2, h2 = generate_evidence(tmp_path / "b", repo)
    assert p1.exists() and h1 == h2  # deterministic artifact content
    artifact = json.loads(p1.read_text())
    assert artifact["results"]["ok"]
    assert artifact["results"]["no_duplicate_accepted_transition"]
    assert artifact["source_identity"]["commit"]
    assert artifact["fault_matrix"]["ok"] and artifact["recovery_suite"]["ok"]
    assert artifact["raw_event_logs"]


def test_gate_c_recompute_accepted_transitions_from_journal(tmp_path):
    store = DistributedStateStore(tmp_path)
    with pytest.raises(CrashError):
        store.submit(terminal("e1", "t1", "running"), crash_after="journal_write")
    store.submit(terminal("e1", "t1", "running"))          # duplicate retry
    store.submit(terminal("e2", "t1", "succeeded"))
    # independent recomputation from the retained journal alone
    journal_events = [r["payload"]["event"]["event_id"]
                      for r in Journal(tmp_path / "dsm.journal").replay(-1)
                      if r["kind"] == "transition"]
    assert len(journal_events) == len(set(journal_events)) == 2
    recovered = DistributedStateStore.recover(tmp_path)
    assert [t["event_id"] for t in recovered.accepted_transitions()] == journal_events
    assert recovered.current_value("task.terminal", "t1") == "succeeded"
