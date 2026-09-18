"""Track F (N9-R18..R23): cluster node — join/leave, heartbeat, failure
detection with task reassignment, and local-first routing.

Extends (does not replace) ``residual.mesh``: when a ``MeshNode`` is
attached, verified task results are also broadcast into the mesh chat so
the existing hash-chained log remains the record of completed work.

Requirements
------------
- N9-R18: versioned wire protocol with discovery, capability
  announcement, task assignment/result return, receipt exchange, and
  device join/leave (see schema.py / discovery.py / transport.py).
- N9-R21: unresponsive nodes MUST be detected via heartbeat timeout;
  their in-flight tasks MUST be reassigned to other capable nodes and
  their receipts MUST be marked ``node_failed``.
- N9-R23: routing MUST prefer local nodes on equal capability.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from .auth import sign_message, verify_message
from .capabilities import Capability, NodeRecord
from .discovery import Discovery
from .registry import NodeRegistry
from .schema import (ClusterError, MessageKind, WireMessage, decode, encode,
                     negotiate_version, supported_versions)
from .transport import LoopbackTransport

HEARTBEAT_INTERVAL_NS = 1_000_000_000
FAILURE_TIMEOUT_NS = 5_000_000_000


@dataclass
class ClusterTask:
    task_id: str
    goal_spec: dict
    required_model: str | None = None
    min_context_window: int = 0
    assigned_node: str | None = None
    state: str = "pending"  # pending | assigned | completed | failed | node_failed
    receipt: dict = field(default_factory=dict)


class ClusterNode:
    """One node in a residual cluster."""

    def __init__(self, node_id: str | None, capability: Capability,
                 cluster_key: str, address: str | None = None,
                 mesh_node=None,
                 heartbeat_interval_ns: int = HEARTBEAT_INTERVAL_NS,
                 failure_timeout_ns: int = FAILURE_TIMEOUT_NS):
        self.node_id = node_id or f"node-{uuid.uuid4().hex[:12]}"
        self.capability = capability
        self.cluster_key = cluster_key
        self.address = address or f"loopback://{self.node_id}"
        self.registry = NodeRegistry()
        self.tasks: dict[str, ClusterTask] = {}
        self.receipts: list[dict] = []
        self.mesh_node = mesh_node  # optional residual.mesh.node.MeshNode
        self.discovery = Discovery(self.node_id, self.address)
        self.transport = LoopbackTransport(self.address, self._on_wire)
        self.heartbeat_interval_ns = heartbeat_interval_ns
        self.failure_timeout_ns = failure_timeout_ns
        self._last_heartbeat_sent = 0
        self.negotiated_version: int | None = None
        self.joined = False

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------
    def open(self) -> None:
        self.transport.open()
        self.discovery.announce()
        self.registry.upsert(NodeRecord(
            node_id=self.node_id, address=self.address,
            capability=self.capability, is_local=True,
            schema_versions=tuple(supported_versions()),
        ))

    def close(self) -> None:
        self.discovery.withdraw()
        self.transport.close()

    def join(self, bootstrap_address: str | None = None) -> dict:
        """N9-R19: discover, authenticate, negotiate, then report joined.

        A first node with no discovered peers may form a standalone cluster.
        When peers are present (or an explicit bootstrap was supplied), a
        transport send alone is not admission: JOIN_ACK/version negotiation is
        required before joined becomes true.
        """
        peers = ([bootstrap_address] if bootstrap_address
                 else self.discovery.discover())
        self.registry.upsert(NodeRecord(
            node_id=self.node_id, address=self.address,
            capability=self.capability, is_local=True,
            schema_versions=tuple(supported_versions()),
        ))
        self.negotiated_version = None
        joined_to = None
        if not peers and bootstrap_address is None:
            self.joined = True
        else:
            self.joined = False
            for addr in peers:
                hello = sign_message(self.cluster_key, WireMessage(
                    kind=MessageKind.JOIN, sender_id=self.node_id,
                    payload={
                        "address": self.address,
                        "capability": self.capability.to_dict(),
                        "schema_versions": supported_versions(),
                    },
                ))
                if not self.transport.send(addr, encode(hello)):
                    continue
                # Loopback transport delivers synchronously; admission is
                # established only if JOIN_ACK negotiated a common version.
                if self.negotiated_version is not None:
                    joined_to = addr
                    self.joined = True
                    break
        return {
            "node_id": self.node_id,
            "address": self.address,
            "joined": self.joined,
            "bootstrap": joined_to,
            "discovery_backend": self.discovery.backend,
            "schema_versions": supported_versions(),
            "capability": self.capability.to_dict(),
        }

    def leave(self) -> dict:
        """N9-R20: announce departure and remove self from routing.

        In-flight tasks are reassigned before departure.
        """
        self.registry.mark_state(self.node_id, "leaving")
        self._reassign_tasks_of(self.node_id, reason="node_left")
        notice = sign_message(self.cluster_key, WireMessage(
            kind=MessageKind.LEAVE, sender_id=self.node_id,
            payload={"address": self.address},
        ))
        data = encode(notice)
        for peer in self.registry.nodes():
            if peer.node_id != self.node_id:
                self.transport.send(peer.address, data)
        self.registry.remove(self.node_id)
        self.joined = False
        return {"node_id": self.node_id, "left": True,
                "inflight_reassigned": True}

    # ------------------------------------------------------------------
    # wire handling
    # ------------------------------------------------------------------
    def _on_wire(self, from_address: str, data: bytes) -> None:
        msg = decode(data)
        try:
            verify_message(self.cluster_key, msg)
        except ClusterError:
            return  # unauthenticated traffic is dropped
        handler = getattr(self, f"_handle_{msg.kind.value}", None)
        if handler:
            handler(msg, from_address)

    def _handle_join(self, msg: WireMessage, from_address: str) -> None:
        offered = msg.payload.get("schema_versions", [])
        requested_address = msg.payload.get("address", from_address)
        existing = self.registry.get(msg.sender_id)
        if msg.sender_id == self.node_id or (existing is not None and existing.address != requested_address):
            self._send(from_address, MessageKind.ERROR, {"reason": "duplicate_node_id"})
            return
        version = negotiate_version(offered)
        if version is None:
            self._send(from_address, MessageKind.ERROR,
                       {"reason": "no_common_schema_version",
                        "schema_versions": supported_versions()})
            return
        cap = Capability.from_dict(msg.payload["capability"])
        self.registry.upsert(NodeRecord(
            node_id=msg.sender_id,
            address=requested_address,
            capability=cap, schema_versions=tuple(offered),
        ))
        # JOIN_ACK carries our versions + full roster so the joiner can
        # populate its registry (version negotiation happens here).
        self._send(from_address, MessageKind.JOIN_ACK, {
            "schema_versions": supported_versions(),
            "negotiated_version": version,
            "capability": self.capability.to_dict(),
            "address": self.address,
            "roster": [n.to_dict() for n in self.registry.nodes()],
        })

    def _handle_join_ack(self, msg: WireMessage, from_address: str) -> None:
        version = negotiate_version(msg.payload.get("schema_versions", []))
        if version is None:
            raise ClusterError("cluster rejected join: no common schema_version")
        negotiated = msg.payload.get("negotiated_version", version)
        if negotiated != version or negotiated not in supported_versions():
            raise ClusterError("cluster join ack contains an invalid negotiated_version")
        self.negotiated_version = negotiated
        for rec in msg.payload.get("roster", []):
            record = NodeRecord.from_dict(rec)
            if record.node_id != self.node_id:
                record.is_local = False
                self.registry.upsert(record)
        record = NodeRecord(
            node_id=msg.sender_id,
            address=msg.payload.get("address", from_address),
            capability=Capability.from_dict(msg.payload["capability"]),
            schema_versions=tuple(msg.payload.get("schema_versions", [])),
        )
        self.registry.upsert(record)

    def _handle_leave(self, msg: WireMessage, from_address: str) -> None:
        self.registry.remove(msg.sender_id)
        self._reassign_tasks_of(msg.sender_id, reason="node_left")

    def _handle_heartbeat(self, msg: WireMessage, from_address: str) -> None:
        self.registry.heartbeat(msg.sender_id, msg.timestamp_ns)
        # Heartbeats piggyback capability refreshes (N9-R18 announcement).
        if "capability" in msg.payload:
            rec = self.registry.get(msg.sender_id)
            if rec is not None:
                rec.capability = Capability.from_dict(msg.payload["capability"])

    def _handle_task_assign(self, msg: WireMessage, from_address: str) -> None:
        spec = msg.payload["goal_spec"]
        task = ClusterTask(
            task_id=msg.payload["task_id"], goal_spec=spec,
            required_model=msg.payload.get("required_model"),
            assigned_node=self.node_id, state="assigned",
        )
        self.tasks[task.task_id] = task
        # In-process execution hook: subclasses/tests may override run_task.
        result = self.run_task(task)
        self._send(from_address, MessageKind.TASK_RESULT, {
            "task_id": task.task_id, "result": result,
            "receipt": {"task_id": task.task_id, "node_id": self.node_id,
                        "outcome": "completed"},
        })

    def _handle_task_result(self, msg: WireMessage, from_address: str) -> None:
        task = self.tasks.get(msg.payload["task_id"])
        receipt = msg.payload.get("receipt", {})
        if task is not None:
            task.state = "completed"
            task.receipt = receipt
        receipt.setdefault("outcome", "completed")
        self.receipts.append(receipt)
        if self.mesh_node is not None:  # integrate with residual.mesh log
            self.mesh_node.broadcast_result(
                task_id=msg.payload["task_id"],
                result=str(msg.payload.get("result", "")),
                receipt_hash=receipt.get("task_id", ""),
                verifier_revision="cluster",
                outcome=receipt["outcome"],
            )

    def _handle_task_reassign(self, msg: WireMessage, from_address: str) -> None:
        self._handle_task_assign(msg, from_address)

    def _send(self, address: str, kind: MessageKind, payload: dict) -> bool:
        msg = sign_message(self.cluster_key, WireMessage(
            kind=kind, sender_id=self.node_id, payload=payload))
        return self.transport.send(address, encode(msg))

    # ------------------------------------------------------------------
    # heartbeat + failure detection (N9-R21)
    # ------------------------------------------------------------------
    def tick(self, now_ns: int | None = None) -> None:
        """Send heartbeats when due and detect failed peers."""
        now = time.time_ns() if now_ns is None else now_ns
        if now - self._last_heartbeat_sent >= self.heartbeat_interval_ns:
            self._last_heartbeat_sent = now
            for peer in self.registry.nodes():
                if peer.node_id != self.node_id:
                    self._send(peer.address, MessageKind.HEARTBEAT,
                               {"capability": self.capability.to_dict()})
        self.detect_failures(now)

    def detect_failures(self, now_ns: int | None = None) -> list[str]:
        """Mark unresponsive peers failed and reassign their tasks."""
        now = time.time_ns() if now_ns is None else now_ns
        failed = []
        for peer in self.registry.nodes():
            if peer.node_id == self.node_id:
                continue
            if now - peer.last_heartbeat_ns > self.failure_timeout_ns:
                self.registry.mark_state(peer.node_id, "failed")
                failed.append(peer.node_id)
                self._reassign_tasks_of(peer.node_id, reason="node_failed")
        return failed

    def _reassign_tasks_of(self, node_id: str, reason: str) -> None:
        for task in self.tasks.values():
            if task.assigned_node == node_id and task.state in ("pending", "assigned"):
                receipt = {"task_id": task.task_id, "node_id": node_id,
                           "outcome": reason}
                self.receipts.append(receipt)
                task.receipt = receipt
                task.state = "node_failed" if reason == "node_failed" else "pending"
                target = self.registry.route(task.required_model,
                                             task.min_context_window)
                if target is not None and target.node_id != node_id:
                    self.assign_task(task, target)

    # ------------------------------------------------------------------
    # task routing (N9-R23)
    # ------------------------------------------------------------------
    def submit_task(self, goal_spec: dict, required_model: str | None = None,
                    min_context_window: int = 0) -> ClusterTask:
        task = ClusterTask(task_id=str(uuid.uuid4()), goal_spec=goal_spec,
                           required_model=required_model,
                           min_context_window=min_context_window)
        self.tasks[task.task_id] = task
        target = self.registry.route(required_model, min_context_window)
        if target is None:
            task.state = "failed"
            task.receipt = {"task_id": task.task_id, "outcome": "no_capable_node"}
            self.receipts.append(task.receipt)
            return task
        self.assign_task(task, target)
        return task

    def assign_task(self, task: ClusterTask, target: NodeRecord) -> None:
        task.assigned_node = target.node_id
        if target.node_id == self.node_id or target.is_local:
            task.state = "assigned"
            result = self.run_task(task)
            task.state = "completed"
            task.receipt = {"task_id": task.task_id, "node_id": self.node_id,
                            "outcome": "completed"}
            self.receipts.append(task.receipt)
            if self.mesh_node is not None:
                self.mesh_node.broadcast_result(
                    task_id=task.task_id, result=str(result),
                    receipt_hash=task.task_id,
                    verifier_revision="cluster", outcome="completed")
            return
        task.state = "assigned"
        self._send(target.address, MessageKind.TASK_ASSIGN, {
            "task_id": task.task_id, "goal_spec": task.goal_spec,
            "required_model": task.required_model,
            "min_context_window": task.min_context_window,
        })

    def run_task(self, task: ClusterTask) -> str:
        """Default in-process executor; real deployments override this."""
        return f"executed:{task.task_id}"

    # ------------------------------------------------------------------
    # status (N9-R22)
    # ------------------------------------------------------------------
    def status(self) -> dict:
        return {
            "node_id": self.node_id,
            "address": self.address,
            "joined": self.joined,
            "negotiated_version": self.negotiated_version,
            "discovery_backend": self.discovery.backend,
            "nodes": [n.to_dict() for n in self.registry.nodes(
                states=("active", "leaving", "failed"))],
            "capacity": self.registry.aggregate_capacity(),
            "tasks": {
                "total": len(self.tasks),
                "inflight": sum(1 for t in self.tasks.values()
                                if t.state in ("pending", "assigned")),
                "completed": sum(1 for t in self.tasks.values()
                                 if t.state == "completed"),
                "node_failed": sum(1 for t in self.tasks.values()
                                   if t.state == "node_failed"),
            },
        }
