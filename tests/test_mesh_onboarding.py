"""Onboarding qualification for the agentic cluster + signed mesh chat."""
from __future__ import annotations
import hashlib
import hmac
import time
import pytest
from residual.cluster import Capability, ClusterNode, LoopbackTransport
from residual.core import ContractError
from residual.mesh import MeshIdentity, MeshMessage, MeshMessageKind, MeshNode

@pytest.fixture(autouse=True)
def clean_loopback():
    LoopbackTransport.reset_registry()
    yield
    LoopbackTransport.reset_registry()

def cluster_node(node_id: str, key: str = "mesh-onboarding-key", models=("qwen",)):
    node = ClusterNode(node_id, Capability(models=models, tokens_per_second=10.0, context_window=8192), key)
    node.open()
    return node

def identity(name: str) -> MeshIdentity:
    return MeshIdentity(
        device_id=f"dev-{name}", display_name=name.upper(), public_key=f"pk-{name}",
        capabilities=("qwen", "review"), address=f"loopback://mesh-{name}",
        joined_at_ns=time.time_ns(),
    )

def signer(name: str):
    key = hashlib.sha256(name.encode()).digest()
    def sign(data: bytes) -> str:
        return hmac.new(key, data, hashlib.sha256).hexdigest()
    return sign

def verifier(keys: dict[str, bytes]):
    def verify(public_key: str, data: bytes, signature: str) -> bool:
        key = keys.get(public_key)
        return bool(key) and hmac.compare_digest(
            hmac.new(key, data, hashlib.sha256).hexdigest(), signature
        )
    return verify

def mesh_nodes(*names: str):
    keys = {f"pk-{n}": hashlib.sha256(n.encode()).digest() for n in names}
    verify = verifier(keys)
    return {name: MeshNode(identity(name), signer(name), verify) for name in names}

def test_explicit_bootstrap_requires_authenticated_ack():
    a = cluster_node("a", key="right")
    intruder = cluster_node("intruder", key="wrong")
    try:
        result = intruder.join(bootstrap_address=a.address)
        assert result["joined"] is False
        assert result["bootstrap"] is None
        assert intruder.negotiated_version is None
        assert a.registry.get("intruder") is None
    finally:
        a.close(); intruder.close()

def test_unreachable_explicit_bootstrap_does_not_claim_joined():
    node = cluster_node("a")
    try:
        result = node.join(bootstrap_address="loopback://missing")
        assert result["joined"] is False
        assert result["bootstrap"] is None
    finally:
        node.close()

def test_first_node_can_form_standalone_cluster():
    node = cluster_node("root")
    try:
        result = node.join()
        assert result["joined"] is True
        assert result["bootstrap"] is None
        assert node.registry.get("root") is not None
    finally:
        node.close()

def test_two_node_join_negotiates_version_and_capabilities():
    a = cluster_node("a", models=("small",))
    b = cluster_node("b", models=("large",))
    try:
        result = b.join(bootstrap_address=a.address)
        assert result["joined"] is True
        assert result["bootstrap"] == a.address
        assert b.negotiated_version == 1
        assert a.registry.get("b").capability.models == ("large",)
        assert b.registry.get("a").capability.models == ("small",)
    finally:
        a.close(); b.close()

def test_third_node_receives_existing_roster_during_onboarding():
    a = cluster_node("a"); b = cluster_node("b"); c = cluster_node("c")
    try:
        assert b.join(bootstrap_address=a.address)["joined"]
        assert c.join(bootstrap_address=b.address)["joined"]
        assert c.registry.get("a") is not None
        assert c.registry.get("b") is not None
        assert a.registry.get("c") is None
    finally:
        a.close(); b.close(); c.close()

def test_leave_then_rejoin_restores_membership():
    a = cluster_node("a"); b = cluster_node("b")
    try:
        assert b.join(bootstrap_address=a.address)["joined"]
        assert a.registry.get("b") is not None
        assert b.leave()["left"] is True
        assert a.registry.get("b") is None
        assert b.join(bootstrap_address=a.address)["joined"] is True
        assert a.registry.get("b") is not None
        assert b.registry.get("b") is not None
        assert b.registry.get("b").is_local is True
    finally:
        a.close(); b.close()

def test_joined_remote_can_receive_task_immediately():
    a = cluster_node("a", models=("local",))
    b = cluster_node("b", models=("special",))
    try:
        assert b.join(bootstrap_address=a.address)["joined"]
        task = a.submit_task({"goal": "onboarding smoke"}, required_model="special")
        assert task.assigned_node == "b"
        assert task.state == "completed"
        assert task.receipt["outcome"] == "completed"
    finally:
        a.close(); b.close()

