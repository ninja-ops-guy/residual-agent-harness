"""Encrypted daily backups with separately managed keys.

Implements ENT4-R5: backups include the receipt chain, observation log,
station state, tenant configurations, and module registry; they are
taken at least daily; and encryption keys are managed separately from
the station via a pluggable key manager.

Encryption note: the Python standard library has no AES, so this module
uses a documented AEAD construction built from hashlib/hmac:

* keystream: SHA-256(key || nonce || counter) blocks XORed with the
  plaintext (a hash-based stream cipher);
* authentication: HMAC-SHA-256 over (nonce || aad || ciphertext) with an
  independently derived MAC key, encrypt-then-MAC.

Both keys are derived from the managed master key with distinct labels
(HMAC-based KDF). This is a stdlib-only construction for the offline
simulation; production deployments should plug in an AEAD such as
AES-GCM via the same KeyManager interface.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass, field
from typing import Protocol

from ..core import ContractError, canonical
from .chain import ReceiptChain
from .clock import Clock
from .events import EventJournal, BACKUP_EVENT

BACKUP_SCHEMA = "residual.hadr.backup.v1"
BACKUP_INTERVAL_SECONDS = 24 * 60 * 60  # at least daily (ENT4-R5)

REQUIRED_COMPONENTS = (
    "receipt_chain",
    "observation_log",
    "station_state",
    "tenant_configs",
    "module_registry",
)


class KeyManager(Protocol):
    """Pluggable, station-external key management. Implements ENT4-R5."""

    def current_key_id(self) -> str:
        ...

    def get_key(self, key_id: str) -> bytes:
        ...


@dataclass
class LocalKeyManager:
    """Standalone key store kept separate from the station. Implements ENT4-R5.

    Each manager instance derives its keys from its own random ``seed``
    so keys are independent per manager (and per rotation), modelling a
    key store that lives outside the station.
    """

    seed: bytes = field(default_factory=lambda: os.urandom(32))
    keys: dict[str, bytes] = field(default_factory=dict)

    def __post_init__(self):
        if not self.keys:
            self.rotate()

    def rotate(self) -> str:
        key_id = hmac.new(
            self.seed, f"key-id-{len(self.keys)}".encode("utf-8"),
            hashlib.sha256).hexdigest()[:16]
        self.keys[key_id] = hmac.new(
            self.seed, f"key-material-{key_id}".encode("utf-8"), hashlib.sha256).digest()
        return key_id

    def current_key_id(self) -> str:
        return list(self.keys)[-1]

    def get_key(self, key_id: str) -> bytes:
        try:
            return self.keys[key_id]
        except KeyError:
            raise ContractError(f"unknown backup key: {key_id!r}") from None


def _kdf(master: bytes, label: bytes) -> bytes:
    return hmac.new(master, label, hashlib.sha256).digest()


def _keystream_xor(key: bytes, nonce: bytes, data: bytes) -> bytes:
    out = bytearray(len(data))
    offset = 0
    counter = 0
    while offset < len(data):
        block = hashlib.sha256(
            key + nonce + counter.to_bytes(8, "big")).digest()
        take = min(len(block), len(data) - offset)
        for i in range(take):
            out[offset + i] = data[offset + i] ^ block[i]
        offset += take
        counter += 1
    return bytes(out)


def encrypt_aead(master_key: bytes, nonce: bytes, plaintext: bytes, aad: bytes) -> tuple[bytes, bytes]:
    """Encrypt-then-MAC AEAD (stdlib construction). Implements ENT4-R5."""
    enc_key = _kdf(master_key, b"residual.hadr.enc")
    mac_key = _kdf(master_key, b"residual.hadr.mac")
    ciphertext = _keystream_xor(enc_key, nonce, plaintext)
    tag = hmac.new(mac_key, nonce + aad + ciphertext, hashlib.sha256).digest()
    return ciphertext, tag


def decrypt_aead(master_key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes, tag: bytes) -> bytes:
    """Verify and decrypt. Implements ENT4-R5 and ENT4-R6."""
    enc_key = _kdf(master_key, b"residual.hadr.enc")
    mac_key = _kdf(master_key, b"residual.hadr.mac")
    expect = hmac.new(mac_key, nonce + aad + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(expect, tag):
        raise ContractError("backup authentication failed")
    return _keystream_xor(enc_key, nonce, ciphertext)


@dataclass(frozen=True)
class BackupRecord:
    """An encrypted backup artifact. Implements ENT4-R5."""

    backup_id: str
    created_at: float
    key_id: str
    nonce: bytes
    ciphertext: bytes
    tag: bytes
    components: tuple[str, ...]
    plaintext_hash: str


@dataclass
class BackupManager:
    """Takes encrypted daily backups. Implements ENT4-R5; receipts them per ENT4-R8."""

    clock: Clock
    journal: EventJournal
    key_manager: KeyManager
    backups: list[BackupRecord] = field(default_factory=list)

    def build_snapshot(self, *, receipt_chain: ReceiptChain, observation_log: list[str],
                       station_state: dict, tenant_configs: dict,
                       module_registry: dict) -> dict:
        """Collect all mandated components. Implements ENT4-R5."""
        snapshot = {
            "schema": BACKUP_SCHEMA,
            "created_at": self.clock.now(),
            "receipt_chain": [
                {
                    "receipt_id": r.receipt_id,
                    "sequence": r.sequence,
                    "task_id": r.task_id,
                    "payload": r.payload,
                    "prev_hash": r.prev_hash,
                }
                for r in receipt_chain.receipts
            ],
            "observation_log": list(observation_log),
            "station_state": dict(station_state),
            "tenant_configs": dict(tenant_configs),
            "module_registry": dict(module_registry),
        }
        return snapshot

    def take_backup(self, *, receipt_chain: ReceiptChain, observation_log: list[str],
                    station_state: dict, tenant_configs: dict,
                    module_registry: dict) -> BackupRecord:
        """Encrypt and store a backup; receipt the operation (ENT4-R8). Implements ENT4-R5."""
        snapshot = self.build_snapshot(
            receipt_chain=receipt_chain, observation_log=observation_log,
            station_state=station_state, tenant_configs=tenant_configs,
            module_registry=module_registry)
        plaintext = canonical(snapshot).encode("utf-8")
        key_id = self.key_manager.current_key_id()
        nonce = hashlib.sha256(
            f"nonce:{len(self.backups)}:{self.clock.now()}".encode("utf-8")).digest()[:16]
        aad = BACKUP_SCHEMA.encode("utf-8")
        ciphertext, tag = encrypt_aead(self.key_manager.get_key(key_id), nonce, plaintext, aad)
        record = BackupRecord(
            backup_id=hashlib.sha256(nonce + ciphertext).hexdigest(),
            created_at=self.clock.now(),
            key_id=key_id,
            nonce=nonce,
            ciphertext=ciphertext,
            tag=tag,
            components=REQUIRED_COMPONENTS,
            plaintext_hash=hashlib.sha256(plaintext).hexdigest(),
        )
        self.backups.append(record)
        self.journal.record(BACKUP_EVENT, {
            "backup_id": record.backup_id,
            "created_at": record.created_at,
            "key_id": record.key_id,
            "components": list(record.components),
        })
        return record

    def backup_due(self) -> bool:
        """True when the daily interval has elapsed. Implements ENT4-R5."""
        if not self.backups:
            return True
        return self.clock.now() - self.backups[-1].created_at >= BACKUP_INTERVAL_SECONDS

    def take_daily_backup_if_due(self, **components) -> BackupRecord | None:
        """Enforce the at-least-daily schedule. Implements ENT4-R5."""
        if not self.backup_due():
            return None
        return self.take_backup(**components)


def decrypt_backup(record: BackupRecord, key_manager: KeyManager) -> dict:
    """Decrypt a backup to its snapshot. Implements ENT4-R5 and ENT4-R6."""
    plaintext = decrypt_aead(
        key_manager.get_key(record.key_id), record.nonce, record.ciphertext,
        BACKUP_SCHEMA.encode("utf-8"), record.tag)
    snapshot = json.loads(plaintext.decode("utf-8"))
    if hashlib.sha256(plaintext).hexdigest() != record.plaintext_hash:
        raise ContractError("backup plaintext hash mismatch")
    return snapshot
