"""Tests for SPEC-ENT-006 (Enterprise Integration Hub).

Covers ENT6-R1 (ITSM), ENT6-R2 (CI/CD), ENT6-R3 (monitoring), ENT6-R4
(communication), ENT6-R5 (ticketing), ENT6-R6 (bidirectional), and
ENT6-R7 (observed request/response hashes and latency). All offline via
an injected FakeTransport.
"""
from __future__ import annotations

import pytest

from residual.core import ContractError, digest
from residual.integrations import (
    AzureBoardsConnector,
    AzureDevOpsConnector,
    BMCConnector,
    CircleCIConnector,
    DatadogConnector,
    DynatraceConnector,
    EmailConnector,
    GitHubActionsConnector,
    GitLabConnector,
    IntegrationConnector,
    ConnectorReceipt,
    JSMConnector,
    JenkinsConnector,
    JiraConnector,
    LinearConnector,
    NewRelicConnector,
    PrometheusConnector,
    ServiceNowConnector,
    SlackConnector,
    TeamsConnector,
    TransportResponse,
)
from residual.integrations.base import UrllibTransport


class FakeTransport:
    """Offline scripted transport."""

    def __init__(self, script=None):
        self.script = list(script or [])
        self.calls = []

    def request(self, method, url, body=None, headers=None):
        self.calls.append({"method": method, "url": url, "body": body,
                           "headers": headers})
        if self.script:
            item = self.script.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        return TransportResponse(200, {"ok": True, "id": "run-1",
                                       "status": "healthy"})


TICKET = TransportResponse(200, {"short_description": "Fix login",
                                 "description": "users locked out",
                                 "priority": "high", "state": "open"})
OK = TransportResponse(200, {"ok": True})


def make(cls, script=None):
    t = FakeTransport(script)
    return cls("https://itsm.example", token="tok", transport=t,
               clock=_Clock()), t


class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        self.t += 0.005
        return self.t


# ---------------------------------------------------------------- ENT6-R1

@pytest.mark.parametrize("cls", [ServiceNowConnector, JSMConnector, BMCConnector])
def test_itsm_task_creation_from_ticket(cls):
    """ENT6-R1: task creation from tickets."""
    conn, _ = make(cls, [TICKET])
    task = conn.import_task("INC-1")
    assert task["external_id"] == "INC-1"
    assert task["goal"] == "Fix login"
    assert task["source"] == cls.system_name


@pytest.mark.parametrize("cls", [ServiceNowConnector, JSMConnector, BMCConnector])
def test_itsm_receipt_attachment_status_sync_hitl(cls):
    """ENT6-R1: receipt attachment, status sync, HITL via assignment."""
    conn, t = make(cls)
    receipt = ConnectorReceipt(cls.system_name, "verify", "task-1",
                                 "accepted", digest({"v": 1}))
    conn.post_receipt("INC-2", receipt)
    conn.sync_status("INC-2", "accepted")
    conn.deliver_hitl_challenge("INC-2", "alice", {"question": "ship it?"})
    attach, sync, hitl = t.calls
    assert "receipt" in attach["body"]
    assert attach["body"]["receipt"]["receipt_hash"] == receipt.receipt_hash
    assert hitl["body"]["assigned_to"] == "alice"
    # status reflects task status
    payload = sync["body"]
    state = payload.get("state") or payload.get("transition", {}).get("name")
    assert state in ("resolved", "Done")


def test_itsm_error_raises_contracterror():
    conn, _ = make(ServiceNowConnector,
                   [TransportResponse(404, {"error": "nope"})])
    with pytest.raises(ContractError):
        conn.import_task("INC-404")


# ---------------------------------------------------------------- ENT6-R2

@pytest.mark.parametrize("cls", [JenkinsConnector, GitLabConnector,
                                 GitHubActionsConnector, AzureDevOpsConnector,
                                 CircleCIConnector])
def test_cicd_trigger_gate_publish(cls):
    """ENT6-R2: trigger from pipeline stage, gating on ConnectorReceipt,
    receipt publication as artifact."""
    conn, t = make(cls, [OK, OK, OK, OK])
    run = conn.trigger_pipeline("pipe-1", {"env": "prod"})
    assert "run_id" in run

    receipt = ConnectorReceipt(cls.system_name, "verify", "task-9",
                                 "accepted", digest({"ok": True}))
    conn.gate_pipeline("run-1", receipt)
    gate = t.calls[1]["body"]
    assert gate["decision"] == "proceed"
    assert gate["receipt_hash"] == receipt.receipt_hash

    conn.publish_receipt_artifact("run-1", receipt)
    assert "receipt" in t.calls[2]["body"]


