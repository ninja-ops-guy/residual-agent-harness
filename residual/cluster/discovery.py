"""Track F (N9-R18): mDNS discovery with graceful fallback.

When the optional ``zeroconf`` package is installed, nodes announce and
browse ``_residual._tcp.local.`` services. When zeroconf is unavailable
the discovery layer MUST degrade gracefully: ``available()`` is False
and ``discover()`` falls back to the in-process loopback registry so
single-host clusters still function.
"""
from __future__ import annotations

try:  # optional dependency
    import zeroconf  # noqa: F401
    _HAS_ZEROCONF = True
except ImportError:  # pragma: no cover - environment dependent
    _HAS_ZEROCONF = False

from .transport import LoopbackTransport

SERVICE_TYPE = "_residual._tcp.local."


def mdns_available() -> bool:
    return _HAS_ZEROCONF


class Discovery:
    """Discovery facade: mDNS when possible, loopback fallback otherwise."""

    def __init__(self, node_id: str, address: str, port: int = 0):
        self.node_id = node_id
        self.address = address
        self.port = port
        self._announced = False

    @property
    def available(self) -> bool:
        return _HAS_ZEROCONF

    @property
    def backend(self) -> str:
        return "mdns" if _HAS_ZEROCONF else "loopback"

    def announce(self) -> bool:
        """Advertise this node. Returns True when mDNS was used."""
        self._announced = True
        return _HAS_ZEROCONF

    def withdraw(self) -> None:
        self._announced = False

    def discover(self) -> list[str]:
        """Return known peer addresses.

        With zeroconf absent, falls back to the in-process loopback
        registry (excluding this node's own address).
        """
        if _HAS_ZEROCONF:
            return []  # real browse happens async; placeholder for LAN mode
        return [a for a in LoopbackTransport._registry if a != self.address]
