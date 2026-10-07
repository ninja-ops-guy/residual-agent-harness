from __future__ import annotations
import base64,hashlib
from pathlib import Path
class SignatureError(ValueError): pass
def package_sha256(path): return hashlib.sha256(Path(path).read_bytes()).digest()
def verify_signature(package_path,public_key_b64,signature_b64):
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        key_bytes=base64.b64decode(public_key_b64,validate=True); sig=base64.b64decode(signature_b64,validate=True); message=b"residual-module-v1\0"+package_sha256(package_path)+b"\0"+key_bytes; Ed25519PublicKey.from_public_bytes(key_bytes).verify(sig,message)
    except ImportError as exc: raise SignatureError("cryptography is required for module signature verification") from exc
    except Exception as exc: raise SignatureError("invalid module signature") from exc
