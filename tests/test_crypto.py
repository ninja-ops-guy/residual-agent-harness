"""Track L tests: crypto provider, KMS interface, AES-GCM backup path, rotation."""
import os

import pytest

from residual.core import ContractError
from residual.crypto import (
    CryptoProvider,
    KeyRing,
    KmsProvider,
    LocalDevCryptoProvider,
    LocalKmsProvider,
    aesgcm_decrypt,
    aesgcm_encrypt,
    backend_name,
)
from residual.crypto._aesgcm_fallback import (
    fallback_aesgcm_decrypt,
    fallback_aesgcm_encrypt,
)


# -- AES-GCM core (L-R3) ----------------------------------------------------

def test_aesgcm_roundtrip():
    key = os.urandom(32)
    blob = aesgcm_encrypt(key, b"secret backup", aad=b"ctx")
    assert aesgcm_decrypt(key, blob, aad=b"ctx") == b"secret backup"


def test_aesgcm_random_nonces():
    key = os.urandom(32)
    a = aesgcm_encrypt(key, b"same")
    b = aesgcm_encrypt(key, b"same")
    assert a != b and a[:12] != b[:12]


def test_aesgcm_tamper_rejected():
    key = os.urandom(32)
    blob = bytearray(aesgcm_encrypt(key, b"data", aad=b"ctx"))
    blob[-1] ^= 1
    with pytest.raises(ContractError):
        aesgcm_decrypt(key, bytes(blob), aad=b"ctx")
    with pytest.raises(ContractError):
        aesgcm_decrypt(key, aesgcm_encrypt(key, b"data", aad=b"ctx"), aad=b"wrong")


def test_aesgcm_key_and_nonce_validation():
    with pytest.raises(ContractError):
        aesgcm_encrypt(b"short", b"x")
    with pytest.raises(ContractError):
        aesgcm_encrypt(os.urandom(32), b"x", nonce=b"short")
    with pytest.raises(ContractError):
        aesgcm_decrypt(os.urandom(32), b"tiny")


def test_fallback_matches_reference_backend():
    """Stdlib fallback MUST agree with the cryptography backend (L-R3)."""
    cryptography = pytest.importorskip("cryptography")
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    for key_len in (16, 24, 32):
        key = os.urandom(key_len)
        nonce = os.urandom(12)
        pt = os.urandom(200)
        aad = b"header"
        assert fallback_aesgcm_encrypt(key, nonce, pt, aad) == AESGCM(key).encrypt(nonce, pt, aad)
        assert fallback_aesgcm_decrypt(key, nonce, AESGCM(key).encrypt(nonce, pt, aad), aad) == pt


def test_fallback_non_standard_nonce_length():
    cryptography = pytest.importorskip("cryptography")
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key, nonce = os.urandom(32), os.urandom(20)  # exercises the GHASH J0 path
    pt, aad = b"payload", b""
    assert fallback_aesgcm_encrypt(key, nonce, pt, aad) == AESGCM(key).encrypt(nonce, pt, None)


def test_fallback_rejects_bad_tag():
    key, nonce = os.urandom(32), os.urandom(12)
    ct = bytearray(fallback_aesgcm_encrypt(key, nonce, b"data", b""))
    ct[-1] ^= 1
    with pytest.raises(ContractError):
        fallback_aesgcm_decrypt(key, nonce, bytes(ct), b"")


def test_backend_name_reported():
    assert backend_name() in ("cryptography", "stdlib-fallback")


# -- CryptoProvider / KmsProvider (L-R1, L-R2) -------------------------------

def test_local_dev_provider_sign_verify():
    p = LocalDevCryptoProvider()
    sig = p.sign(b"message")
    assert p.verify(b"message", sig)
    assert not p.verify(b"other", sig)
    assert not p.verify(b"message", b"\x00" * 32)


def test_local_dev_provider_encrypt_decrypt():
    p = LocalDevCryptoProvider()
    blob = p.encrypt(b"payload", aad=b"aad")
    assert p.decrypt(blob, aad=b"aad") == b"payload"
    with pytest.raises(ContractError):
        p.decrypt(blob, aad=b"other")


