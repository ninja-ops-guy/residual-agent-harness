"""Tests for SPEC-ENT-004 (ENT4-R1 through ENT4-R8)."""
from __future__ import annotations

import pytest

from residual.core import ContractError
from residual.hadr import (
    BackupManager,
    DegradedStation,
    EventJournal,
    FailoverController,
    LocalKeyManager,
    ManualClock,
    ReceiptChain,
    ReceiptReplicator,
    ReplicaNode,
    RestoreDrill,
    RunState,
    SimulatedTransport,
    Station,
    StationRegistry,
    TaskRecord,
    decrypt_backup,
)
from residual.hadr.backup import BACKUP_INTERVAL_SECONDS, REQUIRED_COMPONENTS
from residual.hadr.failover import RTO_LIMIT_SECONDS, TASK_DONE, TASK_RUNNING
from residual.hadr.restore import QUARTER_SECONDS


def make_journal(clock):
    return EventJournal(clock)


def make_cluster(clock):
    journal = make_journal(clock)
    registry = StationRegistry(clock=clock, journal=journal)
    registry.register(Station("st-a", "us-east", ("w1", "w2")))
    registry.register(Station("st-b", "us-east", ("w3",)))
    registry.register(Station("st-c", "eu-west", ("w4", "w5")))
    return registry, journal


# ENT4-R1 -----------------------------------------------------------------

def test_ent4_r1_active_active_multiple_regions_operate_simultaneously():
    clock = ManualClock()
    registry, _ = make_cluster(clock)
    active = registry.active_stations()
    assert len(active) == 3
    assert registry.regions() == {"us-east", "eu-west"}


def test_ent4_r1_automatic_takeover_on_failure():
    clock = ManualClock()
    registry, journal = make_cluster(clock)
    clock.advance(20.0)  # beyond the 15s heartbeat timeout
    registry.heartbeat("st-b")
    registry.heartbeat("st-c")
    takeovers = registry.tick()
    assert len(takeovers) == 1
    assert takeovers[0].failed_station == "st-a"
    assert takeovers[0].successor_station == "st-b"  # same region preferred
    assert not registry.stations["st-a"].active
    assert registry.stations["st-b"].active
    # takeover is observed/receipted (ENT4-R8)
    assert journal.of_kind("takeover")


# ENT4-R2 -----------------------------------------------------------------

def make_replicator(clock, latencies=None):
    journal = make_journal(clock)
    transport = SimulatedTransport(clock=clock, latency_seconds=latencies or {"eu-west": 5.0})
    replicator = ReceiptReplicator(
        clock=clock, transport=transport, journal=journal, primary_region="us-east")
    replicator.add_replica(ReplicaNode("rep-p1", "us-east"))
    replicator.add_replica(ReplicaNode("rep-s1", "eu-west"))
    return replicator, journal


def test_ent4_r2_sync_primary_async_secondary():
    clock = ManualClock()
    replicator, _ = make_replicator(clock)
    receipt = replicator.append("task-1", "output-1")
    # synchronous in the primary region: present immediately
    assert replicator.replicas["rep-p1"].chain.receipts[-1] == receipt
    # asynchronous to secondaries: not yet delivered
    assert not replicator.replicas["rep-s1"].chain.receipts
    clock.advance(5.0)
    replicator.deliver()
    assert replicator.replicas["rep-s1"].chain.receipts[-1] == receipt


def test_ent4_r2_thirty_second_max_lag_alert():
    clock = ManualClock()
    replicator, journal = make_replicator(clock, latencies={"eu-west": 120.0})
    receipt = replicator.append("task-1", "output-1")
    clock.advance(31.0)
    alerts = replicator.check_max_lag()
    assert alerts and alerts[0].receipt_id == receipt.receipt_id
    assert alerts[0].lag_seconds > 30.0
    with pytest.raises(ContractError):
        replicator.assert_max_lag()
    assert journal.of_kind("replication-lag-alert")
    # within budget once delivered
    clock.advance(120.0)
    replicator.deliver()
    assert replicator.check_max_lag() == []


