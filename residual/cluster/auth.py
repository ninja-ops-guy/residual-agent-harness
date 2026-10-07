"""Track F (N9-R18, N9-R19): authenticated join/leave via cluster key.

Join and leave messages MUST carry an HMAC-SHA256 over the canonical
message body keyed with the shared cluster key. Verification MUST use
constant-time comparison and reject stale nonces beyond the allowed
clock skew.
"""
from __future__ import annotations

import hashlib
import hmac
import time

from .schema import ClusterError, WireMessage

DEFAULT_SKEW_NS = 60_000_000_000  # 60 s


def _key_bytes(cluster_key: str | bytes) -> bytes:
    return cluster_key.encode() if isinstance(cluster_key, str) else cluster_key


def sign_message(cluster_key: str | bytes, msg: WireMessage) -> WireMessage:
    """Return a copy of ``msg`` with its ``auth`` HMAC field populated."""
    mac = hmac.new(_key_bytes(cluster_key), msg.canonical_body(), hashlib.sha256)
    from dataclasses import replace
    return replace(msg, auth=mac.hexdigest())


def verify_message(cluster_key: str | bytes, msg: WireMessage,
                   now_ns: int | None = None,
                   max_skew_ns: int = DEFAULT_SKEW_NS) -> None:
    """Verify HMAC and freshness; raise ClusterError on any failure."""
    if not msg.auth:
        raise ClusterError("message is not authenticated")
    expected = hmac.new(_key_bytes(cluster_key), msg.canonical_body(),
                        hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, msg.auth):
        raise ClusterError("invalid cluster key authentication")
    now = time.time_ns() if now_ns is None else now_ns
    if msg.timestamp_ns and abs(now - msg.timestamp_ns) > max_skew_ns:
        raise ClusterError("message timestamp outside allowed clock skew")