def test_providers_are_abstract():
    with pytest.raises(TypeError):
        CryptoProvider()
    with pytest.raises(TypeError):
        KmsProvider()


def test_local_kms_wrap_unwrap():
    kms = LocalKmsProvider(master_secret=b"m" * 32)
    dek, wrapped = kms.generate_data_key(kek_id="backup")
    assert kms.unwrap_key(wrapped, kek_id="backup") == dek
    other = LocalKmsProvider(master_secret=b"n" * 32)
    with pytest.raises(ContractError):
        other.unwrap_key(wrapped, kek_id="backup")


def test_local_kms_kek_isolation():
    kms = LocalKmsProvider(master_secret=b"m" * 32)
    dek, wrapped = kms.generate_data_key(kek_id="a")
    with pytest.raises(ContractError):
        kms.unwrap_key(wrapped, kek_id="b")


def test_backup_envelope_roundtrip_and_tamper():
    p = LocalDevCryptoProvider()
    env = p.encrypt_backup(b"full station backup", kek_id="nightly")
    assert env["schema"] == "residual.backup.v1"
    assert p.decrypt_backup(env) == b"full station backup"
    tampered = dict(env, ciphertext=env["ciphertext"][:-2] + ("00" if not env["ciphertext"].endswith("00") else "01"))
    with pytest.raises(ContractError):
        p.decrypt_backup(tampered)
    with pytest.raises(ContractError):
        p.decrypt_backup(dict(env, schema="unknown"))


def test_backup_with_explicit_kms():
    kms = LocalKmsProvider(master_secret=b"k" * 32)
    p = LocalDevCryptoProvider(kms=kms)
    env = p.encrypt_backup(b"data", kek_id="offsite")
    assert p.decrypt_backup(env) == b"data"
    wrong_kms = LocalKmsProvider(master_secret=b"z" * 32)
    with pytest.raises(ContractError):
        p.decrypt_backup(env, kms=wrong_kms)


# -- Key rotation (L-R4) ------------------------------------------------------

def _clock():
    state = [1000.0]
    return state, (lambda: state[0])


def test_rotation_sign_verify_with_active_key():
    _state, clock = _clock()
    ring = KeyRing(verify_window_seconds=60, clock=clock)
    ring.add_key("k1")
    kid, sig = ring.sign(b"doc")
    assert kid == "k1"
    ring.verify_strict(kid, b"doc", sig)


def test_rotation_old_key_verifiable_within_window():
    state, clock = _clock()
    ring = KeyRing(verify_window_seconds=60, clock=clock)
    ring.add_key("k1")
    kid, sig = ring.sign(b"doc")
    ring.rotate("k2")
    state[0] += 30
    assert ring.verify(kid, b"doc", sig) is True
    status = ring.status()
    assert status["keys"]["k1"]["verifiable"] is True
    assert status["active_key_id"] == "k2"


def test_rotation_old_key_rejected_after_window():
    state, clock = _clock()
    ring = KeyRing(verify_window_seconds=60, clock=clock)
    ring.add_key("k1")
    kid, sig = ring.sign(b"doc")
    ring.rotate("k2")
    state[0] += 120
    assert ring.verify(kid, b"doc", sig) is False
    with pytest.raises(ContractError):
        ring.verify_strict(kid, b"doc", sig)


def test_rotation_unknown_key_rejected():
    _state, clock = _clock()
    ring = KeyRing(clock=clock)
    ring.add_key("k1")
    assert ring.verify("nope", b"doc", b"\x00" * 32) is False


def test_rotation_rejects_duplicate_and_bad_window():
    _state, clock = _clock()
    ring = KeyRing(clock=clock)
    ring.add_key("k1")
    with pytest.raises(ContractError):
        ring.add_key("k1")
    with pytest.raises(ContractError):
        ring.rotate("k1")
    with pytest.raises(ContractError):
        KeyRing(verify_window_seconds=0)


def test_sign_requires_active_key():
    _state, clock = _clock()
    ring = KeyRing(clock=clock)
    with pytest.raises(ContractError):
        ring.sign(b"doc")
