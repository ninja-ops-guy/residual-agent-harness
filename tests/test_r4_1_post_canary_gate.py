from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "verifier" / "r4_1_post_canary" / "verify.py"
SPEC = importlib.util.spec_from_file_location("r41_verify", MODULE_PATH)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fixture(tmp_path: Path) -> tuple[dict, str]:
    names = ["authorization.json", "outbox.log", "restart.log", "services.json", "production.json", "credentials.json", "rollback.json", "events.log"]
    artifacts = []
    for name in names:
        data = (name + "\n").encode()
        (tmp_path / name).write_bytes(data)
        artifacts.append({"path": name, "sha256": digest(data), "bytes": len(data), "media_type": "application/json", "producer": "test-fixture"})
    d = "a" * 64
    operation = "op-r41-001"
    kinds = gate.EVENT_ORDER
    events = [{"seq": i, "at": f"2026-09-23T00:00:{i:02d}Z", "kind": kind, "operation_id": operation, "artifact": "events.log"} for i, kind in enumerate(kinds)]
    state = {"captured_at": "2026-09-23T00:00:00Z", "candidate_head": gate.EXPECTED_HEAD, "candidate_tree": gate.EXPECTED_TREE, "environment_digest": d, "protected_services_digest": d, "credentials_digest": d, "production_state_digest": d}
    bundle = {
        "schema": gate.SCHEMA, "run_id": "r41-001", "candidate": {"head": gate.EXPECTED_HEAD, "tree": gate.EXPECTED_TREE},
        "authorization": {"receipt_artifact": "authorization.json", "run_id": "r41-001", "candidate_head": gate.EXPECTED_HEAD, "candidate_tree": gate.EXPECTED_TREE, "environment": "canary", "not_before": "2026-09-22T23:59:00Z", "not_after": "2026-09-23T00:10:00Z", "authorized_by": "change-control", "canary_only": True, "promotion_authorized": False},
        "bounds": {"started_at": "2026-09-23T00:00:00Z", "finished_at": "2026-09-23T00:01:00Z", "max_duration_seconds": 120, "max_network_attempts": 2, "observed_network_attempts": 1, "timed_out": False},
        "prestate": dict(state), "poststate": {**state, "captured_at": "2026-09-23T00:01:00Z"}, "events": events,
        "receiver": {"operation_id": operation, "side_effect_count": 1, "side_effect_ids": ["effect-1"]},
        "outbox": {"operation_id": operation, "pre_state": "pending", "post_state": "acknowledged", "durable_before_send": True, "durable_terminal": True, "journal_artifact": "outbox.log"},
        "crash_restart": {"injected": True, "operation_id_before": operation, "operation_id_after": operation, "receipt_checked_before_retry": True, "retry_suppressed_by_receipt": True, "receiver_side_effect_count_after_restart": 1, "trace_artifact": "restart.log"},
        "protected_services": {"stable": True, "before_digest": d, "after_digest": d, "artifact": "services.json"},
        "production_mutations": {"count": 0, "authorized_count": 0, "artifact": "production.json"},
        "credential_mutations": {"count": 0, "authorized_count": 0, "artifact": "credentials.json"},
        "rollback": {"rehearsed": True, "succeeded": True, "restored_state_digest": d, "expected_state_digest": d, "within_seconds": 10, "max_seconds": 30, "artifact": "rollback.json"},
        "operator_interventions": [], "artifacts": artifacts,
    }
    receipt = {k: v for k, v in bundle["authorization"].items() if k != "receipt_artifact"}
    receipt_data = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    (tmp_path / "authorization.json").write_bytes(receipt_data)
    artifacts[0]["sha256"] = digest(receipt_data)
    artifacts[0]["bytes"] = len(receipt_data)
    return bundle, artifacts[0]["sha256"]


def test_complete_fixture_is_promotion_eligible(tmp_path: Path) -> None:
    bundle, auth = fixture(tmp_path)
    result = gate.evaluate(bundle, tmp_path, auth)
    assert result.disposition() == "PROMOTION_ELIGIBLE"
    assert set(result.checks.values()) == {"PASS"}


def test_missing_artifact_fails_closed(tmp_path: Path) -> None:
    bundle, auth = fixture(tmp_path)
    (tmp_path / "events.log").unlink()
    result = gate.evaluate(bundle, tmp_path, auth)
    assert result.disposition() == "EVIDENCE_INCOMPLETE"


def test_wrong_candidate_is_incomplete(tmp_path: Path) -> None:
    bundle, auth = fixture(tmp_path)
    bundle["candidate"]["head"] = "0" * 40
    result = gate.evaluate(bundle, tmp_path, auth)
    assert result.disposition() == "EVIDENCE_INCOMPLETE"


def test_functional_failure_is_canary_failed(tmp_path: Path) -> None:
    bundle, auth = fixture(tmp_path)
    bundle["rollback"]["succeeded"] = False
    result = gate.evaluate(bundle, tmp_path, auth)
    assert result.disposition() == "CANARY_FAILED"


def test_verified_safety_trigger_requires_rollback(tmp_path: Path) -> None:
    bundle, auth = fixture(tmp_path)
    bundle["credential_mutations"]["count"] = 1
    result = gate.evaluate(bundle, tmp_path, auth)
    assert result.disposition() == "ROLLBACK_REQUIRED"


def test_incomplete_does_not_hide_verified_rollback_trigger(tmp_path: Path) -> None:
    bundle, auth = fixture(tmp_path)
    bundle["credential_mutations"]["count"] = 1
    bundle["candidate"]["head"] = "0" * 40
    result = gate.evaluate(bundle, tmp_path, auth)
    assert result.disposition() == "ROLLBACK_REQUIRED"


def test_decision_serialization_is_deterministic() -> None:
    value = {"z": 1, "a": [2, 3]}
    assert gate.canonical_bytes(value) == b'{"a":[2,3],"z":1}\n'


def test_cli_writes_non_actionable_decisions(tmp_path: Path, capsys) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    bundle, auth = fixture(evidence)
    (evidence / "canary-evidence.json").write_text(json.dumps(bundle), encoding="utf-8")
    decision = tmp_path / "decision.json"
    rollback = tmp_path / "rollback-decision.json"
    report = tmp_path / "report.md"
    rc = gate.main(["--evidence", str(evidence), "--authorization-sha256", auth, "--decision", str(decision), "--rollback-decision", str(rollback), "--report", str(report)])
    assert rc == 0
    assert capsys.readouterr().out == "PROMOTION_ELIGIBLE\n"
    assert json.loads(decision.read_text())["promotion_performed"] is False
    assert json.loads(rollback.read_text())["rollback_executed"] is False
    assert "not promotion authorization" in report.read_text()


def test_cli_missing_evidence_still_returns_one_disposition(tmp_path: Path, capsys) -> None:
    decision = tmp_path / "decision.json"
    rollback = tmp_path / "rollback-decision.json"
    report = tmp_path / "report.md"
    rc = gate.main(["--evidence", str(tmp_path / "absent"), "--authorization-sha256", "0" * 64, "--decision", str(decision), "--rollback-decision", str(rollback), "--report", str(report)])
    assert rc == 2
    assert capsys.readouterr().out == "EVIDENCE_INCOMPLETE\n"
