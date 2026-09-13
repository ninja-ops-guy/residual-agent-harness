"""Track 6: Federated Mesh — multi-device group chat with local model sharing.

Devices discover each other, exchange signed messages, propose tasks,
offer models, execute locally, and broadcast verified results.
Trustless: all results locally verifiable.
"""
from __future__ import annotations

from observation_layer.core import freeze

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from ..core import ContractError


class MeshMessageKind(str, Enum):
    CHAT = "chat"
    TASK_PROPOSAL = "task_proposal"
    TASK_RESULT = "task_result"
    TASK_RESULT_DISPUTE = "task_result_dispute"
    MODEL_OFFER = "model_offer"
    DEVICE_JOINED = "device_joined"
    DEVICE_LEFT = "device_left"
    REVOKE_DEVICE = "revoke_device"


@dataclass(frozen=True)
class MeshIdentity:
    device_id: str
    display_name: str
    public_key: str            # hex-encoded public key
    capabilities: tuple[str, ...]
    address: str
    joined_at_ns: int


@dataclass(frozen=True)
class MeshMessage:
    message_id: str
    author_id: str
    timestamp_ns: int
    kind: MeshMessageKind
    content: str = ""
    payload: dict = field(default_factory=dict)
    signature: str = ""
    prev_hash: str = "GENESIS"

    def __post_init__(self):
        try:
            object.__setattr__(self, "kind", MeshMessageKind(self.kind))
            object.__setattr__(self, "payload", freeze(self.payload))
            if len(json.dumps(self.payload).encode()) > 24000 or len(self.content.encode()) > 8000:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise ContractError("invalid or oversized mesh message") from None

    @property
    def hash(self) -> str:
        data = {
            "message_id": self.message_id,
            "author_id": self.author_id,
            "timestamp_ns": self.timestamp_ns,
            "kind": self.kind.value,
            "content": self.content,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


class MeshChat:
    """Shared append-only hash-chained message log."""

    def __init__(self):
        self._messages: list[MeshMessage] = []
        self._head = "GENESIS"

    def append(self, msg: MeshMessage) -> None:
        if msg.prev_hash != self._head:
            raise ContractError(f"chain break: expected prev_hash {self._head}, got {msg.prev_hash}")
        self._messages.append(msg)
        self._head = msg.hash

    @property
    def messages(self) -> tuple[MeshMessage, ...]:
        return tuple(self._messages)

    @property
    def head_hash(self) -> str:
        return self._head

    def verify(self) -> bool:
        prev = "GENESIS"
        for msg in self._messages:
            if msg.prev_hash != prev:
                return False
            prev = msg.hash
        return prev == self._head


class MeshNode:
    """One device in the mesh.

    Parameters
    -----------
    identity: MeshIdentity — this device's identity
    sign_fn: callable(bytes) -> str — signs data with device private key
    verify_fn: callable(str, str, str) -> bool — verifies (public_key, data, signature)
    """

    def __init__(self, identity: MeshIdentity,
                 sign_fn: Callable[[bytes], str],
                 verify_fn: Callable[[str, bytes, str], bool]):
        self.identity = identity
        self._sign = sign_fn
        self._verify = verify_fn
        self.chat = MeshChat()
        self.peers: dict[str, MeshIdentity] = {}
        self._revoked: set[str] = set()

    def connect_peer(self, peer: MeshIdentity) -> None:
        if peer.device_id in self._revoked:
            raise ContractError(f"device {peer.device_id} is revoked")
        old = self.peers.get(peer.device_id)
        if old is not None and old.public_key != peer.public_key:
            raise ContractError("peer key changes require explicit host re-admission")
        self.peers[peer.device_id] = peer

    def disconnect_peer(self, device_id: str) -> None:
        self.peers.pop(device_id, None)

    def revoke_device(self, device_id: str, revoker_signature: str) -> None:
        """Host-local revocation only. This prototype has no quorum protocol.

        revoker_signature is a legacy argument and is not an authorization proof.
        Only a trusted host should call this method; never expose it as an RPC.
        """
        self._revoked.add(device_id)
        self.disconnect_peer(device_id)

    def is_revoked(self, device_id: str) -> bool:
        return device_id in self._revoked

    def send_message(self, kind: MeshMessageKind, content: str = "",
                     payload: dict | None = None) -> MeshMessage:
        """Create, sign, and append a message to the shared chat."""
        msg = MeshMessage(
            message_id=str(uuid.uuid4()),
            author_id=self.identity.device_id,
            timestamp_ns=time.time_ns(),
            kind=kind,
            content=content,
            payload=payload or {},
            prev_hash=self.chat.head_hash,
        )
        # Sign
        data = json.dumps({
            "message_id": msg.message_id,
            "author_id": msg.author_id,
            "timestamp_ns": msg.timestamp_ns,
            "kind": msg.kind.value,
            "content": msg.content,
            "payload": msg.payload,
            "prev_hash": msg.prev_hash,
        }, sort_keys=True).encode()
        signature = self._sign(data)
        # Rebuild with signature (frozen dataclass)
        signed_msg = MeshMessage(
            message_id=msg.message_id,
            author_id=msg.author_id,
            timestamp_ns=msg.timestamp_ns,
            kind=msg.kind,
            content=msg.content,
            payload=msg.payload,
            signature=signature,
            prev_hash=msg.prev_hash,
        )
        self.chat.append(signed_msg)
        return signed_msg

    def receive_message(self, msg: MeshMessage) -> bool:
        """Verify and append a message from a peer."""
        if msg.author_id in self._revoked:
            return False
        peer = self.peers.get(msg.author_id)
        if peer is None:
            return False
        # Verify signature
        data = json.dumps({
            "message_id": msg.message_id,
            "author_id": msg.author_id,
            "timestamp_ns": msg.timestamp_ns,
            "kind": msg.kind.value,
            "content": msg.content,
            "payload": msg.payload,
            "prev_hash": msg.prev_hash,
        }, sort_keys=True).encode()
        try:
            valid = self._verify(peer.public_key, data, msg.signature) is True
        except Exception:
            valid = False
        if not valid:
            return False
        try:
            self.chat.append(msg)
            return True
        except ContractError:
            return False

    def propose_task(self, goal_spec: dict) -> MeshMessage:
        """Broadcast a task proposal with a frozen GoalSpec."""
        return self.send_message(
            MeshMessageKind.TASK_PROPOSAL,
            payload={"goal_spec": goal_spec, "goal_spec_hash": _hash(goal_spec)},
        )

    def offer_model(self, task_id: str, model_name: str,
                    capability_score: float, load_time_s: float = 0.0) -> MeshMessage:
        """Offer a local model for a proposed task."""
        return self.send_message(
            MeshMessageKind.MODEL_OFFER,
            payload={
                "task_id": task_id,
                "model_name": model_name,
                "capability_score": capability_score,
                "load_time_s": load_time_s,
                "device_id": self.identity.device_id,
            },
        )

    def broadcast_result(self, task_id: str, result: str,
                         receipt_hash: str, verifier_revision: str,
                         outcome: str) -> MeshMessage:
        """Broadcast a verified task result."""
        return self.send_message(
            MeshMessageKind.TASK_RESULT,
            payload={
                "task_id": task_id,
                "result": result,
                "receipt_hash": receipt_hash,
                "verifier_revision": verifier_revision,
                "outcome": outcome,
            },
        )

    def dispute_result(self, task_id: str, reason: str,
                       expected_hash: str) -> MeshMessage:
        """Dispute a result that fails local verification."""
        return self.send_message(
            MeshMessageKind.TASK_RESULT_DISPUTE,
            payload={
                "task_id": task_id,
                "reason": reason,
                "expected_hash": expected_hash,
            },
        )


def _hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()
