"""Multi-factor authentication (MFA) enforcement for Enterprise IAM.

Implements ENT1-R7: MFA may be delegated to the IdP (preferred — the
OIDC ``amr`` claim or SAML AuthnContext carries the assurance) or
enforced locally via RFC 6238 TOTP. Privileged actions (HITL approval,
policy modification, module installation) require MFA regardless of
session age.
"""
from __future__ import annotations

import hashlib
import hmac
import struct
from typing import Callable

from ..core import ContractError, identifier

#: Actions that always require MFA, regardless of session age. ENT1-R7.
PRIVILEGED_ACTIONS = frozenset({
    "hitl_approval",
    "policy_modification",
    "module_installation",
})

#: IdP assurance markers treated as delegated MFA. ENT1-R7.
IDP_MFA_AMR = frozenset({"mfa", "otp", "hwk", "fido2", "webauthn"})
IDP_MFA_AUTHN_CONTEXT = (
    "urn:oasis:names:tc:SAML:2.0:ac:classes:Multifactor",
    "http://schemas.microsoft.com/claims/multipleauthn",
)


def generate_totp(secret: bytes, at: int, *, period: int = 30, digits: int = 6) -> str:
    """Generate an RFC 6238 TOTP code (SHA-1). Implements ENT1-R7."""
    if not isinstance(secret, bytes) or not secret:
        raise ContractError("totp secret must be non-empty bytes")
    if type(at) is not int or at < 0:
        raise ContractError("totp time must be a nonnegative integer")
    if type(period) is not int or period < 1 or type(digits) is not int or not 6 <= digits <= 8:
        raise ContractError("invalid totp period/digits")
    counter = at // period
    digest = hmac.new(secret, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10 ** digits)).zfill(digits)


def verify_totp(secret: bytes, code: str, at: int, *, period: int = 30, digits: int = 6,
                window: int = 1) -> bool:
    """Verify a TOTP code within +/- ``window`` periods. Implements ENT1-R7."""
    if not isinstance(code, str) or not code.isdigit():
        return False
    if type(window) is not int or window < 0:
        raise ContractError("window must be a nonnegative integer")
    for drift in range(-window, window + 1):
        step = at + drift * period
        if step < 0:
            continue
        if hmac.compare_digest(generate_totp(secret, step, period=period, digits=digits), code):
            return True
    return False


class MFAManager:
    """Enforces MFA for privileged actions. Implements ENT1-R7.

    Delegation to the IdP is preferred: an Identity whose ``amr``
    contains a known MFA method (or whose SAML AuthnContext signals
    multifactor) satisfies MFA. Otherwise a local TOTP verification is
    required immediately before the privileged action — regardless of
    session age.
    """

    def __init__(self, clock: Callable[[], int]):
        if not callable(clock):
            raise ContractError("clock must be callable")
        self._clock = clock
        self._local_verifications: dict[str, int] = {}

    def idp_mfa_satisfied(self, amr: tuple[str, ...] = (), authn_context: str | None = None) -> bool:
        """True when the IdP already performed MFA. Implements ENT1-R7."""
        if any(str(a).lower() in IDP_MFA_AMR for a in amr):
            return True
        return authn_context in IDP_MFA_AUTHN_CONTEXT

    def verify_local(self, subject_id: str, secret: bytes, code: str) -> bool:
        """Verify a local TOTP factor and remember it. Implements ENT1-R7."""
        identifier(subject_id)
        ok = verify_totp(secret, code, self._clock())
        if ok:
            self._local_verifications[subject_id] = self._clock()
        return ok

    def has_local_mfa(self, subject_id: str) -> bool:
        identifier(subject_id)
        return subject_id in self._local_verifications

    def require_privileged(
        self,
        action: str,
        subject_id: str,
        *,
        amr: tuple[str, ...] = (),
        authn_context: str | None = None,
    ) -> None:
        """Enforce MFA for a privileged action, regardless of session age.

        Implements ENT1-R7: raises ContractError unless the IdP performed
        MFA (preferred) or a local TOTP verification is on record.
        """
        identifier(subject_id)
        if action not in PRIVILEGED_ACTIONS:
            raise ContractError(f"unknown privileged action {action!r}")
        if self.idp_mfa_satisfied(amr, authn_context):
            return
        if self.has_local_mfa(subject_id):
            return
        raise ContractError(f"MFA required for privileged action {action!r}")
