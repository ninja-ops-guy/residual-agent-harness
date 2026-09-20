"""EXP-M6-SLM observation export: schema validity, chain integrity, redaction, failure path.

All tests run against tmp_path fixtures only; nothing touches a production store
or a network path.
"""
from __future__ import annotations

import json
import tempfile

import pytest

from residual.core import ContractError
from residual.station.models import save_settings
from residual.station.service import Station, demo_spec
from residual.station.slm_observation import (
    GENESIS_DIGEST,
    HEAD_FILE,
    SlmObservationEmitter,
    SlmObservationLog,
    compile_denylist,
    envelope_digest,
    load_schema,
    validate_observation,
    verify_log,
)


def fields(**overrides):
    base = dict(
        decision_point="test.decision",
        state={"task_id": "OPS-101", "attempt": 1},
        proposed_decision={"files_proposed": ["station/health.py"]},
        actual_decision={"action": "commit_candidate", "head_commit": "a" * 40},
        outcome={"checks_passed": 2, "checks_total": 2},
        verification={"status": "verified_success", "verifier_refs": ["p-x:abc"]},
        cost={"latency_ms": 12.5},
        authority={"requested": ["file_write"], "granted": ["file_write"], "violation": False},
        artifact_digests=["b" * 64],
    )
    base.update(overrides)
    return base


@pytest.fixture
def emitter(tmp_path):
    return SlmObservationEmitter(tmp_path / "station")


def read_envelopes(root):
    lines = []
    for path in SlmObservationLog(root / "slm-observations").files():
        lines += [json.loads(line) for line in path.read_text().splitlines()]
    return lines


def test_emitted_record_is_schema_valid(emitter, tmp_path):
    envelope = emitter.emit(mission_id="p-test", incident_id="OPS-101", **fields())
    record = envelope["record"]
    assert record["schema_version"] == "slm-observation-v0"
    assert record["contamination_group"] is None
    assert {"collection-only", "quarantined-unallocated"} <= set(record["labels"])
    assert record["provenance"]["source_class"] == "ax21"
    assert record["provenance"]["mission_id"] == "p-test"
    assert record["provenance"]["incident_id"] == "OPS-101"
    assert record["provenance"]["redactions"] == 0
    # Re-validation from disk confirms the vendored schema accepts emitted bytes.
    validate_observation(record, load_schema())


def test_validator_rejects_non_conforming_records():
    emitter_schema = load_schema()
    with tempfile.TemporaryDirectory() as d:
        record = SlmObservationEmitter(d).build(mission_id="p-x", **fields())
    extra = {**record, "training_authorized": True}
    with pytest.raises(ContractError):
        validate_observation(extra, emitter_schema)
    bad_status = json.loads(json.dumps(record))
    bad_status["verification"]["status"] = "looks_good"
    with pytest.raises(ContractError):
        validate_observation(bad_status, emitter_schema)
    bad_ts = json.loads(json.dumps(record))
    bad_ts["timestamp"] = "2026-09-20 15:32:37"
    with pytest.raises(ContractError):
        validate_observation(bad_ts, emitter_schema)


def test_digest_chain_integrity_and_tamper_detection(emitter, tmp_path):
    for i in range(3):
        emitter.emit(mission_id="p-test", incident_id=f"OPS-10{i}", **fields())
    root = tmp_path / "station"
    assert verify_log(root) is True
    envs = read_envelopes(root)
    assert [e["seq"] for e in envs] == [1, 2, 3]
    assert envs[0]["prev_digest"] == GENESIS_DIGEST
    assert envs[1]["prev_digest"] == envs[0]["digest"]
    assert envs[2]["digest"] == envelope_digest(envs[2]["record"], envs[1]["digest"])
    # Tamper: rewrite one record payload in place.
    path = SlmObservationLog(root / "slm-observations").files()[0]
    lines = path.read_text().splitlines()
    env = json.loads(lines[1])
    env["record"]["outcome"]["checks_passed"] = 0
    lines[1] = json.dumps(env)
    path.write_text("\n".join(lines) + "\n")
    assert verify_log(root) is False


def test_truncation_detected_via_head_pointer(emitter, tmp_path):
    for _ in range(2):
        emitter.emit(mission_id="p-test", **fields())
    root = tmp_path / "station"
    path = SlmObservationLog(root / "slm-observations").files()[0]
    lines = path.read_text().splitlines()
    path.write_text(lines[0] + "\n")  # drop the tail record
    assert verify_log(root) is False


