"""Station <-> MeshSession bridge performance experiment."""
from __future__ import annotations

import hashlib
import hmac
import statistics
import tempfile
import time
from typing import Any

from residual.core import digest
from residual.mesh import MeshIdentity, MeshNode, MeshSession
from residual.mesh.station_bridge import StationMeshBridge
from residual.station.service import Station, demo_spec


def _room(member_count: int) -> tuple[MeshSession, list[MeshNode]]:
    if not 2 <= member_count <= 16:
        raise ValueError("member_count must be 2..16")
    keys={
        f"pk-{index}":hashlib.sha256(f"bridge-{index}".encode()).digest()
        for index in range(member_count)
    }
    def verify(public_key,data,signature):
        key=keys.get(public_key)
        return bool(key) and hmac.compare_digest(
            hmac.new(key,data,hashlib.sha256).hexdigest(),signature
        )
    room=MeshSession("station-bridge-benchmark")
    nodes=[]
    for index in range(member_count):
        key=keys[f"pk-{index}"]
        node=MeshNode(
            MeshIdentity(
                f"dev-{index}",
                f"P{index}",
                f"pk-{index}",
                ("chat",),
                f"loopback://bridge-{index}",
                time.time_ns(),
            ),
            lambda data,key=key:hmac.new(key,data,hashlib.sha256).hexdigest(),
            verify,
        )
        room.join(node)
        nodes.append(node)
    return room,nodes


def _trial(member_count: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="residual-station-mesh-bridge-") as tmp:
        station=Station(tmp)
        pid=station.create(demo_spec(),demo=True)["project_id"]
        result=station.batch(pid)
        if result["integrated"]!=3:
            raise RuntimeError("demo workload did not fully integrate before bridge measurement")

        room,nodes=_room(member_count)
        bridge=StationMeshBridge(station,pid,room,"dev-0")
        event_count=len(station.store.events(pid,0,100000))

        mirror_started=time.perf_counter_ns()
        mirrored=bridge.mirror_station_events(after_seq=0,limit=500)
        mirror_finished=time.perf_counter_ns()
        if len(mirrored["mirrored"])!=event_count:
            raise RuntimeError("bridge did not mirror the complete Station event stream")
        if not mirrored["converged"]:
            raise RuntimeError("bridge room diverged while mirroring Station events")

        note_text="peer benchmark note"
        note_started=time.perf_counter_ns()
        message,receipt=room.chat("dev-1",note_text)
        if not receipt.converged:
            raise RuntimeError("peer chat did not converge")
        ingested=bridge.ingest_peer_chat(message.message_id)
        note_finished=time.perf_counter_ns()
        if not ingested["ingested"]:
            raise RuntimeError("peer chat was not ingested")
        if any(task["state"]!="integrated" for task in station.store.project(pid)["tasks"]):
            raise RuntimeError("peer chat changed Station workflow authority")

        mirror_ms=(mirror_finished-mirror_started)/1_000_000.0
        note_ms=(note_finished-note_started)/1_000_000.0
        replica_updates=event_count*member_count
        return {
            "members":member_count,
            "station_events":event_count,
            "mirrored_messages":len(mirrored["mirrored"]),
            "mirror_ms":mirror_ms,
            "mirror_messages_s":event_count/(mirror_ms/1000.0),
            "mirror_replica_updates_s":replica_updates/(mirror_ms/1000.0),
            "peer_note_roundtrip_ms":note_ms,
            "converged":room.converged(),
            "message_count":room.status()["message_count"],
            "station_tasks_remained_integrated":True,
            "mesh_head":nodes[0].chat.head_hash,
            "station_event_head":station.store.events(pid,0,100000)[-1]["hash"],
        }


def run_station_mesh_bridge_benchmark(
    *,
    member_counts: tuple[int,...]=(2,4,8),
    repeats: int=3,
) -> dict[str,Any]:
    if not member_counts or len(member_counts)!=len(set(member_counts)):
        raise ValueError("member_counts must be unique and nonempty")
    if any(not 2<=count<=16 for count in member_counts) or repeats<1:
        raise ValueError("invalid bridge benchmark bounds")
    runs=[]
    for members in member_counts:
        for repeat in range(repeats):
            row=_trial(members)
            row["repeat"]=repeat
            runs.append(row)

    summary=[]
    for members in member_counts:
        group=[row for row in runs if row["members"]==members]
        summary.append({
            "members":members,
            "mirror_median_ms":statistics.median(row["mirror_ms"] for row in group),
            "mirror_median_messages_s":statistics.median(row["mirror_messages_s"] for row in group),
            "mirror_median_replica_updates_s":statistics.median(row["mirror_replica_updates_s"] for row in group),
            "peer_note_roundtrip_median_ms":statistics.median(row["peer_note_roundtrip_ms"] for row in group),
            "all_converged":all(row["converged"] for row in group),
            "station_authority_preserved":all(row["station_tasks_remained_integrated"] for row in group),
        })

    config={"member_counts":list(member_counts),"repeats":repeats}
    return {
        "schema_version":"residual.station-mesh-bridge-experiment.v1",
        "kind":"station-mesh-observability-bridge",
        "evidence_level":"development_fixture",
        "simulation":True,
        "configuration":config,
        "runs":runs,
        "summary":summary,
        "claim_boundary":(
            "The Station workload is the scripted real-Git demo, while mesh signing, "
            "history, fanout and note ingestion are real in-process protocol operations. "
            "This does not measure physical transport, model inference, or authorize "
            "mesh chat to execute Station actions."
        ),
        "benchmark_hash":digest(config),
    }
