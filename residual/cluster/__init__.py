"""residual.cluster — distributed node clustering (Tracks F + G).

Versioned JSON wire protocol, capability advertisement, mDNS discovery
with loopback fallback, WebSocket relay (optional), HMAC-authenticated
join/leave, heartbeat-based failure detection with task reassignment,
and local-first routing. Extends ``residual.mesh`` rather than replacing
it: attach a ``MeshNode`` to mirror task results into the mesh log.

Requirement IDs: N9-R18..N9-R23 (harness_specs/PATH_TO_10_SPECS.md).
"""
from .auth import sign_message, verify_message
from .capabilities import Capability, NodeRecord
from .discovery import Discovery, mdns_available
from .node import ClusterNode, ClusterTask
from .registry import NodeRegistry
from .schema import (SCHEMA_VERSION, ClusterError, MessageKind, WireMessage,
                     decode, encode, negotiate_version, supported_versions)
from .transport import LoopbackTransport, WebSocketRelayTransport, websockets_available

__all__ = [
    "Capability", "ClusterError", "ClusterNode", "ClusterTask", "Discovery",
    "LoopbackTransport", "MessageKind", "NodeRecord", "NodeRegistry",
    "SCHEMA_VERSION", "WebSocketRelayTransport", "WireMessage", "decode",
    "encode", "mdns_available", "negotiate_version", "sign_message",
    "supported_versions", "verify_message", "websockets_available",
]
