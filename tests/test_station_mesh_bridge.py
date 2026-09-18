import hashlib
import hmac
import tempfile
import time

from residual.mesh import MeshIdentity, MeshNode, MeshSession
from residual.mesh.station_bridge import StationMeshBridge
from residual.station.service import Station, demo_spec


def session_nodes():
    keys={
        "pk-station":hashlib.sha256(b"station").digest(),
        "pk-peer":hashlib.sha256(b"peer").digest(),
    }
    def verify(pk,data,sig):
        key=keys.get(pk)
        return bool(key) and hmac.compare_digest(
            hmac.new(key,data,hashlib.sha256).hexdigest(),sig
        )
    nodes={}
    for name in ("station","peer"):
        key=keys[f"pk-{name}"]
        nodes[name]=MeshNode(
            MeshIdentity(
                f"dev-{name}",name.upper(),f"pk-{name}",("chat",),
                f"loopback://{name}",time.time_ns(),
            ),
            lambda data,key=key:hmac.new(key,data,hashlib.sha256).hexdigest(),
            verify,
        )
    room=MeshSession("station-room")
    room.join(nodes["station"])
    room.join(nodes["peer"])
    return room,nodes


def test_station_events_mirror_as_signed_inert_chat():
    with tempfile.TemporaryDirectory() as tmp:
        station=Station(tmp)
        pid=station.create(demo_spec(),demo=True)["project_id"]
        room,nodes=session_nodes()
        bridge=StationMeshBridge(station,pid,room,"dev-station")

        result=bridge.mirror_station_events()
        assert result["converged"] is True
        assert len(result["mirrored"])==1
        assert nodes["station"].chat.head_hash==nodes["peer"].chat.head_hash
        message=nodes["peer"].chat.messages[-1]
        assert message.payload=={}
        assert "[project.created]" in message.content
        assert "event 1" in message.content


def test_verified_peer_chat_enters_station_only_as_project_note():
    with tempfile.TemporaryDirectory() as tmp:
        station=Station(tmp)
        pid=station.create(demo_spec(),demo=True)["project_id"]
        before=[task["state"] for task in station.store.project(pid)["tasks"]]
        room,_=session_nodes()
        bridge=StationMeshBridge(station,pid,room,"dev-station")

        message,receipt=room.chat("dev-peer","Please check the queued work.")
        assert receipt.converged is True
        result=bridge.ingest_peer_chat(message.message_id)
        assert result["ingested"] is True

        after=[task["state"] for task in station.store.project(pid)["tasks"]]
        assert after==before
        event=station.store.events(pid)[-1]
        assert event["event_type"]=="project.note"
        assert event["actor"]=="mesh:dev-peer"
        assert event["data"]["message"]=="Please check the queued work."
        assert event["data"]["mesh_message_id"]==message.message_id


def test_peer_chat_ingest_is_durable_idempotent_and_does_not_echo():
    with tempfile.TemporaryDirectory() as tmp:
        station=Station(tmp)
        pid=station.create(demo_spec(),demo=True)["project_id"]
        room,nodes=session_nodes()
        bridge=StationMeshBridge(station,pid,room,"dev-station")
        bridge.mirror_station_events()

        message,_=room.chat("dev-peer","One retained note.")
        first=bridge.ingest_peer_chat(message.message_id)
        second=bridge.ingest_peer_chat(message.message_id)
        assert first["ingested"] is True
        assert second["duplicate"] is True
        before=len(nodes["station"].chat.messages)

        note_event=station.store.events(pid)[-1]
        mirrored=bridge.mirror_station_events(after_seq=note_event["seq"]-1)
        assert mirrored["mirrored"]==[]
        assert mirrored["through_seq"]==note_event["seq"]
        assert len(nodes["station"].chat.messages)==before


def test_triage_workflow_facts_mirror_without_granting_mesh_authority():
    with tempfile.TemporaryDirectory() as tmp:
        station=Station(tmp)
        pid=station.create(demo_spec(),demo=True)["project_id"]
        room,nodes=session_nodes()
        bridge=StationMeshBridge(station,pid,room,"dev-station")
        initial=bridge.mirror_station_events()
        station.triage(pid)
        result=bridge.mirror_station_events(after_seq=initial["through_seq"])
        assert result["mirrored"]
        text="\n".join(message.content for message in nodes["peer"].chat.messages)
        assert "[task.transition]" in text
        assert "-> ready" in text
        assert all(message.payload=={} for message in nodes["peer"].chat.messages)


def test_bridge_status_states_authority_boundary():
    with tempfile.TemporaryDirectory() as tmp:
        station=Station(tmp)
        pid=station.create(demo_spec(),demo=True)["project_id"]
        room,_=session_nodes()
        bridge=StationMeshBridge(station,pid,room,"dev-station")
        status=bridge.status()
        assert status["mesh"]["converged"] is True
        assert status["authority"]=={
            "chat_executes_actions":False,
            "peer_chat_station_effect":"project.note only",
            "workflow_owner":"station",
            "worker_transport":"station-worker-api",
        }