def test_late_joiner_must_replay_history_before_live_messages():
    nodes = mesh_nodes("a", "b"); a, b = nodes["a"], nodes["b"]
    b.connect_peer(a.identity)
    first = a.send_message(MeshMessageKind.CHAT, content="before join")
    second = a.send_message(MeshMessageKind.CHAT, content="still before join")
    live = a.send_message(MeshMessageKind.CHAT, content="live")
    assert b.receive_message(live) is False
    b2 = mesh_nodes("a", "b")["b"]; b2.connect_peer(a.identity)
    assert b2.sync_history((first, second)) == 2
    assert b2.receive_message(live) is True
    assert [m.content for m in b2.chat.messages] == ["before join", "still before join", "live"]
    assert b2.chat.verify()

def test_sync_history_is_idempotent_for_an_identical_prefix():
    nodes = mesh_nodes("a", "b"); a, b = nodes["a"], nodes["b"]; b.connect_peer(a.identity)
    history = (a.send_message(MeshMessageKind.CHAT, content="one"),
               a.send_message(MeshMessageKind.CHAT, content="two"))
    assert b.sync_history(history) == 2
    assert b.sync_history(history) == 0
    assert len(b.chat.messages) == 2

def test_sync_history_rejects_forked_existing_prefix():
    nodes = mesh_nodes("a", "b"); a, b = nodes["a"], nodes["b"]; b.connect_peer(a.identity)
    msg = a.send_message(MeshMessageKind.CHAT, content="canonical")
    assert b.sync_history((msg,)) == 1
    fork = MeshMessage(message_id=msg.message_id, author_id=msg.author_id,
        timestamp_ns=msg.timestamp_ns, kind=msg.kind, content="tampered",
        payload={}, signature=msg.signature, prev_hash=msg.prev_hash)
    with pytest.raises(ContractError, match="history prefix"):
        b.sync_history((fork,))

def test_sync_history_rejects_unknown_author():
    a = mesh_nodes("a")["a"]
    msg = a.send_message(MeshMessageKind.CHAT, content="hello")
    b = mesh_nodes("b")["b"]
    with pytest.raises(ContractError, match="unknown history author"):
        b.sync_history((msg,))

def test_sync_history_rejects_invalid_signature():
    nodes = mesh_nodes("a", "b"); a, b = nodes["a"], nodes["b"]; b.connect_peer(a.identity)
    msg = a.send_message(MeshMessageKind.CHAT, content="hello")
    bad = MeshMessage(message_id=msg.message_id, author_id=msg.author_id,
        timestamp_ns=msg.timestamp_ns, kind=msg.kind, content=msg.content,
        payload=msg.payload, signature="0" * 64, prev_hash=msg.prev_hash)
    with pytest.raises(ContractError, match="signature"):
        b.sync_history((bad,))

def test_invalid_history_snapshot_does_not_partially_advance_head():
    nodes = mesh_nodes("a", "b"); a, b = nodes["a"], nodes["b"]; b.connect_peer(a.identity)
    one = a.send_message(MeshMessageKind.CHAT, content="one")
    two = a.send_message(MeshMessageKind.CHAT, content="two")
    bad_two = MeshMessage(
        message_id=two.message_id, author_id=two.author_id,
        timestamp_ns=two.timestamp_ns, kind=two.kind, content=two.content,
        payload=two.payload, signature="bad", prev_hash=two.prev_hash,
    )
    with pytest.raises(ContractError, match="signature"):
        b.sync_history((one, bad_two))
    assert b.chat.messages == ()
    assert b.chat.head_hash == "GENESIS"


def test_code_like_chat_remains_inert_text():
    nodes = mesh_nodes("a", "b"); a, b = nodes["a"], nodes["b"]; b.connect_peer(a.identity)
    text = "```python\\nprint(42)\\n```"
    msg = a.send_message(MeshMessageKind.CHAT, content=text)
    assert msg.payload == {}
    assert b.receive_message(msg) is True
    assert b.chat.messages[-1].content == text

def test_out_of_order_history_fails_closed():
    nodes = mesh_nodes("a", "b"); a, b = nodes["a"], nodes["b"]; b.connect_peer(a.identity)
    one = a.send_message(MeshMessageKind.CHAT, content="one")
    two = a.send_message(MeshMessageKind.CHAT, content="two")
    with pytest.raises(ContractError, match="chain break"):
        b.sync_history((two, one))

