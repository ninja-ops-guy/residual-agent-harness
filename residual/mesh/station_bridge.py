"""Safe Station <-> MeshSession observability bridge.

The bridge does not dispatch work from chat. Station workflow events are mirrored as
human-readable, inert CHAT messages. Verified peer CHAT can enter Station only as a
project.note. Worker claims, task transitions, review and integration remain owned by
their existing Station APIs.
"""
from __future__ import annotations

from typing import Any

from residual.core import ContractError
from residual.station.service import Station
from .node import MeshMessageKind
from .session import MeshSession


def _short(value: Any, limit: int = 160) -> str:
    text = str(value or "").replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def summarize_station_event(event: dict) -> str:
    event_type = event.get("event_type", "event")
    task = event.get("task_id")
    data = event.get("data") or {}
    prefix = f"[{event_type}]"
    if task:
        prefix += f" {task}"

    if event_type == "project.created":
        detail = f"{data.get('name','project')} · {data.get('tasks','?')} tasks"
    elif event_type == "task.transition":
        detail = f"{data.get('from','?')} -> {data.get('to','?')}"
    elif event_type == "task.claimed":
        detail = f"claimed by {event.get('actor','worker')} · route {data.get('route','?')}"
    elif event_type == "checks.completed":
        detail = f"checks {data.get('passed','?')}/{data.get('total','?')} passed"
    elif event_type == "review.completed":
        detail = f"review {'approved' if data.get('approved') else 'changes requested'}"
    elif event_type == "integration.completed":
        detail = f"integrated {str(data.get('head_commit',''))[:12]}"
    elif event_type == "task.finding":
        detail = _short(data.get("message", "finding recorded"), 400)
    elif event_type == "project.note":
        detail = _short(data.get("message", "operator note"), 1000)
    elif event_type == "worker.expired":
        detail = f"worker expired from {data.get('from','unknown')}"
    else:
        detail = "recorded"

    event_hash = str(event.get("hash", ""))
    suffix = f" · event {event.get('seq','?')}"
    if event_hash:
        suffix += f" · {event_hash[:12]}"
    return _short(f"{prefix} {detail}{suffix}", 1800)


class StationMeshBridge:
    """Project-scoped inert-chat bridge between Station and MeshSession."""

    def __init__(
        self,
        station: Station,
        project_id: str,
        session: MeshSession,
        coordinator_device_id: str,
    ):
        if not isinstance(station, Station):
            raise ContractError("StationMeshBridge requires a Station")
        station.store.project(project_id)
        session.node(coordinator_device_id)
        self.station = station
        self.project_id = project_id
        self.session = session
        self.coordinator_device_id = coordinator_device_id

    def status(self) -> dict[str, Any]:
        mesh = self.session.status()
        project = self.station.store.project(self.project_id)
        return {
            "project_id": self.project_id,
            "project_name": project["name"],
            "mesh": mesh,
            "authority": {
                "chat_executes_actions": False,
                "peer_chat_station_effect": "project.note only",
                "workflow_owner": "station",
                "worker_transport": "station-worker-api",
            },
        }

    def mirror_station_events(self, *, after_seq: int = 0, limit: int = 500) -> dict[str, Any]:
        if type(after_seq) is not int or after_seq < 0:
            raise ContractError("after_seq must be a nonnegative integer")
        events = self.station.store.events(self.project_id, after_seq, limit)
        mirrored = []
        through = after_seq
        for event in events:
            through = max(through, event["seq"])
            # A peer chat ingested into Station must not echo back into the room.
            if event["event_type"] == "project.note" and str(event.get("actor", "")).startswith("mesh:"):
                continue
            message, receipt = self.session.chat(
                self.coordinator_device_id,
                summarize_station_event(event),
            )
            mirrored.append({
                "event_seq": event["seq"],
                "event_hash": event["hash"],
                "message_id": message.message_id,
                "message_hash": message.hash,
                "delivery": receipt.to_dict(),
            })
        return {
            "mirrored": mirrored,
            "through_seq": through,
            "converged": self.session.converged(),
        }

    def ingest_peer_chat(self, message_id: str) -> dict[str, Any]:
        message = self.session.message(message_id)
        if message.kind is not MeshMessageKind.CHAT:
            raise ContractError("only inert CHAT messages may enter Station notes")
        if message.author_id == self.coordinator_device_id:
            raise ContractError("coordinator chat is already represented by Station events")
        if len(message.content) > 2000:
            raise ContractError("peer chat exceeds Station note limit")

        for event in self.station.store.events(self.project_id, 0, 100000):
            if event["event_type"] == "project.note" and event["data"].get("mesh_message_id") == message.message_id:
                return {
                    "ingested": False,
                    "duplicate": True,
                    "event_seq": event["seq"],
                    "message_id": message.message_id,
                }

        event = self.station.store.event(
            self.project_id,
            "project.note",
            {
                "message": message.content,
                "mesh_message_id": message.message_id,
                "mesh_message_hash": message.hash,
            },
            actor=f"mesh:{message.author_id}",
        )
        return {
            "ingested": True,
            "duplicate": False,
            "event_seq": event["seq"],
            "event_hash": event["hash"],
            "message_id": message.message_id,
        }
