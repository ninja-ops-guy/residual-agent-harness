"""Experimental in-process mesh session coordinator.

MeshSession is the control-plane object missing between isolated MeshNode instances
and a future real transport. It owns explicit membership, verified late-join catch-up,
fanout and convergence reporting. It deliberately does not resolve divergent histories:
a fork blocks further session broadcast until an external policy/operator handles it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from residual.core import ContractError
from .node import MeshMessage, MeshMessageKind, MeshNode


@dataclass(frozen=True)
class DeliveryReceipt:
    message_id: str
    author_id: str
    acknowledged: tuple[str, ...]
    rejected: tuple[str, ...]
    converged: bool
    head_hash: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "author_id": self.author_id,
            "acknowledged": list(self.acknowledged),
            "rejected": list(self.rejected),
            "converged": self.converged,
            "head_hash": self.head_hash,
        }


class MeshSession:
    """Explicit membership + fanout over already authenticated MeshNode objects."""

    def __init__(self, session_id: str):
        if not isinstance(session_id, str) or not session_id.strip():
            raise ContractError("mesh session id is required")
        self.session_id = session_id.strip()
        self._nodes: dict[str, MeshNode] = {}
        self._degraded = False

    @property
    def members(self) -> tuple[str, ...]:
        return tuple(sorted(self._nodes))

    def node(self, device_id: str) -> MeshNode:
        try:
            return self._nodes[device_id]
        except KeyError:
            raise ContractError(f"mesh member {device_id!r} is not joined") from None

    def heads(self) -> dict[str, str]:
        return {device_id: node.chat.head_hash for device_id, node in sorted(self._nodes.items())}

    def converged(self) -> bool:
        heads = set(self.heads().values())
        return len(heads) <= 1 and not self._degraded

    def _require_converged(self) -> str:
        if not self._nodes:
            return "GENESIS"
        heads = self.heads()
        unique = set(heads.values())
        if len(unique) != 1 or self._degraded:
            raise ContractError(f"mesh session is divergent: {heads}")
        return next(iter(unique))

    def join(self, node: MeshNode) -> dict[str, Any]:
        if not isinstance(node, MeshNode):
            raise ContractError("mesh session requires a MeshNode")
        device_id = node.identity.device_id
        if device_id in self._nodes:
            raise ContractError(f"mesh device {device_id!r} is already joined")
        if self._nodes:
            self._require_converged()
            reference = self._nodes[sorted(self._nodes)[0]]
            for peer in self._nodes.values():
                peer.connect_peer(node.identity)
                node.connect_peer(peer.identity)
            appended = node.sync_history(reference.chat.messages)
        else:
            appended = 0
        self._nodes[device_id] = node
        return {
            "session_id": self.session_id,
            "device_id": device_id,
            "members": list(self.members),
            "history_appended": appended,
            "head_hash": node.chat.head_hash,
            "converged": self.converged(),
        }

    def leave(self, device_id: str) -> dict[str, Any]:
        node = self.node(device_id)
        for peer_id, peer in list(self._nodes.items()):
            if peer_id != device_id:
                peer.disconnect_peer(device_id)
                node.disconnect_peer(peer_id)
        del self._nodes[device_id]
        if self._nodes and len(set(self.heads().values())) == 1:
            self._degraded = False
        return {
            "session_id": self.session_id,
            "device_id": device_id,
            "members": list(self.members),
            "converged": self.converged(),
        }

    def broadcast(
        self,
        author_id: str,
        kind: MeshMessageKind,
        *,
        content: str = "",
        payload: dict | None = None,
    ) -> tuple[MeshMessage, DeliveryReceipt]:
        self._require_converged()
        sender = self.node(author_id)
        message = sender.send_message(kind, content=content, payload=payload)
        acknowledged = [author_id]
        rejected = []
        for device_id, node in sorted(self._nodes.items()):
            if device_id == author_id:
                continue
            if node.receive_message(message):
                acknowledged.append(device_id)
            else:
                rejected.append(device_id)
        heads = self.heads()
        converged = not rejected and len(set(heads.values())) == 1
        if not converged:
            self._degraded = True
        receipt = DeliveryReceipt(
            message_id=message.message_id,
            author_id=author_id,
            acknowledged=tuple(sorted(acknowledged)),
            rejected=tuple(sorted(rejected)),
            converged=converged,
            head_hash=message.hash if converged else None,
        )
        return message, receipt

    def chat(self, author_id: str, text: str) -> tuple[MeshMessage, DeliveryReceipt]:
        if not isinstance(text, str) or not text:
            raise ContractError("chat text is required")
        return self.broadcast(author_id, MeshMessageKind.CHAT, content=text)

    def status(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "members": list(self.members),
            "member_count": len(self._nodes),
            "heads": self.heads(),
            "converged": self.converged(),
            "degraded": self._degraded,
            "message_count": max((len(n.chat.messages) for n in self._nodes.values()), default=0),
        }
