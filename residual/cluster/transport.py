"""Track F (N9-R18): transports.

- ``LoopbackTransport``: in-process message passing, built on the same
  address registry style as ``residual.mesh``; always available and used
  for tests and single-process clusters.
- ``WebSocketRelayTransport``: WAN relay over WebSockets. Uses the
  optional ``websockets`` package; when it is unavailable the transport
  degrades gracefully (``available()`` is False and construction of a
  live connection raises ClusterError with a clear message).
"""
from __future__ import annotations

from typing import Callable

from .schema import ClusterError

try:  # optional dependency
    import websockets  # noqa: F401
    _HAS_WEBSOCKETS = True
except ImportError:  # pragma: no cover - environment dependent
    _HAS_WEBSOCKETS = False


def websockets_available() -> bool:
    return _HAS_WEBSOCKETS


MessageHandler = Callable[[str, bytes], None]


class LoopbackTransport:
    """In-process transport. Nodes register under an address; sending
    delivers synchronously to the registered handler, mirroring the
    in-memory semantics of ``residual.mesh``."""

    _registry: dict[str, MessageHandler] = {}

    def __init__(self, address: str, handler: MessageHandler):
        self.address = address
        self._handler = handler
        self._open = False

    def open(self) -> None:
        LoopbackTransport._registry[self.address] = self._handler
        self._open = True

    def close(self) -> None:
        LoopbackTransport._registry.pop(self.address, None)
        self._open = False

    def send(self, peer_address: str, data: bytes) -> bool:
        handler = LoopbackTransport._registry.get(peer_address)
        if handler is None:
            return False
        handler(self.address, data)
        return True

    @classmethod
    def reset_registry(cls) -> None:
        cls._registry.clear()


class WebSocketRelayTransport:
    """WebSocket relay transport for WAN clusters.

    Requires the optional ``websockets`` package. When unavailable,
    ``available()`` returns False so callers can fall back to loopback
    or report that WAN clustering is disabled.
    """

    def __init__(self, relay_url: str):
        self.relay_url = relay_url
        if not _HAS_WEBSOCKETS:
            raise ClusterError(
                "websockets package unavailable; WAN relay disabled "
                "(install 'websockets' or use the in-process transport)"
            )

    @staticmethod
    def available() -> bool:
        return _HAS_WEBSOCKETS
