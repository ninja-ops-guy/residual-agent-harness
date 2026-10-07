"""Track M tests: connector contract conformance suite and certification matrix."""
import json

import pytest

from residual.connectors.conformance import (
    CertificationMatrix,
    ConformanceSuite,
    ResilientConnector,
    ScriptedTransport,
    run_conformance_suite,
)
from residual.core import ContractError
from residual.integrations.base import TransportResponse


def _factory(t):
    return ResilientConnector("https://conformance.local", token="initial", transport=t)


# -- ScriptedTransport mechanics (M-R1) ---------------------------------------

def test_scripted_transport_records_requests():
    t = ScriptedTransport()
    t.add("GET", "/x", TransportResponse(200, {"ok": True}, {}))
    resp = t.request("GET", "https://h/x", None, {"A": "b"})
    assert resp.ok
    assert t.requests[0]["headers"] == {"A": "b"}
    assert t.count("GET", "/x") == 1


def test_scripted_transport_unmatched_returns_404():
    t = ScriptedTransport()
    resp = t.request("GET", "https://h/nowhere")
    assert resp.status == 404


# -- Individual contract behaviors (M-R2) --------------------------------------

def test_auth_expiry_triggers_single_reauth():
    t = ScriptedTransport()
    t.add("GET", "/tasks/t1",
          TransportResponse(401, {"error": "expired"}, {}),
          TransportResponse(200, {"id": "t1"}, {}))
    t.add("POST", "/auth/token", TransportResponse(200, {"access_token": "fresh"}, {}))
    conn = _factory(t)
    assert conn.import_task("t1") == {"id": "t1"}
    assert conn.reauths == 1
    auths = [r["headers"].get("Authorization") for r in t.requests if r["url"].endswith("/tasks/t1")]
    assert auths == ["Bearer initial", "Bearer fresh"]


def test_persistent_auth_failure_raises():
    t = ScriptedTransport()
    t.add("GET", "/tasks/t1", TransportResponse(401, {"error": "expired"}, {}))
    t.add("POST", "/auth/token", TransportResponse(200, {"access_token": "fresh"}, {}))
    conn = _factory(t)
    with pytest.raises(ContractError):
        conn.import_task("t1")


def test_pagination_aggregates_pages():
    t = ScriptedTransport()
    t.add("GET", "/items",
          TransportResponse(200, {"items": ["a"], "next_cursor": "c2"}, {}),
          TransportResponse(200, {"items": ["b", "c"], "next_cursor": "c3"}, {}),
          TransportResponse(200, {"items": ["d"], "next_cursor": None}, {}))
    conn = _factory(t)
    assert conn.fetch_all("/items") == ["a", "b", "c", "d"]


def test_retry_backoff_increases_and_eventually_succeeds():
    t = ScriptedTransport()
    t.add("GET", "/tasks/x",
          TransportResponse(500, {}, {}),
          TransportResponse(500, {}, {}),
          TransportResponse(200, {"id": "x"}, {}))
    conn = _factory(t)
    assert conn.import_task("x") == {"id": "x"}
    assert conn.waits[0] < conn.waits[1]


def test_retry_exhaustion_raises():
    t = ScriptedTransport()
    t.add("GET", "/tasks/x", TransportResponse(500, {}, {}))
    conn = _factory(t)
    with pytest.raises(ContractError):
        conn.import_task("x")
    assert len(conn.waits) == conn.max_attempts


def test_429_respects_retry_after():
    t = ScriptedTransport()
    t.add("GET", "/tasks/x",
          TransportResponse(429, {}, {"Retry-After": "9"}),
          TransportResponse(200, {"id": "x"}, {}))
    conn = _factory(t)
    assert conn.import_task("x") == {"id": "x"}
    assert conn.waits == [9.0]


def test_duplicate_webhook_deduplicated():
    conn = _factory(ScriptedTransport())
    assert conn.handle_webhook("d1", {"e": 1}) is True
    assert conn.handle_webhook("d1", {"e": 1}) is False
    assert conn.handle_webhook("d2", {"e": 2}) is True
    with pytest.raises(ContractError):
        conn.handle_webhook("", {})


def test_malformed_response_raises_contract_error():
    t = ScriptedTransport()
    t.add("GET", "/items", TransportResponse(200, ["not", "a", "dict"], {}))
    conn = _factory(t)
    with pytest.raises(ContractError):
        conn.fetch_all("/items")


def test_idempotency_key_stable_across_retries():
    t = ScriptedTransport()
    t.add("POST", "/receipts",
          TransportResponse(500, {}, {}),
          TransportResponse(200, {"id": "r9"}, {}))
    conn = _factory(t)
    assert conn.post_receipt({"receipt_hash": "h"}) == "r9"
    keys = [r["headers"].get("Idempotency-Key") for r in t.requests if r["url"].endswith("/receipts")]
    assert len(keys) == 2 and keys[0] == keys[1] and keys[0]


def test_idempotency_key_deterministic_for_same_payload():
    conn = _factory(ScriptedTransport())
    from residual.core import digest
    expected = digest({"action": "post_receipt", "receipt": {"receipt_hash": "h"}})
    t = ScriptedTransport()
    t.add("POST", "/receipts", TransportResponse(200, {"id": "r"}, {}))
    conn = ResilientConnector("https://x.local", transport=t)
    conn.post_receipt({"receipt_hash": "h"})
    assert t.requests[0]["headers"]["Idempotency-Key"] == expected


# -- Suite + matrix (M-R3, M-R4) ----------------------------------------------

def test_reference_connector_is_certified():
    matrix = run_conformance_suite()
    assert isinstance(matrix, CertificationMatrix)
    assert matrix.certified
    assert len(matrix.results) == 7
    assert all(r.passed for r in matrix.results)


def test_matrix_json_roundtrip():
    matrix = run_conformance_suite()
    doc = json.loads(matrix.to_json())
    assert doc["certified"] is True
    assert {c["check_id"] for c in doc["checks"]} == {
        "auth_expiry", "pagination", "retry_backoff", "http_429",
        "duplicate_webhooks", "malformed_responses", "idempotency_keys",
    }


def test_matrix_markdown():
    md = run_conformance_suite().to_markdown()
    assert "| auth_expiry |" in md and "PASS" in md and md.startswith("# Connector Certification")


def test_suite_survives_broken_connector():
    """A failing connector MUST fail checks without aborting the suite (M-R3)."""

    class BrokenConnector(ResilientConnector):
        def import_task(self, external_id):
            raise ContractError("always broken")

    suite = ConformanceSuite(lambda t: BrokenConnector("https://x.local", transport=t))
    matrix = suite.run()
    assert not matrix.certified
    assert len(matrix.results) == 7  # every check still ran
    auth = next(r for r in matrix.results if r.check_id == "auth_expiry")
    assert not auth.passed and "always broken" in auth.evidence["error"]
    # unrelated checks unaffected
    webhooks = next(r for r in matrix.results if r.check_id == "duplicate_webhooks")
    assert webhooks.passed