def test_ent4_r2_receipt_reaches_secondary_within_30s():
    clock = ManualClock()
    replicator, _ = make_replicator(clock, latencies={"eu-west": 10.0})
    receipt = replicator.append("task-1", "output-1")
    clock.advance(10.0)
    replicator.deliver()
    assert any(r.receipt_id == receipt.receipt_id
               for r in replicator.replicas["rep-s1"].chain.receipts)
    replicator.assert_max_lag()


# ENT4-R3 / ENT4-R4 -------------------------------------------------------

def make_run():
    return RunState(
        run_id="run-1",
        station_id="st-a",
        tasks=[
            TaskRecord("task-1", TASK_DONE, "w1"),
            TaskRecord("task-2", TASK_RUNNING, "w2"),
            TaskRecord("task-3"),
        ],
    )


def test_ent4_r3_mid_run_failover_resumes_from_last_verified_receipt():
    clock = ManualClock()
    registry, journal = make_cluster(clock)
    run = make_run()
    run.chain.append("task-1", "output-1")
    last = run.chain.receipts[-1]
    controller = FailoverController(clock=clock, registry=registry, journal=journal)
    report = controller.failover(run, "st-a")
    assert report.resumed_from_receipt == last.receipt_id
    assert set(report.incomplete_tasks) == {"task-2", "task-3"}
    # reassigned to successor's workers only
    assert {w for _, w in report.reassignments} <= set(
        registry.stations[report.successor_station].workers)
    assert run.station_id == report.successor_station
    # no human intervention: all incomplete tasks reassigned automatically
    assert len(report.reassignments) == 2


def test_ent4_r3_failover_refuses_corrupted_chain():
    clock = ManualClock()
    registry, _ = make_cluster(clock)
    run = make_run()
    run.chain.append("task-1", "output-1")
    run.chain.receipts[0] = run.chain.receipts[0].__class__(
        receipt_id="f" * 64, sequence=0, task_id="task-1",
        payload="tampered", prev_hash="0" * 64)
    controller = FailoverController(clock=clock, registry=registry, journal=make_journal(clock))
    with pytest.raises(ContractError):
        controller.failover(run, "st-a")


def test_ent4_r4_rpo_zero_receipt_acked_only_when_durable():
    clock = ManualClock()
    replicator, _ = make_replicator(clock)
    replicator.replicas["rep-p1"].available = False
    with pytest.raises(ContractError):
        replicator.append("task-1", "output-1")
    # nothing acknowledged: chain rolled back, no replica holds it
    assert replicator.chain.receipts == []
    replicator.replicas["rep-p1"].available = True
    receipt = replicator.append("task-1", "output-1")
    assert replicator.chain.receipts == [receipt]
    assert replicator.replicas["rep-p1"].chain.receipts == [receipt]


def test_ent4_r4_rto_under_60s_via_injected_clock():
    clock = ManualClock()
    registry, _ = make_cluster(clock)
    run = make_run()
    run.chain.append("task-1", "output-1")
    controller = FailoverController(clock=clock, registry=registry, journal=make_journal(clock))
    clock.advance(5.0)  # detection time
    report = controller.failover(run, "st-a")
    clock.advance(1.0)  # failover itself was instant on the injected clock
    assert report.rto_seconds == 0.0
    assert report.within_rto
    assert report.rto_seconds < RTO_LIMIT_SECONDS
    # takeover RTO from registry is also measurable and within budget
    clock.advance(20.0)
    registry.heartbeat("st-c")
    takeover = registry.tick()[0]
    assert takeover.rto_seconds < RTO_LIMIT_SECONDS


# ENT4-R5 -----------------------------------------------------------------

def snapshot_kwargs(chain):
    return dict(
        receipt_chain=chain,
        observation_log=["obs-1", "obs-2"],
        station_state={"station": "st-a"},
        tenant_configs={"tenant-1": {"plan": "ent"}},
        module_registry={"mod-1": "1.0.0"},
    )


