"""Soak-state persistence and deterministic resume tests."""
import json

import pytest

from residual.soak import SoakConfig, SoakHarness, SoakMetrics, SoakState

CFG = SoakConfig(total_days=4, tasks_per_day=50)


def _harness(path):
    return SoakHarness(CFG, b"key", state_path=str(path) if path else None,
                       enforce_load_minimum=False)


def test_state_roundtrip(tmp_path):
    state = SoakState(seed=1, tasks_per_day=50, total_days=4, next_day=2,
                      metrics=SoakMetrics(tasks_executed=100, accepted=95,
                                          recovery_times_seconds=[3.0]),
                      red_team_results=[{"attack": "x", "receipt_id": "r"}])
    path = tmp_path / "state.json"
    state.save(str(path))
    loaded = SoakState.load(str(path))
    assert loaded.to_dict() == state.to_dict()
    assert loaded.days_completed == 2 and not loaded.complete


def test_state_rejects_unknown_schema(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"schema_version": "bogus"}))
    with pytest.raises(ValueError, match="unsupported soak state schema"):
        SoakState.load(str(path))


def test_state_saved_atomically_per_day(tmp_path):
    path = tmp_path / "state.json"
    h = _harness(path)
    h.run(max_days=1)
    assert path.exists()
    assert not (tmp_path / "state.json.tmp").exists()
    loaded = SoakState.load(str(path))
    assert loaded.next_day == 1
    assert loaded.metrics.tasks_executed == 50


def test_resume_matches_uninterrupted_run(tmp_path):
    # reference: full 4-day run, never persisted
    ref = SoakHarness(CFG, b"key", state_path=None, enforce_load_minimum=False)
    ref.run()

    # interrupted: 2 days, then a brand-new harness resumes from state
    path = tmp_path / "state.json"
    first = _harness(path)
    first.run(max_days=2)
    assert first.state.days_completed == 2
    partial_metrics = first.state.metrics.to_dict()

    second = _harness(path)
    second.run()
    assert second.state.days_completed == 4
    assert second.state.metrics.to_dict() == ref.state.metrics.to_dict()
    assert second.state.red_team_results == ref.state.red_team_results
    # partial state was a strict prefix of the work (task counts add up)
    assert partial_metrics["tasks_executed"] == 100
    assert ref.state.metrics.tasks_executed == 200


def test_resume_after_corrupt_state_starts_fresh_or_fails(tmp_path):
    path = tmp_path / "state.json"
    h = _harness(path)
    h.run(max_days=1)
    path.write_text("{ not json")
    resumed = _harness(path)
    with pytest.raises(json.JSONDecodeError):
        resumed.run()


def test_completed_soak_is_idempotent(tmp_path):
    path = tmp_path / "state.json"
    h = _harness(path)
    h.run()
    snapshot = h.state.to_dict()
    h2 = _harness(path)
    h2.run()
    assert h2.state.to_dict() == snapshot
    assert h2.state.complete
