"""SoakTestReport signature verification tests (N9-R10, N9-R11, N9-R12)."""
import pytest

from residual.soak import (
    SoakConfig,
    SoakHarness,
    SoakMetrics,
    SoakTestReport,
    sign_report,
    verify_report,
)

STATION_KEY = b"station-identity-key-0001"


def _signed_report():
    m = SoakMetrics(tasks_executed=10, accepted=9, rejected=1, escalated=1,
                    cache_eligible=10, cache_hits=7, tokens_used=400,
                    tokens_uncached=1000, recovery_times_seconds=[12.0])
    return SoakTestReport(m, days_completed=1,
                          red_team_results=[{
                              "exercise": "rt", "attack": "receipt_forgery",
                              "blocked": True, "observed": True,
                              "receipt_id": "abc123", "detail": "x",
                          }]).build_signed(STATION_KEY)


def test_signature_verifies():
    assert verify_report(_signed_report(), STATION_KEY)


def test_wrong_key_fails():
    assert not verify_report(_signed_report(), b"other-key")


def test_tampered_payload_fails():
    signed = _signed_report()
    signed["payload"]["totals"]["tasks_executed"] = 999999
    assert not verify_report(signed, STATION_KEY)
    assert not SoakTestReport.verify(signed, STATION_KEY)


def test_tampered_signature_fails():
    signed = _signed_report()
    signed["signature"] = "0" * 64
    assert not verify_report(signed, STATION_KEY)


def test_malformed_envelope_fails():
    assert not verify_report({}, STATION_KEY)
    assert not verify_report({"payload": {}}, STATION_KEY)


def test_signature_deterministic():
    m = SoakMetrics(tasks_executed=1, accepted=1)
    r1 = sign_report(SoakTestReport(m, 1).build(), STATION_KEY)
    # drop the timestamp so payloads are identical
    r2 = sign_report({**SoakTestReport(m, 1).build(),
                      "generated_at_epoch": r1["payload"]["generated_at_epoch"]}, STATION_KEY)
    assert r1["signature"] == r2["signature"]
    assert r1["key_id"] == r2["key_id"]


def test_report_contains_all_n9_r10_fields(tmp_path):
    cfg = SoakConfig(total_days=1, tasks_per_day=50)
    h = SoakHarness(cfg, STATION_KEY, state_path=str(tmp_path / "s.json"),
                    enforce_load_minimum=False)
    h.run()
    signed = h.report(signed=True)
    assert verify_report(signed, STATION_KEY)
    p = signed["payload"]
    assert p["schema_version"] == "residual.soak.report.v1"
    for key in ("tasks_executed", "accepted", "rejected", "escalated", "unhandled_exceptions"):
        assert key in p["totals"]
    for key in ("cache_hit_rate", "token_savings_rate", "brake_fp_rate",
                "brake_fn_rate", "escalation_rate", "mttr_seconds"):
        assert key in p["rates"]
    assert set(p["targets"]) == {"cache_hit_rate", "token_savings", "brake_fp_rate",
                                 "brake_fn_rate", "escalation_rate", "unhandled_exceptions"}


def test_red_team_results_documented(tmp_path):
    cfg = SoakConfig(total_days=1, tasks_per_day=20)
    h = SoakHarness(cfg, STATION_KEY, state_path=str(tmp_path / "s.json"),
                    enforce_load_minimum=False)
    h.run(redteam=True)
    rt = h.report(signed=False)["red_team"]
    # N9-R12: at least one exercise; every attempt receipted and observed
    assert rt["exercises"] >= 1
    assert rt["attempts"], "red team attempts must be recorded"
    assert rt["all_receipted"]
    assert all(a["observed"] for a in rt["attempts"])
    assert {a["attack"] for a in rt["attempts"]} == {
        "quarantine_bypass", "receipt_forgery", "unsafe_execution", "data_exfiltration"}
    assert rt["blocked"] + rt["succeeded"] == len(rt["attempts"])
    assert rt["succeeded"] == 0  # spec: attacks must be blocked or observed; all blocked here
