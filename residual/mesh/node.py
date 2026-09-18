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
    public_key: str            # encoded public identity material
    capabilities: tuple[str, ...]
    address: str
    joined_at_ns: int

    def __post_init__(self):
        if not isinstance(self.device_id, str) or not 0 < len(self.device_id) <= 200:
            raise ContractError("invalid mesh device identity")
        if not isinstance(self.display_name, str) or not 0 < len(self.display_name) <= 200:
            raise ContractError("invalid mesh display name")
        if not isinstance(self.public_key, str) or not 0 < len(self.public_key) <= 4096:
            raise ContractError("invalid mesh public identity")
        if not isinstance(self.address, str) or len(self.address) > 1000:
            raise ContractError("invalid mesh address")
        if type(self.joined_at_ns) is not int or self.joined_at_ns < 0:
            raise ContractError("invalid mesh join timestamp")
        if not isinstance(self.capabilities, (tuple, list)):
            raise ContractError("mesh capabilities must be a sequence")
        capabilities = tuple(self.capabilities)
        if any(not isinstance(value, str) or not 0 < len(value) <= 200 for value in capabilities):
            raise ContractError("invalid mesh capability")
        if len(set(capabilities)) != len(capabilities):
            raise ContractError("mesh capabilities must be unique")
        object.__setattr__(self, "capabilities", capabilities)


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
            if not isinstance(self.message_id, str) or not 0 < len(self.message_id) <= 200:
                raise ContractError("invalid mesh message id")
            if not isinstance(self.author_id, str) or not 0 < len(self.author_id) <= 200:
                raise ContractError("invalid mesh message author")
            if type(self.timestamp_ns) is not int or self.timestamp_ns < 0:
                raise ContractError("invalid mesh message timestamp")
            if not isinstance(self.content, str):
                raise ContractError("mesh message content must be text")
            if not isinstance(self.signature, str) or len(self.signature) > 8192:
                raise ContractError("invalid mesh message signature")
            if self.prev_hash != "GENESIS" and (
                not isinstance(self.prev_hash, str)
                or len(self.prev_hash) != 64
                or any(ch not in "0123456789abcdef" for ch in self.prev_hash)
            ):
                raise ContractError("invalid mesh previous hash")
            object.__setattr__(self, "payload", freeze(self.payload))
            if self.kind is MeshMessageKind.CHAT and self.payload:
                raise ContractError("chat messages cannot carry structured payload")
            if len(json.dumps(self.payload).encode()) > 24000 or len(self.content.encode()) > 8000:
                raise ValueError()
        except ContractError:
            raise
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
        self._ids: set[str] = set()
        self._head = "GENESIS"

    def append(self, msg: MeshMessage) -> None:
        if not isinstance(msg, MeshMessage):
            raise ContractError("chat accepts MeshMessage objects only")
        if msg.message_id in self._ids:
            raise ContractError("duplicate mesh message id")
        if msg.prev_hash != self._head:
            raise ContractError(f"chain break: expected prev_hash {self._head}, got {msg.prev_hash}")
        self._messages.append(msg)
        self._ids.add(msg.message_id)
        self._head = msg.hash

    @property
    def messages(self) -> tuple[MeshMessage, ...]:
        return tuple(self._messages)

    @property
    def head_hash(self) -> str:
        return self._head

    def verify(self) -> bool:
        prev = "GENESIS"
        seen: set[str] = set()
        for msg in self._messages:
            if msg.message_id in seen or msg.prev_hash != prev:
                return False
            seen.add(msg.message_id)
            prev = msg.hash
        return prev == self._head and seen == self._ids


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
        if peer.device_id == self.identity.device_id:
            raise ContractError("cannot admit local device identity as a peer")
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

    def sync_history(self, messages) -> int:
        """Verify then atomically append an authoritative history catch-up.

        The caller must admit identities referenced by the snapshot first.
        Existing local history must be an exact prefix. The complete new suffix
        is authenticated and chain-checked before the local head advances.
        """
        incoming = tuple(messages)
        if any(not isinstance(msg, MeshMessage) for msg in incoming):
            raise ContractError("history contains an invalid mesh message")
        local = self.chat.messages
        if len(incoming) < len(local):
            raise ContractError("history prefix is shorter than local history")
        for index, existing in enumerate(local):
            candidate = incoming[index]
            if candidate.hash != existing.hash or candidate.signature != existing.signature:
                raise ContractError("history prefix conflicts with local history")

        pending = []
        seen_ids = {msg.message_id for msg in local}
        expected_head = self.chat.head_hash
        for msg in incoming[len(local):]:
            if msg.message_id in seen_ids:
                raise ContractError("duplicate mesh message id in history")
            seen_ids.add(msg.message_id)
            if msg.author_id in self._revoked:
                raise ContractError("history author is revoked")
            author = self.identity if msg.author_id == self.identity.device_id else self.peers.get(msg.author_id)
            if author is None:
                raise ContractError("unknown history author")
            if msg.prev_hash != expected_head:
                raise ContractError(f"history chain break: expected prev_hash {expected_head}, got {msg.prev_hash}")
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
                valid = self._verify(author.public_key, data, msg.signature) is True
            except Exception:
                valid = False
            if not valid:
                raise ContractError("history message signature verification failed")
            pending.append(msg)
            expected_head = msg.hash

        for msg in pending:
            self.chat.append(msg)
        return len(pending)

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
