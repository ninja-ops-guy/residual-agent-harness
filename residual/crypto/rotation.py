"""Key rotation with a bounded old-key verification window (Track L, L-R4).

A ``KeyRing`` holds one active key and zero or more retired keys. Signing
always uses the active key; verification accepts the active key and any
retired key still inside its verification window, and MUST reject retired
keys once the window has closed.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from typing import Callable

from ..core import ContractError, identifier


@dataclass
class KeyRecord:
    """One signing key and its lifecycle timestamps."""

    key_id: str
    key: bytes
    created_at: float
    retired_at: float | None = None
    verify_until: float | None = None

    def __post_init__(self):
        identifier(self.key_id)
        if len(self.key) < 16:
            raise ContractError("key material must be at least 16 bytes")

    @property
    def active(self) -> bool:
        return self.retired_at is None


class KeyRing:
    """Rotating key store. Implements L-R4.

    - ``rotate`` installs a new active key and retires the previous one with
      a verification window of ``verify_window_seconds``.
    - ``verify`` accepts signatures made by the active key or by a retired
      key whose ``verify_until`` has not passed; otherwise it returns False.
    - ``verify_strict`` raises ContractError instead of returning False.
    """

    def __init__(self, verify_window_seconds: float = 86400.0,
                 clock: Callable[[], float] = time.time):
        if verify_window_seconds <= 0:
            raise ContractError("verify window must be positive")
        self.verify_window_seconds = float(verify_window_seconds)
        self.clock = clock
        self._keys: dict[str, KeyRecord] = {}
        self._active_id: str | None = None

    # -- lifecycle --------------------------------------------------------

    def add_key(self, key_id: str, key: bytes | None = None) -> KeyRecord:
        if key_id in self._keys:
            raise ContractError(f"duplicate key_id {key_id!r}")
        record = KeyRecord(key_id=key_id, key=key or os.urandom(32),
                           created_at=self.clock())
        self._keys[key_id] = record
        if self._active_id is None:
            self._active_id = key_id
        return record

    def rotate(self, new_key_id: str, key: bytes | None = None) -> KeyRecord:
        """Install a new active key; retire the old one with a verify window."""
        if new_key_id in self._keys:
            raise ContractError(f"duplicate key_id {new_key_id!r}")
        now = self.clock()
        old = self.active_record
        if old is not None:
            old.retired_at = now
            old.verify_until = now + self.verify_window_seconds
        record = KeyRecord(key_id=new_key_id, key=key or os.urandom(32),
                           created_at=now)
        self._keys[new_key_id] = record
        self._active_id = new_key_id
        return record

    @property
    def active_record(self) -> KeyRecord | None:
        return self._keys.get(self._active_id) if self._active_id else None

    def get(self, key_id: str) -> KeyRecord:
        try:
            return self._keys[key_id]
        except KeyError:
            raise ContractError(f"unknown key_id {key_id!r}") from None

    def status(self) -> dict:
        now = self.clock()
        return {
            "active_key_id": self._active_id,
            "keys": {
                kid: {
                    "active": rec.active,
                    "retired_at": rec.retired_at,
                    "verify_until": rec.verify_until,
                    "verifiable": rec.active or (rec.verify_until is not None and now <= rec.verify_until),
                }
                for kid, rec in sorted(self._keys.items())
            },
        }

    # -- sign / verify ----------------------------------------------------

    @staticmethod
    def _mac(key: bytes, data: bytes) -> bytes:
        if not isinstance(data, bytes):
            raise ContractError("data must be bytes")
        return hmac.new(key, data, hashlib.sha256).digest()

    def sign(self, data: bytes) -> tuple[str, bytes]:
        """Sign with the active key. Returns (key_id, signature)."""
        active = self.active_record
        if active is None:
            raise ContractError("no active key in ring")
        return active.key_id, self._mac(active.key, data)

    def verify(self, key_id: str, data: bytes, signature: bytes) -> bool:
        try:
            record = self.get(key_id)
        except ContractError:
            return False
        if not record.active:
            if record.verify_until is None or self.clock() > record.verify_until:
                return False  # L-R4: window closed
        return hmac.compare_digest(self._mac(record.key, data), signature)

    def verify_strict(self, key_id: str, data: bytes, signature: bytes) -> None:
        if not self.verify(key_id, data, signature):
            raise ContractError(f"signature verification failed for key {key_id!r}")