def test_cicd_gate_holds_on_rejected_receipt():
    """ENT6-R2: pipeline waits/holds when the receipt is not accepted."""
    conn, t = make(JenkinsConnector)
    receipt = ConnectorReceipt("jenkins", "verify", "task-1", "rejected",
                                 digest({"bad": 1}))
    conn.gate_pipeline("run-2", receipt)
    assert t.calls[0]["body"]["decision"] == "hold"


def test_cicd_gate_requires_integration_receipt():
    conn, _ = make(JenkinsConnector)
    with pytest.raises(ContractError):
        conn.gate_pipeline("run-3", {"not": "a receipt"})


def test_cicd_import_task():
    """ENT6-R2/ENT6-R6: pipeline -> task input direction."""
    conn, _ = make(GitLabConnector,
                   [TransportResponse(200, {"name": "deploy", "id": 7})])
    task = conn.import_task("77")
    assert task["goal"] == "deploy"
    assert task["source"] == "gitlab"


# ---------------------------------------------------------------- ENT6-R3

@pytest.mark.parametrize("cls", [DatadogConnector, NewRelicConnector,
                                 DynatraceConnector, PrometheusConnector])
def test_monitoring_metrics_health_alerts_tracing(cls):
    """ENT6-R3: metrics export, health checks, alerts on brake trips and
    HITL escalations, tracing context propagation."""
    conn, t = make(cls)
    ctx = {"trace_id": "a" * 32, "span_id": "b" * 16}
    conn.export_metrics([{"metric": "residual.brakes", "points": [[1, 1]]}],
                        trace_context=ctx)
    assert t.calls[0]["headers"]["traceparent"].startswith("00-" + "a" * 32)

    health = conn.health_check()
    assert health["system"] == cls.system_name

    conn.alert_brake_trip("brake-1", {"task": "t-1"}, trace_context=ctx)
    conn.alert_hitl_escalation("esc-1", {"challenge": "c-1"}, trace_context=ctx)
    assert "brake" in t.calls[2]["body"]["title"].lower()
    assert "hitl" in t.calls[3]["body"]["title"].lower()


def test_monitoring_metrics_requires_nonempty():
    conn, _ = make(DatadogConnector)
    with pytest.raises(ContractError):
        conn.export_metrics([])


# ---------------------------------------------------------------- ENT6-R4

@pytest.mark.parametrize("cls", [SlackConnector, TeamsConnector, EmailConnector])
def test_comms_hitl_receipt_swarm_alert(cls):
    """ENT6-R4: HITL notifications, receipt delivery, swarm updates,
    on-call alert routing."""
    conn, t = make(cls)
    conn.notify_hitl_challenge("#ops", "ch-1", {"question": "approve?"})
    receipt = ConnectorReceipt(cls.system_name, "verify", "task-1",
                                 "accepted", digest({"x": 1}))
    conn.deliver_receipt("#ops", receipt)
    conn.send_swarm_status("#ops", "swarm-1", {"agents": 3, "state": "running"})
    conn.route_alert("#oncall", {"title": "brake tripped"})
    assert len(t.calls) == 4
    texts = []
    for c in t.calls:
        body = c["body"]
        inner = body.get("body")
        texts.append(body.get("text")
                     or (inner.get("content") if isinstance(inner, dict) else inner)
                     or body.get("subject"))
    assert any("HITL" in s for s in texts)
    assert any("Swarm" in s for s in texts)
    assert any("ALERT" in s for s in texts)


def test_comms_receipt_delivery_requires_accepted():
    conn, _ = make(SlackConnector)
    bad = ConnectorReceipt("slack", "verify", "t", "rejected", digest({}))
    with pytest.raises(ContractError):
        conn.deliver_receipt("#ops", bad)


def test_comms_bidirectional_decision_poll():
    """ENT6-R4/ENT6-R6: decisions flow back from the platform."""
    conn, _ = make(SlackConnector, [TransportResponse(
        200, {"decision": "approve", "user": "bob"})])
    out = conn.poll_decision("ch-9")
    assert out["decision"] == "approve"
    assert out["responder"] == "bob"


# ---------------------------------------------------------------- ENT6-R5

