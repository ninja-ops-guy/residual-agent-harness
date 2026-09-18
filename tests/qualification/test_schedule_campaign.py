from __future__ import annotations

from residual.qualification.schedule import run_campaign, run_history


def test_same_seed_replays_same_semantic_history():
    first = run_history(20260916, steps=80, lanes=3)
    second = run_history(20260916, steps=80, lanes=3)
    assert first["result"] == second["result"] == "PASS"
    assert first["trace"] == second["trace"]
    assert first["final_state"] == second["final_state"]
    assert first["semantic_observation_digest"] == second["semantic_observation_digest"]
    assert first["replay_digest"] == second["replay_digest"]


def test_campaign_retains_each_seed_and_has_no_hidden_retries():
    report = run_campaign(start_seed=11, seeds=8, steps=60, lanes=2)
    assert report["result"] == "PASS"
    assert [row["seed"] for row in report["histories"]] == list(range(11, 19))
    assert report["failures"] == []
    assert all(row["steps_executed"] == 60 for row in report["histories"])
    assert report["discovery_adequacy"]["result"] == "PASS"
    assert report["discovery_adequacy"]["missing_actions"] == []
    assert report["discovery_adequacy"]["outcome_counts"].get("UNHANDLED", 0) == 0
    assert all(row["outcome_counts"].get("NOOP", 0) == 0 for row in report["histories"])
