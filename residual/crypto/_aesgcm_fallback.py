"""Pure-stdlib AES-GCM fallback (Track L, L-R3).

This module exists so backup encryption remains functional on hosts where the
``cryptography`` package is not installed. It implements FIPS-197 AES
(128/192/256, encryption direction only) and NIST SP 800-38D GCM in pure
Python on top of ``hashlib``/``hmac``-era stdlib only.

WARNING: this fallback is constant-*correct* but not constant-*time* and is
roughly two orders of magnitude slower than the ``cryptography`` backend.
It is intended for development, tests, and disaster-recovery bootstrap only;
production deployments MUST install ``cryptography``. ``backend_name()``
reports which backend is active so operators can audit this.
"""
from __future__ import annotations

import os

from ..core import ContractError

# ---------------------------------------------------------------------------
# AES (FIPS-197), encrypt-direction block primitive
# ---------------------------------------------------------------------------

_SBOX = (
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
    0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
    0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
    0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
    0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
    0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
    0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
    0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
    0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
    0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16,
)

_RCON = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)


def _xtime(a: int) -> int:
    a <<= 1
    if a & 0x100:
        a ^= 0x11B
    return a & 0xFF


def _mul(a: int, b: int) -> int:
    r = 0
    while b:
        if b & 1:
            r ^= a
        a = _xtime(a)
        b >>= 1
    return r