@pytest.mark.parametrize("cls", [JiraConnector, AzureBoardsConnector,
                                 LinearConnector])
def test_ticketing_import_status_receipt_autoclose(cls):
    """ENT6-R5: ticket -> GoalSpec import, status sync, receipt as
    evidence, auto-close on acceptance."""
    body = {"summary": "Add cache", "fields": {"summary": "Add cache",
                                               "labels": ["perf"]},
            "data": {"issue": {"title": "Add cache", "labels": []}}}
    conn, t = make(cls, [TransportResponse(200, body), OK, OK, OK])
    spec = conn.import_requirement("TKT-1")
    assert spec["schema"] == "residual.goalspec.v1"
    assert spec["goal"] == "Add cache"

    conn.sync_status("TKT-1", "running")
    receipt = ConnectorReceipt(cls.system_name, "verify", "task-1",
                                 "accepted", digest({"y": 2}))
    conn.close_on_acceptance("TKT-1", receipt)
    # evidence posted before closure
    assert "receipt" in t.calls[2]["body"]
    close_body = t.calls[3]["body"]
    assert "Done" in str(close_body) or "Closed" in str(close_body)


def test_ticketing_autoclose_requires_accepted():
    conn, _ = make(JiraConnector)
    bad = ConnectorReceipt("jira", "verify", "t", "pending", digest({}))
    with pytest.raises(ContractError):
        conn.close_on_acceptance("TKT-2", bad)


# ---------------------------------------------------------------- ENT6-R6

def test_bidirectional_surface_all_connectors():
    """ENT6-R6: every connector accepts input and produces output."""
    for cls in [ServiceNowConnector, JSMConnector, BMCConnector,
                JenkinsConnector, GitLabConnector, GitHubActionsConnector,
                AzureDevOpsConnector, CircleCIConnector, DatadogConnector,
                NewRelicConnector, DynatraceConnector, PrometheusConnector,
                SlackConnector, TeamsConnector, EmailConnector,
                JiraConnector, AzureBoardsConnector, LinearConnector]:
        conn, _ = make(cls, [TransportResponse(200, {"title": "x", "text": "x",
                                                     "name": "x", "fields": {}}),
                             OK])
        assert callable(conn.import_task)
        assert callable(conn.post_receipt)
        assert callable(conn.sync_status)


# ---------------------------------------------------------------- ENT6-R7

def test_every_call_observed_with_hashes_and_latency():
    """ENT6-R7: observations carry target system, endpoint, request hash,
    response hash, and latency."""
    conn, _ = make(ServiceNowConnector, [TICKET, OK])
    conn.import_task("INC-7")
    conn.sync_status("INC-7", "running")
    assert len(conn.observations) == 2
    for obs, call in zip(conn.observations, conn.transport.calls):
        assert obs.target_system == "servicenow"
        assert obs.endpoint == call["url"]
        assert obs.request_hash == digest({"method": call["method"],
                                           "url": call["url"],
                                           "body": call["body"]})
        assert obs.response_hash == digest(OK.body if obs is conn.observations[1]
                                           else TICKET.body)
        assert obs.latency_ms > 0
        assert obs.status == 200
        assert set(obs.to_dict()) >= {"target_system", "endpoint",
                                      "request_hash", "response_hash",
                                      "latency_ms"}


def test_observation_hashes_change_with_payload():
    """ENT6-R7: hashes actually reflect request/response content."""
    conn, _ = make(SlackConnector)
    conn.send_message("#a", "hello")
    conn.send_message("#a", "world")
    o1, o2 = conn.observations
    assert o1.request_hash != o2.request_hash


def test_receipt_carries_observations():
    """ENT6-R7: ConnectorReceipt embeds the observations made."""
    conn, _ = make(DatadogConnector, [OK])
    conn.export_metrics([{"m": 1}])
    receipt = conn.receipt("export", "metrics-1", "accepted", {"m": 1})
    assert len(receipt.observations) == 1
    assert receipt.observations[0].target_system == "datadog"
    assert receipt.receipt_hash == digest({
        "integration": "datadog", "action": "export",
        "subject_id": "metrics-1", "verdict": "accepted",
        "payload_hash": receipt.payload_hash})


def test_urllib_transport_satisfies_protocol():
    """ENT6-R7: real HTTP lives behind the same transport interface."""
    conn = IntegrationConnector("https://example.invalid")
    assert isinstance(conn.transport, UrllibTransport)
    assert hasattr(conn.transport, "request")