def test_peer_cannot_reuse_local_device_identity():
    a = mesh_nodes("a")["a"]
    impostor = MeshIdentity(
        device_id=a.identity.device_id, display_name="impostor",
        public_key="different-key", capabilities=(),
        address="loopback://impostor", joined_at_ns=time.time_ns(),
    )
    with pytest.raises(ContractError, match="local device identity"):
        a.connect_peer(impostor)

def test_key_pinning_blocks_silent_identity_replacement():
    b = mesh_nodes("b")["b"]; original = identity("a"); b.connect_peer(original)
    replacement = MeshIdentity(device_id=original.device_id, display_name="A replaced",
        public_key="different-key", capabilities=original.capabilities,
        address=original.address, joined_at_ns=original.joined_at_ns)
    with pytest.raises(ContractError, match="re-admission"):
        b.connect_peer(replacement)

def test_revoked_peer_cannot_rejoin_or_send():
    nodes = mesh_nodes("a", "b"); a, b = nodes["a"], nodes["b"]; b.connect_peer(a.identity)
    b.revoke_device(a.identity.device_id, "legacy-host-arg")
    with pytest.raises(ContractError, match="revoked"):
        b.connect_peer(a.identity)
    msg = a.send_message(MeshMessageKind.CHAT, content="after revoke")
    assert b.receive_message(msg) is False

def test_chat_payload_is_inert_text_only():
    with pytest.raises(ContractError, match="chat messages cannot carry structured payload"):
        MeshMessage(message_id="m1", author_id="dev-a", timestamp_ns=1,
            kind=MeshMessageKind.CHAT, content="hello", payload={"tool": "shell.exec"})

def test_mesh_payload_is_deeply_frozen_after_construction():
    proposal = {"goal": {"objective": "x"}}
    msg = MeshMessage(message_id="m1", author_id="dev-a", timestamp_ns=1,
        kind=MeshMessageKind.TASK_PROPOSAL, payload=proposal)
    proposal["goal"]["objective"] = "mutated"
    assert msg.payload["goal"]["objective"] == "x"
    with pytest.raises(TypeError):
        msg.payload["goal"]["objective"] = "again"

def test_oversized_chat_and_payload_are_rejected():
    with pytest.raises(ContractError):
        MeshMessage("m", "a", 1, MeshMessageKind.CHAT, content="x" * 8001)
    with pytest.raises(ContractError):
        MeshMessage("m", "a", 1, MeshMessageKind.TASK_PROPOSAL,
                    payload={"blob": "x" * 24001})

def test_large_backlog_catchup_preserves_exact_chain():
    nodes = mesh_nodes("a", "b"); a, b = nodes["a"], nodes["b"]; b.connect_peer(a.identity)
    for index in range(128):
        a.send_message(MeshMessageKind.CHAT, content=f"message-{index}")
    assert b.sync_history(a.chat.messages) == 128
    assert len(b.chat.messages) == 128
    assert b.chat.head_hash == a.chat.head_hash
    assert b.chat.verify()


def test_concurrent_same_head_messages_are_detected_as_fork_not_auto_merged():
    nodes = mesh_nodes("a", "b"); a, b = nodes["a"], nodes["b"]
    a.connect_peer(b.identity); b.connect_peer(a.identity)
    seed = a.send_message(MeshMessageKind.CHAT, content="seed")
    assert b.receive_message(seed)
    left = a.send_message(MeshMessageKind.CHAT, content="left")
    right = b.send_message(MeshMessageKind.CHAT, content="right")
    assert left.prev_hash == right.prev_hash
    assert a.receive_message(right) is False
    assert b.receive_message(left) is False
    assert a.chat.head_hash != b.chat.head_hash
    assert a.chat.verify() and b.chat.verify()

def test_three_member_conversation_replays_then_continues():
    nodes = mesh_nodes("a", "b", "c"); a,b,c = nodes["a"],nodes["b"],nodes["c"]
    a.connect_peer(b.identity); b.connect_peer(a.identity)
    m1 = a.send_message(MeshMessageKind.CHAT, content="a1"); assert b.receive_message(m1)
    m2 = b.send_message(MeshMessageKind.CHAT, content="b1"); assert a.receive_message(m2)
    assert a.chat.head_hash == b.chat.head_hash
    c.connect_peer(a.identity); c.connect_peer(b.identity)
    assert c.sync_history(a.chat.messages) == 2
    m3 = a.send_message(MeshMessageKind.CHAT, content="a2")
    assert b.receive_message(m3); assert c.receive_message(m3)
    assert a.chat.head_hash == b.chat.head_hash == c.chat.head_hash
    assert c.chat.verify()
