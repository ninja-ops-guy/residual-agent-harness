"""Track F tests: two-node integration, failure/reassignment, schema
version negotiation, local-first routing, mesh integration."""
from __future__ import annotations

import pytest

from residual.cluster import (Capability, ClusterError, ClusterNode,
                              LoopbackTransport, MessageKind, NodeRecord,
                              NodeRegistry, WireMessage, decode, encode,
                              negotiate_version, sign_message, verify_message)
from residual.cluster.discovery import Discovery, mdns_available


def make_node(node_id, key="cluster-key", models=("m-a",), tok=10.0, **kw):
    cap = Capability(models=models, tokens_per_second=tok,
                     context_window=4096, memory_bytes=1 << 30, gpus=1)
    node = ClusterNode(node_id, cap, key, **kw)
    node.open()
    return node


@pytest.fixture(autouse=True)
def clean_loopback():
    LoopbackTransport.reset_registry()
    yield
    LoopbackTransport.reset_registry()


# ---------------------------------------------------------------- schema
def test_wire_roundtrip_includes_schema_version():
    msg = WireMessage(kind=MessageKind.HEARTBEAT, sender_id="n1",
                      payload={"x": 1})
    raw = encode(msg)
    assert b'"schema_version"' in raw
    out = decode(raw)
    assert out.kind is MessageKind.HEARTBEAT and out.payload == {"x": 1}


def test_decode_rejects_missing_or_unsupported_version():
    with pytest.raises(ClusterError):
        decode(b'{"kind": "heartbeat"}')
    with pytest.raises(ClusterError):
        decode(b'{"kind": "heartbeat", "sender_id": "x", "schema_version": 99}')


def test_version_negotiation():
    assert negotiate_version([1]) == 1
    assert negotiate_version([1, 2, 3]) == 1  # clamp to local max
    assert negotiate_version([2, 3]) is None  # no common version


def test_hmac_auth():
    msg = sign_message("key", WireMessage(kind=MessageKind.JOIN, sender_id="n"))
    verify_message("key", msg)
    with pytest.raises(ClusterError):
        verify_message("wrong-key", msg)
    with pytest.raises(ClusterError):
        verify_message("key", WireMessage(kind=MessageKind.JOIN, sender_id="n"))


# ------------------------------------------------- two-node integration
def test_two_node_join_task_and_result():
    a = make_node("a")
    b = make_node("b")
    try:
        result = b.join(bootstrap_address=a.address)
        assert result["joined"] and result["bootstrap"] == a.address
        # Both registries know each other after JOIN/JOIN_ACK.
        assert a.registry.get("b") is not None
        assert b.registry.get("a") is not None
        assert b.negotiated_version == 1

        task = a.submit_task({"goal": "summarize"}, required_model="m-a")
        # Local-first: a is local and equally capable -> runs on a.
        assert task.state == "completed"
        assert task.assigned_node == "a"

        # Capability gap: only b advertises m-b; task routes to b.
        b_cap = b.registry.get("b")
        b.capability = Capability(models=("m-b",), tokens_per_second=5,
                                  context_window=8192)
        a.registry.upsert(NodeRecord("b", b.address, b.capability))
        task2 = a.submit_task({"goal": "code"}, required_model="m-b")
        assert task2.assigned_node == "b"
        assert task2.state == "completed"  # synchronous loopback result
        assert any(r["task_id"] == task2.task_id for r in a.receipts)
    finally:
        a.close(); b.close()


def test_leave_removes_peer_and_reassigns():
    a = make_node("a")
    b = make_node("b", models=("m-b",))
    try:
        b.join(bootstrap_address=a.address)
        assert a.registry.get("b") is not None
        b.leave()
        assert a.registry.get("b") is None
    finally:
        a.close(); b.close()


def test_wrong_cluster_key_is_dropped():
    a = make_node("a", key="key-1")
    intruder = make_node("evil", key="key-2")
    try:
        intruder.join(bootstrap_address=a.address)
        assert a.registry.get("evil") is None
    finally:
        a.close(); intruder.close()