def test_ent4_r5_encrypted_backup_contains_all_components():
    clock = ManualClock()
    journal = make_journal(clock)
    chain = ReceiptChain()
    chain.append("task-1", "output-1")
    manager = BackupManager(clock=clock, journal=journal, key_manager=LocalKeyManager())
    record = manager.take_backup(**snapshot_kwargs(chain))
    assert record.components == REQUIRED_COMPONENTS
    snapshot = decrypt_backup(record, manager.key_manager)
    for component in REQUIRED_COMPONENTS:
        assert component in snapshot
    assert snapshot["receipt_chain"][0]["task_id"] == "task-1"
    # ciphertext is not plaintext
    assert b"task-1" not in record.ciphertext
    # backup is observed/receipted (ENT4-R8)
    assert journal.of_kind("backup")


def test_ent4_r5_keys_managed_separately_and_tamper_detected():
    clock = ManualClock()
    keys = LocalKeyManager()
    manager = BackupManager(clock=clock, journal=make_journal(clock), key_manager=keys)
    chain = ReceiptChain()
    chain.append("task-1", "output-1")
    record = manager.take_backup(**snapshot_kwargs(chain))
    # wrong key cannot decrypt
    other = LocalKeyManager()
    with pytest.raises(ContractError):
        decrypt_backup(record, other)
    # tampered ciphertext is rejected by the MAC
    tampered = record.__class__(
        **{**record.__dict__, "ciphertext": bytes([record.ciphertext[0] ^ 1]) + record.ciphertext[1:]})
    with pytest.raises(ContractError):
        decrypt_backup(tampered, keys)


def test_ent4_r5_daily_schedule():
    clock = ManualClock()
    manager = BackupManager(clock=clock, journal=make_journal(clock), key_manager=LocalKeyManager())
    chain = ReceiptChain()
    first = manager.take_daily_backup_if_due(**snapshot_kwargs(chain))
    assert first is not None
    assert manager.take_daily_backup_if_due(**snapshot_kwargs(chain)) is None
    clock.advance(BACKUP_INTERVAL_SECONDS)
    assert manager.take_daily_backup_if_due(**snapshot_kwargs(chain)) is not None


# ENT4-R6 -----------------------------------------------------------------

def test_ent4_r6_restore_drill_verifies_integrity_and_reports():
    clock = ManualClock()
    journal = make_journal(clock)
    keys = LocalKeyManager()
    manager = BackupManager(clock=clock, journal=journal, key_manager=keys)
    chain = ReceiptChain()
    chain.append("task-1", "output-1")
    chain.append("task-2", "output-2")
    record = manager.take_backup(**snapshot_kwargs(chain))
    drill = RestoreDrill(clock=clock, journal=journal, key_manager=keys)
    report = drill.run(record, expected_observations=2)
    assert report.ok
    assert report.restored and report.chain_intact and report.observation_log_complete
    assert report.components_present == REQUIRED_COMPONENTS
    # restore test is observed/receipted (ENT4-R8)
    assert journal.of_kind("restore-test")


def test_ent4_r6_restore_drill_detects_corruption():
    clock = ManualClock()
    keys = LocalKeyManager()
    manager = BackupManager(clock=clock, journal=make_journal(clock), key_manager=keys)
    chain = ReceiptChain()
    chain.append("task-1", "output-1")
    record = manager.take_backup(**snapshot_kwargs(chain))
    snapshot = decrypt_backup(record, keys)
    snapshot["receipt_chain"][0]["payload"] = "tampered"
    # rebuild a backup whose chain is broken but MAC is valid
    from residual.core import canonical
    from residual.hadr.backup import encrypt_aead
    import hashlib
    plaintext = canonical(snapshot).encode("utf-8")
    ciphertext, tag = encrypt_aead(keys.get_key(record.key_id), record.nonce, plaintext,
                                   "residual.hadr.backup.v1".encode("utf-8"))
    corrupted = record.__class__(
        **{**record.__dict__, "ciphertext": ciphertext, "tag": tag,
           "plaintext_hash": hashlib.sha256(plaintext).hexdigest()})
    drill = RestoreDrill(clock=clock, journal=make_journal(clock), key_manager=keys)
    report = drill.run(corrupted)
    assert not report.ok
    assert not report.chain_intact