def _expand_key(key: bytes):
    nk = len(key) // 4
    if nk not in (4, 6, 8):
        raise ContractError("AES key must be 16, 24, or 32 bytes")
    nr = nk + 6
    w = [list(key[4 * i:4 * i + 4]) for i in range(nk)]
    for i in range(nk, 4 * (nr + 1)):
        temp = list(w[i - 1])
        if i % nk == 0:
            temp = [_SBOX[temp[1]] ^ _RCON[i // nk - 1], _SBOX[temp[2]], _SBOX[temp[3]], _SBOX[temp[0]]]
        elif nk > 6 and i % nk == 4:
            temp = [_SBOX[b] for b in temp]
        w.append([w[i - nk][j] ^ temp[j] for j in range(4)])
    # round keys as 16-byte values, column-major per FIPS-197
    return [bytes(sum(w[4 * r:4 * r + 4], [])) for r in range(nr + 1)]


def _add_round_key(state: list, rk: bytes) -> None:
    for i in range(16):
        state[i] ^= rk[i]


def _sub_bytes(state: list) -> None:
    for i in range(16):
        state[i] = _SBOX[state[i]]


def _shift_rows(state: list) -> None:
    # state is column-major: state[row + 4*col]
    for row in (1, 2, 3):
        vals = [state[row + 4 * c] for c in range(4)]
        for c in range(4):
            state[row + 4 * c] = vals[(c + row) % 4]


def _mix_columns(state: list) -> None:
    for c in range(4):
        col = state[4 * c:4 * c + 4]
        state[4 * c] = _mul(col[0], 2) ^ _mul(col[1], 3) ^ col[2] ^ col[3]
        state[4 * c + 1] = col[0] ^ _mul(col[1], 2) ^ _mul(col[2], 3) ^ col[3]
        state[4 * c + 2] = col[0] ^ col[1] ^ _mul(col[2], 2) ^ _mul(col[3], 3)
        state[4 * c + 3] = _mul(col[0], 3) ^ col[1] ^ col[2] ^ _mul(col[3], 2)


def _aes_encrypt_block(round_keys: list, block: bytes) -> bytes:
    if len(block) != 16:
        raise ContractError("AES block must be 16 bytes")
    state = list(block)
    _add_round_key(state, round_keys[0])
    for r in range(1, len(round_keys) - 1):
        _sub_bytes(state)
        _shift_rows(state)
        _mix_columns(state)
        _add_round_key(state, round_keys[r])
    _sub_bytes(state)
    _shift_rows(state)
    _add_round_key(state, round_keys[-1])
    return bytes(state)


# ---------------------------------------------------------------------------
# GCM (NIST SP 800-38D)
# ---------------------------------------------------------------------------

def _gf128_mul(x: int, y: int) -> int:
    # Multiplication in GF(2^128) with the GCM polynomial; bit-reflected.
    r = 0xE1000000000000000000000000000000
    z = 0
    v = x
    for i in range(128):
        if (y >> (127 - i)) & 1:
            z ^= v
        v = (v >> 1) ^ (r if v & 1 else 0)
    return z


def _ghash(h: int, data: bytes) -> int:
    y = 0
    for off in range(0, len(data), 16):
        block = data[off:off + 16]
        block = block + b"\x00" * (16 - len(block))
        y = _gf128_mul(y ^ int.from_bytes(block, "big"), h)
    return y


def _inc32(counter: bytes) -> bytes:
    prefix = counter[:12]
    low = (int.from_bytes(counter[12:], "big") + 1) & 0xFFFFFFFF
    return prefix + low.to_bytes(4, "big")


def _gctr(round_keys: list, icb: bytes, data: bytes) -> bytes:
    if not data:
        return b""
    out = bytearray()
    cb = icb
    for off in range(0, len(data), 16):
        block = data[off:off + 16]
        ks = _aes_encrypt_block(round_keys, cb)
        out += bytes(a ^ b for a, b in zip(block, ks))
        cb = _inc32(cb)
    return bytes(out)


def _j0(round_keys: list, nonce: bytes) -> bytes:
    if len(nonce) == 12:
        return nonce + b"\x00\x00\x00\x01"
    h = int.from_bytes(_aes_encrypt_block(round_keys, b"\x00" * 16), "big")
    bitlen = (len(nonce) * 8).to_bytes(8, "big")
    s = _ghash(h, nonce + b"\x00" * ((16 - len(nonce) % 16) % 16) + b"\x00" * 8 + bitlen)
    return s.to_bytes(16, "big")


def fallback_aesgcm_encrypt(key: bytes, nonce: bytes, plaintext: bytes, aad: bytes) -> bytes:
    """Encrypt with AES-GCM; returns ciphertext || 16-byte tag."""
    rk = _expand_key(key)
    j0 = _j0(rk, nonce)
    ciphertext = _gctr(rk, _inc32(j0), plaintext)
    h = int.from_bytes(_aes_encrypt_block(rk, b"\x00" * 16), "big")
    lens = (len(aad) * 8).to_bytes(8, "big") + (len(ciphertext) * 8).to_bytes(8, "big")
    padded = aad + b"\x00" * ((16 - len(aad) % 16) % 16) + ciphertext + b"\x00" * ((16 - len(ciphertext) % 16) % 16)
    s = _ghash(h, padded + lens)
    tag = (s ^ int.from_bytes(_aes_encrypt_block(rk, j0), "big")).to_bytes(16, "big")
    return ciphertext + tag


def fallback_aesgcm_decrypt(key: bytes, nonce: bytes, ciphertext_and_tag: bytes, aad: bytes) -> bytes:
    """Decrypt AES-GCM; raises ContractError on tag mismatch."""
    if len(ciphertext_and_tag) < 16:
        raise ContractError("ciphertext too short for GCM tag")
    ciphertext, tag = ciphertext_and_tag[:-16], ciphertext_and_tag[-16:]
    rk = _expand_key(key)
    j0 = _j0(rk, nonce)
    h = int.from_bytes(_aes_encrypt_block(rk, b"\x00" * 16), "big")
    lens = (len(aad) * 8).to_bytes(8, "big") + (len(ciphertext) * 8).to_bytes(8, "big")
    padded = aad + b"\x00" * ((16 - len(aad) % 16) % 16) + ciphertext + b"\x00" * ((16 - len(ciphertext) % 16) % 16)
    s = _ghash(h, padded + lens)
    expected = (s ^ int.from_bytes(_aes_encrypt_block(rk, j0), "big")).to_bytes(16, "big")
    import hmac as _hmac
    if not _hmac.compare_digest(expected, tag):
        raise ContractError("AES-GCM authentication failed")
    return _gctr(rk, _inc32(j0), ciphertext)


def random_nonce() -> bytes:
    return os.urandom(12)