def test_corrupt_chain_head_blocks_append(emitter, tmp_path):
    emitter.emit(mission_id="p-test", **fields())
    (tmp_path / "station" / "slm-observations" / HEAD_FILE).write_text("garbage")
    with pytest.raises(ContractError):
        emitter.emit(mission_id="p-test", **fields())


def test_redaction_is_marked_not_silent(emitter, tmp_path):
    emitter.emit(mission_id="p-test", **fields(state={
        "note": "used api_key=sk-live-9876543210 from host db-01.corp at 192.168.5.161",
        "auth": "Bearer abcdefgh12345678",
    }))
    raw = ""
    for path in SlmObservationLog(tmp_path / "station" / "slm-observations").files():
        raw += path.read_text()
    assert "sk-live-9876543210" not in raw
    assert "192.168.5.161" not in raw
    assert "db-01.corp" not in raw
    assert "abcdefgh12345678" not in raw
    assert "[REDACTED:credential]" in raw and "[REDACTED:ipv4]" in raw
    assert "[REDACTED:hostname]" in raw and "[REDACTED:bearer]" in raw
    env = read_envelopes(tmp_path / "station")[0]
    assert env["record"]["provenance"]["redactions"] >= 4
    assert "credential" in env["record"]["provenance"]["redaction_kinds"]


def test_custom_denylist_and_validation(tmp_path):
    em = SlmObservationEmitter(tmp_path / "s")
    em.emit(mission_id="p-test", denylist=[r"widget-\d+"], **fields(state={"part": "widget-42"}))
    raw = read_envelopes(tmp_path / "s")[0]["record"]
    assert "widget-42" not in json.dumps(raw)
    assert "[REDACTED:custom]" in json.dumps(raw)
    with pytest.raises(ContractError):
        compile_denylist(["(unclosed"])
    with pytest.raises(ContractError):
        compile_denylist(["x"] * 21)


def test_station_gate_off_by_default(tmp_path):
    station = Station(tmp_path / "station")
    pid = station.create(demo_spec(), demo=True)["project_id"]
    result = station._slm_observe(pid, "OPS-101", **fields())
    assert result is None
    assert not (station.store.root / "slm-observations").exists()


def test_station_emission_when_enabled(tmp_path):
    station = Station(tmp_path / "station")
    save_settings(station.store, {"slm_observation_export": True})
    pid = station.create(demo_spec(), demo=True)["project_id"]
    envelope = station._slm_observe(pid, "OPS-101", **fields())
    assert envelope is not None
    assert envelope["record"]["provenance"]["mission_id"] == pid
    assert verify_log(station.store.root) is True


def test_emission_failure_is_logged_and_never_blocks(tmp_path, monkeypatch):
    station = Station(tmp_path / "station")
    save_settings(station.store, {"slm_observation_export": True})
    pid = station.create(demo_spec(), demo=True)["project_id"]
    before = len(station.store.events(pid, 0, 100000))

    def boom(**kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(station.slm_observations, "emit", boom)
    assert station._slm_observe(pid, "OPS-101", **fields()) is None  # no raise
    events = station.store.events(pid, 0, 100000)
    assert len(events) == before + 1
    failure = events[-1]
    assert failure["event_type"] == "slm.observation_failed"
    assert failure["task_id"] == "OPS-101"
    assert "disk full" in failure["data"]["message"]


def test_invalid_observation_payload_logged_not_raised(tmp_path):
    station = Station(tmp_path / "station")
    save_settings(station.store, {"slm_observation_export": True})
    pid = station.create(demo_spec(), demo=True)["project_id"]
    bad = fields()
    bad["verification"] = {"status": "definitely-fine"}
    assert station._slm_observe(pid, "OPS-101", **bad) is None
    assert any(e["event_type"] == "slm.observation_failed" for e in station.store.events(pid, 0, 100000))


def test_settings_validation(tmp_path):
    station = Station(tmp_path / "station")
    with pytest.raises(ContractError):
        save_settings(station.store, {"slm_observation_export": "yes"})
    with pytest.raises(ContractError):
        save_settings(station.store, {"slm_observation_denylist": ["(broken"]})
    save_settings(station.store, {"slm_observation_export": True, "slm_observation_denylist": [r"host-\d+"]})
    settings = station.store.settings()
    assert settings["slm_observation_export"] is True
    assert settings["slm_observation_denylist"] == [r"host-\d+"]
