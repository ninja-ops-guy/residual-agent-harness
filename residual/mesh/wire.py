"""Versioned, signed end-to-end encrypted mesh envelopes.

Host-pinned Ed25519 identities and X25519 encryption keys are mandatory. This
protocol provides message confidentiality/integrity, not consensus, proof of
correct execution, automatic trust, forward secrecy or guaranteed delivery.
"""
from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
import hashlib
import json
import os
import time

from ..core import ContractError, canonical, strict_json
from .node import MeshMessage, MeshNode

MAX_WIRE_BYTES = 65_536
SCHEMA = "residual.mesh.envelope.v1"


def _encode(data: bytes) -> str:
    return base64.b64encode(data).decode('ascii')


def _decode(data: str, length: int | None = None) -> bytes:
    result = base64.b64decode(data, validate=True)
    if length is not None and len(result) != length:
        raise ValueError()
    return result


@dataclass(frozen=True)
class PeerKeys:
    signing_key: str  # raw Ed25519 public key, hex; matches MeshIdentity
    encryption_key: str  # raw X25519 public key, hex

    def __post_init__(self):
        for value in (self.signing_key, self.encryption_key):
            if not isinstance(value, str) or len(value) != 64 or bytes.fromhex(value).hex() != value:
                raise ContractError("peer keys require canonical 32-byte hex encodings")


class DeviceKeys:
    """In-memory private keys. The host owns secure storage and provisioning."""
    def __init__(self, signing_key, encryption_key):
        self._signing, self._encryption = signing_key, encryption_key

    @classmethod
    def generate(cls):
        from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
        return cls(ed25519.Ed25519PrivateKey.generate(), x25519.X25519PrivateKey.generate())

    @property
    def public(self) -> PeerKeys:
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        def raw(key):
            return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        return PeerKeys(raw(self._signing), raw(self._encryption))

    def sign(self, data: bytes) -> str:
        return self._signing.sign(data).hex()

    @staticmethod
    def verify(public_key: str, data: bytes, signature: str) -> bool:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key)).verify(bytes.fromhex(signature), data)
            return True
        except Exception:
            return False


def _derive(shared: bytes, header: dict) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                info=SCHEMA.encode() + b'\0' + canonical(header).encode()).derive(shared)


def inspect_envelope(raw: str | bytes) -> dict:
    """Bounded structural parsing only; this does not authenticate the sender."""
    try:
        if not isinstance(raw, (str, bytes)) or len(raw.encode() if isinstance(raw, str) else raw) > MAX_WIRE_BYTES:
            raise ValueError()
        envelope = strict_json(raw.decode('utf-8') if isinstance(raw, bytes) else raw)
        if not isinstance(envelope, dict) or set(envelope) != {'header', 'ciphertext', 'signature'}:
            raise ValueError()
        header = envelope['header']
        if (not isinstance(header, dict) or set(header) != {'schema','room','sender','recipient','message_id','issued_at','ephemeral','nonce'}
                or header['schema'] != SCHEMA or type(header['issued_at']) is not int):
            raise ValueError()
        for name in ('room','sender','recipient','message_id'):
            if not isinstance(header[name], str) or not 1 <= len(header[name]) <= 128 or any(ord(c) < 32 for c in header[name]):
                raise ValueError()
        _decode(header['ephemeral'],32); _decode(header['nonce'],12)
        if not isinstance(envelope['signature'], str) or len(envelope['signature']) != 128:
            raise ValueError()
        if not 16 <= len(_decode(envelope['ciphertext'])) <= 48_000:
            raise ValueError()
        return envelope
    except Exception:
        raise ContractError('invalid mesh envelope') from None


class EnvelopeCodec:
    def __init__(self, node: MeshNode, keys: DeviceKeys, peers: dict[str, PeerKeys], *, room: str,
                 max_age_s: int = 300):
        if keys.public.signing_key != node.identity.public_key:
            raise ContractError('device keys do not match mesh identity')
        if not isinstance(room,str) or not 1 <= len(room) <= 128 or type(max_age_s) is not int or not 1 <= max_age_s <= 3600:
            raise ContractError('invalid mesh room or replay window')
        self.node, self.keys, self.peers, self.room = node, keys, dict(peers), room
        self.max_age_s = max_age_s

    def _peer(self, device_id):
        peer = self.node.peers.get(device_id)
        keys = self.peers.get(device_id)
        if (peer is None or keys is None or peer.public_key != keys.signing_key
                or self.node.is_revoked(device_id)):
            raise ContractError('mesh peer is not admitted')
        return keys

    def seal(self, message: MeshMessage, recipient: str) -> str:
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        peer = self._peer(recipient)
        if message.author_id != self.node.identity.device_id:
            raise ContractError('cannot transmit another device message')
        ephemeral = X25519PrivateKey.generate()
        nonce = os.urandom(12)
        header = {'schema':SCHEMA,'room':self.room,'sender':message.author_id,'recipient':recipient,
            'message_id':message.message_id,'issued_at':int(time.time()),
            'ephemeral':_encode(ephemeral.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)),
            'nonce':_encode(nonce)}
        shared = ephemeral.exchange(X25519PublicKey.from_public_bytes(bytes.fromhex(peer.encryption_key)))
        plain = canonical({**asdict(message), 'kind':message.kind.value}).encode()
        body = {'header':header,'ciphertext':_encode(AESGCM(_derive(shared,header)).encrypt(nonce,plain,canonical(header).encode()))}
        envelope = {**body,'signature':self.keys.sign(canonical(body).encode())}
        encoded = canonical(envelope)
        inspect_envelope(encoded)
        return encoded

    def open(self, raw: str | bytes) -> MeshMessage:
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        try:
            envelope = inspect_envelope(raw); header = envelope['header']
            if (header['room'] != self.room or header['recipient'] != self.node.identity.device_id
                    or not -30 <= time.time()-header['issued_at'] <= self.max_age_s):
                raise ValueError()
            peer = self._peer(header['sender'])
            body = {'header':header,'ciphertext':envelope['ciphertext']}
            if not DeviceKeys.verify(peer.signing_key,canonical(body).encode(),envelope['signature']):
                raise ValueError()
            shared = self.keys._encryption.exchange(X25519PublicKey.from_public_bytes(_decode(header['ephemeral'],32)))
            plain = AESGCM(_derive(shared,header)).decrypt(_decode(header['nonce'],12),_decode(envelope['ciphertext']),canonical(header).encode())
            data = strict_json(plain.decode('utf-8'))
            if not isinstance(data,dict) or set(data) != set(MeshMessage.__dataclass_fields__):
                raise ValueError()
            if (type(data['timestamp_ns']) is not int or data['timestamp_ns'] < 0
                    or not isinstance(data['signature'], str) or len(data['signature']) != 128
                    or not isinstance(data['prev_hash'], str)
                    or (data['prev_hash'] != 'GENESIS' and (len(data['prev_hash']) != 64 or bytes.fromhex(data['prev_hash']).hex() != data['prev_hash']))):
                raise ValueError()
            message = MeshMessage(**data)
            if message.author_id != header['sender'] or message.message_id != header['message_id']:
                raise ValueError()
            return message
        except Exception:
            raise ContractError('mesh envelope authentication failed') from None