# ------------------------------------------- failure + reassignment
def test_failure_detection_reassigns_tasks():
    a = make_node("a")
    b = make_node("b")
    try:
        b.join(bootstrap_address=a.address)

        # Pretend a task is in-flight on b (no synchronous completion).
        task = a.submit_task({"goal": "x"}, required_model="m-a")
        task.state = "assigned"
        task.assigned_node = "b"

        # b stops heartbeating: push last_heartbeat into the past.
        a.registry.heartbeat("b", at_ns=0)
        failed = a.detect_failures(now_ns=a.failure_timeout_ns + 1)
        assert failed == ["b"]
        assert a.registry.get("b").state == "failed"
        # N9-R21: task reassigned to a capable node and receipt marked.
        assert task.assigned_node == "a"
        assert task.state == "completed"
        assert any(r["task_id"] == task.task_id and r["outcome"] == "node_failed"
                   for r in a.receipts)
    finally:
        a.close(); b.close()


def test_tick_sends_heartbeats():
    a = make_node("a")
    b = make_node("b")
    try:
        b.join(bootstrap_address=a.address)
        a.registry.heartbeat("b", at_ns=0)
        a.tick(now_ns=a.heartbeat_interval_ns + 1)
        assert b.registry.get("a") is not None
        assert b.registry.get("a").last_heartbeat_ns > 0
    finally:
        a.close(); b.close()


# --------------------------------------------------------- routing
def test_local_first_routing_on_equal_capability():
    reg = NodeRegistry()
    cap = Capability(models=("m",), tokens_per_second=10.0)
    reg.upsert(NodeRecord("local", "l", cap, is_local=True))
    reg.upsert(NodeRecord("remote", "r", cap, is_local=False))
    assert reg.route("m").node_id == "local"


def test_remote_chosen_for_capability_gap():
    reg = NodeRegistry()
    reg.upsert(NodeRecord("local", "l",
                          Capability(models=("m",), tokens_per_second=10.0),
                          is_local=True))
    reg.upsert(NodeRecord("remote", "r",
                          Capability(models=("big",), tokens_per_second=50.0)))
    assert reg.route("big").node_id == "remote"
    assert reg.route("missing") is None


def test_aggregate_capacity():
    reg = NodeRegistry()
    reg.upsert(NodeRecord("n1", "a", Capability(
        models=("m1", "m2"), gpus=2, memory_bytes=8, workers=3)))
    reg.upsert(NodeRecord("n2", "b", Capability(
        models=("m2",), gpus=1, memory_bytes=4, workers=1)))
    cap = reg.aggregate_capacity()
    assert cap["nodes"] == 2 and cap["total_gpus"] == 3
    assert cap["total_models"] == 2 and cap["total_workers"] == 4
    assert cap["total_memory_bytes"] == 12


# ------------------------------------------------------------ discovery
def test_discovery_graceful_fallback():
    d = Discovery("n1", "loopback://n1")
    assert d.backend in ("mdns", "loopback")
    if not mdns_available():
        assert d.backend == "loopback"
        assert d.announce() is False


# --------------------------------------------------------- mesh bridge
def test_mesh_integration_broadcasts_results():
    import hmac, hashlib, time
    from residual.mesh.node import MeshIdentity, MeshNode

    key = b"k" * 32
    def sign(data: bytes) -> str:
        return hmac.new(key, data, hashlib.sha256).hexdigest()
    def verify(pk, data, sig) -> bool:
        return hmac.compare_digest(hmac.new(key, data, hashlib.sha256).hexdigest(), sig)

    identity = MeshIdentity(device_id="dev-a", display_name="A",
                            public_key="pk", capabilities=("m-a",),
                            address="loopback://a", joined_at_ns=time.time_ns())
    mesh = MeshNode(identity, sign, verify)
    a = make_node("a", mesh_node=mesh)
    try:
        task = a.submit_task({"goal": "g"})
        assert task.state == "completed"
        kinds = [m.kind.value for m in mesh.chat.messages]
        assert "task_result" in kinds
    finally:
        a.close()
