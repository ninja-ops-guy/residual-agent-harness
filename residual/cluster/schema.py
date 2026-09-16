"""Track F (N9-R18): versioned JSON wire schema for cluster communication.

Every wire message MUST carry a ``schema_version`` field. Decoders MUST
reject messages whose major version is unsupported, and peers MUST
negotiate a mutually supported version during join (``JOIN`` /
``JOIN_ACK`` exchange).
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

SCHEMA_VERSION = 1
MIN_SUPPORTED_VERSION = 1
MAX_SUPPORTED_VERSION = 1
MAX_WIRE_BYTES = 256 * 1024


class ClusterError(Exception):
    """Raised on any cluster protocol violation."""


class MessageKind(str, Enum):
    HELLO = "hello"
    JOIN = "join"
    JOIN_ACK = "join_ack"
    LEAVE = "leave"
    HEARTBEAT = "heartbeat"
    CAPABILITIES = "capabilities"
    TASK_ASSIGN = "task_assign"
    TASK_RESULT = "task_result"
    TASK_REASSIGN = "task_reassign"
    RECEIPT = "receipt"
    ERROR = "error"


@dataclass(frozen=True)
class WireMessage:
    kind: MessageKind
    sender_id: str
    payload: dict = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION
    timestamp_ns: int = field(default_factory=time.time_ns)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    auth: str = ""  # HMAC hex over canonical body, when cluster key is in use

    def __post_init__(self):
        try:
            object.__setattr__(self, "kind", MessageKind(self.kind))
        except (ValueError, TypeError):
            raise ClusterError(f"unknown message kind {self.kind!r}") from None
        if not isinstance(self.schema_version, int) or self.schema_version < 1:
            raise ClusterError("invalid schema_version")

    def canonical_body(self) -> bytes:
        return json.dumps(
            {
                "kind": self.kind.value,
                "sender_id": self.sender_id,
                "payload": self.payload,
                "schema_version": self.schema_version,
                "timestamp_ns": self.timestamp_ns,
                "message_id": self.message_id,
            },
            sort_keys=True,
        ).encode()


def encode(msg: WireMessage) -> bytes:
    """Serialize a WireMessage to JSON bytes (always includes schema_version)."""
    body = json.loads(msg.canonical_body())
    body["auth"] = msg.auth
    data = json.dumps(body, sort_keys=True).encode()
    if len(data) > MAX_WIRE_BYTES:
        raise ClusterError("wire message exceeds size limit")
    return data


def decode(data: bytes | str,
           min_version: int = MIN_SUPPORTED_VERSION,
           max_version: int = MAX_SUPPORTED_VERSION) -> WireMessage:
    """Parse JSON bytes into a WireMessage, enforcing version bounds."""
    if isinstance(data, str):
        data = data.encode()
    if len(data) > MAX_WIRE_BYTES:
        raise ClusterError("wire message exceeds size limit")
    try:
        obj = json.loads(data)
        if not isinstance(obj, dict):
            raise ValueError
        version = obj["schema_version"]
    except (ValueError, KeyError, TypeError):
        raise ClusterError("malformed wire message: missing schema_version") from None
    if not isinstance(version, int) or version < min_version or version > max_version:
        raise ClusterError(
            f"unsupported schema_version {version!r} "
            f"(supported {min_version}..{max_version})"
        )
    try:
        return WireMessage(
            kind=obj["kind"],
            sender_id=obj["sender_id"],
            payload=obj.get("payload") or {},
            schema_version=version,
            timestamp_ns=obj.get("timestamp_ns", 0),
            message_id=obj.get("message_id", ""),
            auth=obj.get("auth", ""),
        )
    except (KeyError, TypeError) as exc:
        raise ClusterError(f"malformed wire message: {exc}") from None


def negotiate_version(peer_versions: list[int] | tuple[int, ...],
                      local_min: int = MIN_SUPPORTED_VERSION,
                      local_max: int = MAX_SUPPORTED_VERSION) -> int | None:
    """Return the highest mutually supported schema version, or None."""
    candidates = [v for v in peer_versions
                  if isinstance(v, int) and local_min <= v <= local_max]
    return max(candidates) if candidates else None


def supported_versions() -> list[int]:
    """Versions this node offers during version negotiation."""
    return list(range(MIN_SUPPORTED_VERSION, MAX_SUPPORTED_VERSION + 1))
