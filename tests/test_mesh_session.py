import hashlib
import hmac
import time

import pytest

from residual.core import ContractError
from residual.mesh import MeshIdentity, MeshNode, MeshSession


def node(name, *, verifier=None):
    key=hashlib.sha256(name.encode()).digest()
    public=f"pk-{name}"
    keys={public:key}
    verify=verifier or (lambda pk,data,sig: pk in keys and hmac.compare_digest(
        hmac.new(keys[pk],data,hashlib.sha256).hexdigest(),sig))
    sign=lambda data:hmac.new(key,data,hashlib.sha256).hexdigest()
    return MeshNode(
        MeshIdentity(f"dev-{name}",name.upper(),public,("chat",),f"loopback://{name}",time.time_ns()),
        sign,verify,
    )


def compatible_nodes(*names):
    keys={f"pk-{n}":hashlib.sha256(n.encode()).digest() for n in names}
    def verify(pk,data,sig):
        key=keys.get(pk)
        return bool(key) and hmac.compare_digest(hmac.new(key,data,hashlib.sha256).hexdigest(),sig)
    found={}
    for name in names:
        key=keys[f"pk-{name}"]
        found[name]=MeshNode(
            MeshIdentity(f"dev-{name}",name.upper(),f"pk-{name}",("chat",),f"loopback://{name}",time.time_ns()),
            lambda data,key=key:hmac.new(key,data,hashlib.sha256).hexdigest(),
            verify,
        )
    return found


def test_join_catches_up_history_before_membership():
    nodes=compatible_nodes("a","b")
    session=MeshSession("room")
    session.join(nodes["a"])
    session.chat("dev-a","one")
    session.chat("dev-a","two")
    joined=session.join(nodes["b"])
    assert joined["history_appended"]==2
    assert joined["converged"] is True
    assert nodes["a"].chat.head_hash==nodes["b"].chat.head_hash


def test_failed_late_join_rolls_back_peer_connections():
    nodes=compatible_nodes("a","b")
    session=MeshSession("room")
    session.join(nodes["a"])
    session.chat("dev-a","history")
    bad=MeshNode(
        nodes["b"].identity,
        lambda data:"bad",
        lambda *args:False,
    )
    with pytest.raises(ContractError,match="signature"):
        session.join(bad)
    assert session.members==("dev-a",)
    assert "dev-b" not in nodes["a"].peers
    assert "dev-a" not in bad.peers
    assert bad.chat.messages==()


def test_broadcast_fans_out_and_returns_delivery_receipt():
    nodes=compatible_nodes("a","b","c")
    session=MeshSession("room")
    for name in ("a","b","c"): session.join(nodes[name])
    message,receipt=session.chat("dev-b","hello")
    assert receipt.converged is True
    assert receipt.rejected==()
    assert receipt.acknowledged==("dev-a","dev-b","dev-c")
    assert all(n.chat.messages[-1].message_id==message.message_id for n in nodes.values())


def test_divergence_blocks_future_broadcast_instead_of_picking_winner():
    nodes=compatible_nodes("a","b")
    session=MeshSession("room")
    session.join(nodes["a"]);session.join(nodes["b"])
    nodes["a"].send_message("chat",content="left-only")
    with pytest.raises(ContractError,match="divergent"):
        session.chat("dev-b","must not auto-merge")


def test_rejected_delivery_degrades_session():
    nodes=compatible_nodes("a","b")
    session=MeshSession("room")
    session.join(nodes["a"]);session.join(nodes["b"])
    nodes["b"].revoke_device("dev-a","host")
    _,receipt=session.chat("dev-a","will be rejected")
    assert receipt.converged is False
    assert receipt.rejected==("dev-b",)
    assert session.status()["degraded"] is True
    with pytest.raises(ContractError,match="divergent"):
        session.chat("dev-a","blocked after degrade")


def test_leave_disconnects_member_without_erasing_history():
    nodes=compatible_nodes("a","b")
    session=MeshSession("room")
    session.join(nodes["a"]);session.join(nodes["b"])
    session.chat("dev-a","before leave")
    result=session.leave("dev-b")
    assert result["members"]==["dev-a"]
    assert session.status()["message_count"]==1


def test_membership_epoch_binds_delivery_receipts():
    nodes=compatible_nodes("a","b")
    session=MeshSession("room")
    assert session.status()["membership_epoch"]==0
    assert session.join(nodes["a"])["membership_epoch"]==1
    assert session.join(nodes["b"])["membership_epoch"]==2
    _,receipt=session.chat("dev-a","epoch-bound")
    assert receipt.membership_epoch==2
    assert receipt.to_dict()["membership_epoch"]==2
    assert session.leave("dev-b")["membership_epoch"]==3
    assert session.status()["membership_epoch"]==3


def test_duplicate_member_and_unknown_author_fail_closed():
    nodes=compatible_nodes("a")
    session=MeshSession("room")
    session.join(nodes["a"])
    with pytest.raises(ContractError,match="already joined"):
        session.join(nodes["a"])
    with pytest.raises(ContractError,match="not joined"):
        session.chat("dev-missing","x")