def test_ent4_r6_quarterly_cadence():
    clock = ManualClock()
    keys = LocalKeyManager()
    drill = RestoreDrill(clock=clock, journal=make_journal(clock), key_manager=keys)
    assert drill.quarterly_test_due()
    manager = BackupManager(clock=clock, journal=make_journal(clock), key_manager=keys)
    chain = ReceiptChain()
    chain.append("task-1", "output-1")
    record = manager.take_backup(**snapshot_kwargs(chain))
    drill.run(record)
    assert not drill.quarterly_test_due()
    clock.advance(QUARTER_SECONDS)
    assert drill.quarterly_test_due()
    with pytest.raises(ContractError):
        drill.assert_quarterly_tested()


# ENT4-R7 -----------------------------------------------------------------

def test_ent4_r7_degraded_mode_queues_and_syncs_on_reconnect():
    clock = ManualClock()
    registry, _ = make_cluster(clock)
    journal = make_journal(clock)
    shared = ReceiptChain()
    station = DegradedStation(
        station_id="st-c", registry=registry, journal=journal,
        local_model=lambda work: f"local:{work}", shared_chain=shared)
    # connected: publishes directly
    station.operate("task-0", "a")
    assert station.pending_count() == 0
    assert len(shared.receipts) == 1
    # cluster unavailable: local operation continues, receipts queue locally
    registry.stations["st-c"].reachable = False
    r1 = station.operate("task-1", "b")
    r2 = station.operate("task-2", "c")
    assert station.pending_count() == 2
    assert len(shared.receipts) == 1
    with pytest.raises(ContractError):
        station.sync()
    # connectivity returns: queued receipts synchronize
    registry.stations["st-c"].reachable = True
    resolutions = station.sync()
    assert resolutions == []
    assert station.pending_count() == 0
    assert len(shared.receipts) == 3
    assert journal.of_kind("degraded-sync")
    # local model outputs are what was queued
    assert [r.payload for r in (r1, r2)] == ["local:b", "local:c"]


def test_ent4_r7_conflict_resolution_is_deterministic():
    clock = ManualClock()
    registry, _ = make_cluster(clock)
    journal = make_journal(clock)
    shared = ReceiptChain()
    shared.append("task-1", "zzz-authoritative")
    station = DegradedStation(
        station_id="st-c", registry=registry, journal=journal,
        local_model=lambda work: work, shared_chain=shared)
    registry.stations["st-c"].reachable = False
    station.operate("task-1", "aaa-local")  # conflicts with shared copy
    registry.stations["st-c"].reachable = True
    resolutions = station.sync()
    assert len(resolutions) == 1
    assert resolutions[0].kept == "local"  # smaller payload wins
    assert shared.receipts[-1].payload == "aaa-local"
    # reverse case: authoritative copy retained
    shared.append("task-2", "aaa-authoritative")
    registry.stations["st-c"].reachable = False
    station.operate("task-2", "zzz-local")
    registry.stations["st-c"].reachable = True
    resolutions = station.sync()
    assert resolutions[0].kept == "remote"


# ENT4-R8 -----------------------------------------------------------------

def test_ent4_r8_all_operations_observed_and_receipted():
    clock = ManualClock()
    registry, journal = make_cluster(clock)
    chain = ReceiptChain()
    chain.append("task-1", "output-1")

    controller = FailoverController(clock=clock, registry=registry, journal=journal)
    run = make_run()
    run.chain = chain.clone()
    controller.failover(run, "st-a")

    keys = LocalKeyManager()
    manager = BackupManager(clock=clock, journal=journal, key_manager=keys)
    record = manager.take_backup(**snapshot_kwargs(chain))
    drill = RestoreDrill(clock=clock, journal=journal, key_manager=keys)
    drill.run(record)

    assert journal.of_kind("failover")
    assert journal.of_kind("backup")
    assert journal.of_kind("restore-test")
    assert journal.verify()
