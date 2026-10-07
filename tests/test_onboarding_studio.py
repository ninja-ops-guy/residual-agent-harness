"""Track H (Swarm 8): Studio frontend stub contracts and stub API.

The stub API MUST serve fixtures conforming to the local WorkerContract /
WorkerReceipt stubs (mirroring SPEC-STUDIO-003, STUDIO-R9/R11), expose the
five Studio surfaces, and record HITL approval decisions in memory.
"""
from __future__ import annotations

import json
import threading
import urllib.request
from urllib.error import HTTPError

import pytest

from residual.studio_frontend.contracts import WorkerContract, WorkerReceipt
from residual.studio_frontend.stub_server import load_fixtures, serve

R11_FIELDS = {
    "receipt_id", "task_id", "attempt_id", "engine", "engine_version",
    "node_id", "input_commit", "output_artifacts", "requirement_verdicts",
    "verification", "parent_receipts", "started_at", "ended_at",
    "resource_usage", "status",
}


@pytest.fixture(scope="module")
def fixtures():
    return load_fixtures()


def test_contract_fixture_shape(fixtures):
    for raw in fixtures["contracts"]:
        contract = WorkerContract.from_dict(raw)
        assert contract.task_id
        assert contract.token_budget > 0
        assert contract.wall_clock_budget_s > 0
        assert isinstance(contract.forbidden, tuple)


def test_receipt_fixture_shape_binds_studio_r11(fixtures):
    receipts = fixtures["receipts"]
    assert receipts, "fixtures must include receipts"
    for raw in receipts:
        assert R11_FIELDS <= set(raw), f"receipt missing fields: {R11_FIELDS - set(raw)}"
        receipt = WorkerReceipt.from_dict(raw)
        assert len(receipt.hash()) == 64
    by_id = {r["receipt_id"]: r for r in receipts}
    for raw in receipts:
        if raw.get("supersedes"):
            assert raw["supersedes"] in by_id, "superseded receipt must remain queryable"


def test_timeline_derived_from_receipts(fixtures):
    timeline = fixtures["timeline"]
    assert len(timeline) == len(fixtures["receipts"])
    starts = [s["started_at"] for s in timeline]
    assert starts == sorted(starts)


def test_swarm_fixture_has_panel_metrics(fixtures):
    metrics = fixtures["swarm"]["metrics"]
    for key in ("effective_speedup", "coordination_overhead_minutes",
                "rework_rate", "verifier_rejection_rate"):
        assert key in metrics, f"STUDIO-R25 metric missing: {key}"


@pytest.fixture()
def stub_server():
    server = serve(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def _get(base, path):
    with urllib.request.urlopen(base + path, timeout=10) as res:
        return json.loads(res.read())


def test_stub_api_endpoints(stub_server):
    plan = _get(stub_server, "/api/plan")
    assert plan["requirements"] and plan["swarms"]
    assert _get(stub_server, "/api/contracts")[0]["task_id"]
    assert _get(stub_server, "/api/swarm/status")["metrics"]["effective_speedup"]
    assert R11_FIELDS <= set(_get(stub_server, "/api/evidence/receipts")[0])
    assert _get(stub_server, "/api/workers/timeline")
    assert _get(stub_server, "/api/approvals")


def test_stub_api_serves_static_ui(stub_server):
    with urllib.request.urlopen(stub_server + "/", timeout=10) as res:
        html = res.read().decode()
    assert "Residual" in html or "RESIDUAL" in html
    with urllib.request.urlopen(stub_server + "/app.js", timeout=10) as res:
        assert "api/plan" in res.read().decode()
    with pytest.raises(HTTPError) as exc:
        urllib.request.urlopen(stub_server + "/../etc/passwd", timeout=10)
    assert exc.value.code == 404


def test_approval_decision_flow(stub_server):
    approvals = _get(stub_server, "/api/approvals")
    target = next(a for a in approvals if a["status"] == "pending")

    def post(payload):
        req = urllib.request.Request(
            f"{stub_server}/api/approvals/{target['approval_id']}",
            data=json.dumps(payload).encode(), method="POST",
            headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(req, timeout=10)

    with post({"decision": "approve", "decided_by": "pytest"}) as res:
        decided = json.loads(res.read())
    assert decided["status"] == "decided"
    assert decided["decision"] == "approve"
    assert decided["decided_by"] == "pytest"
    assert decided["decided_at"]

    with pytest.raises(HTTPError) as exc:
        post({"decision": "reject"})
    assert exc.value.code == 409, "double decision MUST be rejected (HITL is one-shot)"

    req = urllib.request.Request(
        f"{stub_server}/api/approvals/approval-gate-0002",
        data=json.dumps({"decision": "maybe"}).encode(), method="POST",
        headers={"Content-Type": "application/json"})
    with pytest.raises(HTTPError) as exc:
        urllib.request.urlopen(req, timeout=10)
    assert exc.value.code == 400
