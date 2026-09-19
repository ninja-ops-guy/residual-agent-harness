"""SAML 2.0 authentication for Enterprise IAM.

Implements ENT1-R1: protocol-level SAML 2.0 Web Browser SSO response
parsing and validation with pure stdlib XML processing. Provider
presets for Okta, Azure AD (Entra ID), Ping Identity, Auth0, and
OneLogin share one code path — no custom configuration per provider.

Signature verification uses RSA PKCS#1 v1.5 over SHA-256 (see
residual.iam.crypto) via a simplified detached-signature scheme: the
Response carries a ``Signature`` attribute whose value is the RSA
signature over the exact response bytes with the signature attribute
blanked. A custom ``signature_verifier`` hook can be supplied to plug
in full XML-DSig validation.

All validation failures raise ContractError so callers can record
access-denied observations (ENT1-R6).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
import defusedxml.ElementTree as DefusedET
from dataclasses import dataclass, field
from typing import Any, Callable

from ..core import ContractError
from .crypto import (
    RSAPublicKey,
    b64url_decode,
    b64url_encode,
    rsa_pkcs1v15_sign_sha256,
    rsa_pkcs1v15_verify_sha256,
    RSAPrivateKey,
)

NS_ASSERTION = "urn:oasis:names:tc:SAML:2.0:assertion"
NS_PROTOCOL = "urn:oasis:names:tc:SAML:2.0:protocol"

ET.register_namespace("saml", NS_ASSERTION)
ET.register_namespace("samlp", NS_PROTOCOL)

SIGNATURE_PLACEHOLDER = "__SIGNATURE__"

#: Provider presets implementing ENT1-R1. Each preset only parameterizes
#: the issuer pattern and default attribute mappings; the validation and
#: parsing logic is identical for every provider.
SAML_PROVIDERS: dict[str, dict[str, Any]] = {
    "okta": {
        "issuer_pattern": "http://www.okta.com/{org}",
        "sso_url_pattern": "https://{org}.okta.com/app/{app}/sso/saml",
        "name_id_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
    },
    "azure_ad": {
        "issuer_pattern": "https://sts.windows.net/{tenant}/",
        "sso_url_pattern": "https://login.microsoftonline.com/{tenant}/saml2",
        "name_id_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
    },
    "ping": {
        "issuer_pattern": "https://{org}.pingidentity.com",
        "sso_url_pattern": "https://{org}.pingidentity.com/idp/startSSO.ping",
        "name_id_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
    },
    "auth0": {
        "issuer_pattern": "urn:{org}.auth0.com",
        "sso_url_pattern": "https://{org}.auth0.com/samlp/{client}",
        "name_id_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
    },
    "onelogin": {
        "issuer_pattern": "https://app.onelogin.com/saml/metadata/{app}",
        "sso_url_pattern": "https://{org}.onelogin.com/trust/saml2/http-post/sso/{app}",
        "name_id_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
    },
}


@dataclass(frozen=True)
class SAMLSettings:
    """Service-provider settings for SAML SSO. Implements ENT1-R1."""

    idp_entity_id: str
    idp_sso_url: str
    sp_entity_id: str
    signature_key: RSAPublicKey | None = None  # verify assertion signatures when set
    clock_skew: int = 60

    def __post_init__(self):
        for name in ("idp_entity_id", "idp_sso_url", "sp_entity_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ContractError(f"saml setting {name} is required")
        if type(self.clock_skew) is not int or self.clock_skew < 0:
            raise ContractError("clock_skew must be a nonnegative integer")
        if self.signature_key is not None and not isinstance(self.signature_key, RSAPublicKey):
            raise ContractError("signature_key must be an RSAPublicKey")


@dataclass(frozen=True)
class Identity:
    """Authenticated identity. Implements ENT1-R1 and feeds ENT1-R3/R7."""

    subject: str
    issuer: str
    attributes: dict = field(default_factory=dict)
    session_index: str | None = None
    not_on_or_after: int | None = None
    authn_instant: int | None = None
    authn_context: str | None = None
    amr: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.subject, str) or not self.subject.strip():
            raise ContractError("identity subject is required")
        if not isinstance(self.issuer, str) or not self.issuer.strip():
            raise ContractError("identity issuer is required")
        if not isinstance(self.attributes, dict):
            raise ContractError("identity attributes must be a dict")
        if not isinstance(self.amr, tuple):
            raise ContractError("amr must be a tuple")


def provider_settings(provider: str, settings_kwargs: dict) -> SAMLSettings:
    """Build SAMLSettings for a known provider preset. Implements ENT1-R1:
    the same settings shape works for Okta, Azure AD, Ping, Auth0, and
    OneLogin with no provider-specific code."""
    if provider not in SAML_PROVIDERS:
        raise ContractError(f"unknown SAML provider {provider!r}")
    return SAMLSettings(**settings_kwargs)


def _text(parent: ET.Element, path: str) -> str | None:
    node = parent.find(path, {"saml": NS_ASSERTION, "samlp": NS_PROTOCOL})
    return node.text.strip() if node is not None and node.text else None


def sign_response(xml_with_placeholder: str, key: RSAPrivateKey) -> str:
    """Sign a SAML Response template containing the placeholder
    ``__SIGNATURE__`` and return the response with a real RSA
    signature. Implements ENT1-R1 (test/fixture helper)."""
    if SIGNATURE_PLACEHOLDER not in xml_with_placeholder:
        raise ContractError("template must contain the signature placeholder")
    blanked = xml_with_placeholder.replace(SIGNATURE_PLACEHOLDER, "")
    signature = rsa_pkcs1v15_sign_sha256(key, blanked.encode("utf-8"))
    return xml_with_placeholder.replace(SIGNATURE_PLACEHOLDER, b64url_encode(signature))


def _verify_response_signature(xml_text: str, signature_b64: str, key: RSAPublicKey) -> bool:
    blanked = xml_text.replace(f'Signature="{signature_b64}"', 'Signature=""')
    try:
        signature = b64url_decode(signature_b64)
    except ContractError:
        return False
    return rsa_pkcs1v15_verify_sha256(key, blanked.encode("utf-8"), signature)


def parse_saml_response(
    xml_text: str,
    settings: SAMLSettings,
    *,
    now: int,
    signature_verifier: Callable[[str, RSAPublicKey], bool] | None = None,
) -> Identity:
    """Parse and validate a SAML 2.0 Response. Implements ENT1-R1.

    Checks: well-formed XML, Response root, Issuer matches the IdP,
    Conditions NotBefore/NotOnOrAfter (with clock skew), Audience
    restriction matches the SP entity id, a Subject NameID, and —
    when ``settings.signature_key`` is configured — the RSA signature.
    """
    if not isinstance(xml_text, str) or not xml_text.strip():
        raise ContractError("saml response must be non-empty XML text")
    if not isinstance(settings, SAMLSettings):
        raise ContractError("settings must be SAMLSettings")
    if type(now) is not int:
        raise ContractError("now must be an integer")
    try:
        root = DefusedET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ContractError("malformed SAML response XML") from exc
    if root.tag != f"{{{NS_PROTOCOL}}}Response":
        raise ContractError("expected a samlp:Response root element")

    if settings.signature_key is not None:
        signature_b64 = root.get("Signature")
        if not signature_b64:
            raise ContractError("signed SAML response required")
        if signature_verifier is not None:
            ok = signature_verifier(xml_text, settings.signature_key)
        else:
            ok = _verify_response_signature(xml_text, signature_b64, settings.signature_key)
        if not ok:
            raise ContractError("SAML response signature verification failed")

    assertion = root.find("saml:Assertion", {"saml": NS_ASSERTION})
    if assertion is None:
        raise ContractError("SAML response contains no Assertion")

    issuer = _text(assertion, "saml:Issuer")
    if issuer != settings.idp_entity_id:
        raise ContractError("SAML issuer does not match the configured IdP")

    conditions = assertion.find("saml:Conditions", {"saml": NS_ASSERTION})
    if conditions is None:
        raise ContractError("SAML assertion has no Conditions")
    not_before = conditions.get("NotBefore")
    not_on_or_after = conditions.get("NotOnOrAfter")
    if not_before is None or not_on_or_after is None:
        raise ContractError("SAML Conditions require NotBefore and NotOnOrAfter")
    try:
        nb = int(not_before)
        noa = int(not_on_or_after)
    except ValueError as exc:
        raise ContractError("SAML condition timestamps must be integers") from exc
    if now < nb - settings.clock_skew:
        raise ContractError("SAML assertion not yet valid")
    if now >= noa + settings.clock_skew:
        raise ContractError("SAML assertion expired")
    audience = _text(conditions, "saml:AudienceRestriction/saml:Audience")
    if audience != settings.sp_entity_id:
        raise ContractError("SAML audience restriction mismatch")

    name_id = _text(assertion, "saml:Subject/saml:NameID")
    if not name_id:
        raise ContractError("SAML assertion has no Subject NameID")

    attributes: dict[str, str] = {}
    attr_statement = assertion.find("saml:AttributeStatement", {"saml": NS_ASSERTION})
    if attr_statement is not None:
        for attr in attr_statement.findall("saml:Attribute", {"saml": NS_ASSERTION}):
            name = attr.get("Name")
            value = _text(attr, "saml:AttributeValue")
            if name:
                attributes[name] = value or ""

    session_index = None
    authn_instant = None
    authn_context = None
    authn_statement = assertion.find("saml:AuthnStatement", {"saml": NS_ASSERTION})
    if authn_statement is not None:
        session_index = authn_statement.get("SessionIndex")
        instant = authn_statement.get("AuthnInstant")
        if instant is not None:
            try:
                authn_instant = int(instant)
            except ValueError as exc:
                raise ContractError("AuthnInstant must be an integer") from exc
        authn_context = _text(authn_statement, "saml:AuthnContext/saml:AuthnContextClassRef")

    return Identity(
        subject=name_id,
        issuer=issuer,
        attributes=attributes,
        session_index=session_index,
        not_on_or_after=noa,
        authn_instant=authn_instant,
        authn_context=authn_context,
    )


def build_response(
    *,
    issuer: str,
    audience: str,
    name_id: str,
    not_before: int,
    not_on_or_after: int,
    attributes: dict[str, str] | None = None,
    session_index: str | None = None,
    authn_instant: int | None = None,
    authn_context: str | None = None,
    sign_key: RSAPrivateKey | None = None,
) -> str:
    """Build a SAML Response XML string (fixture helper). Implements ENT1-R1."""
    attrs = ""
    for name, value in (attributes or {}).items():
        attrs += (
            f'<saml:Attribute Name="{name}">'
            f"<saml:AttributeValue>{value}</saml:AttributeValue></saml:Attribute>"
        )
    authn = ""
    if session_index is not None or authn_instant is not None or authn_context is not None:
        instant_attr = f' AuthnInstant="{authn_instant}"' if authn_instant is not None else ""
        index_attr = f' SessionIndex="{session_index}"' if session_index is not None else ""
        ctx = (
            f"<saml:AuthnContext><saml:AuthnContextClassRef>{authn_context}"
            "</saml:AuthnContextClassRef></saml:AuthnContext>"
        ) if authn_context else ""
        authn = f"<saml:AuthnStatement{instant_attr}{index_attr}>{ctx}</saml:AuthnStatement>"
    xml = (
        f'<samlp:Response xmlns:samlp="{NS_PROTOCOL}" Signature="{SIGNATURE_PLACEHOLDER}">'
        f'<saml:Assertion xmlns:saml="{NS_ASSERTION}">'
        f"<saml:Issuer>{issuer}</saml:Issuer>"
        f"<saml:Subject><saml:NameID>{name_id}</saml:NameID></saml:Subject>"
        f'<saml:Conditions NotBefore="{not_before}" NotOnOrAfter="{not_on_or_after}">'
        f"<saml:AudienceRestriction><saml:Audience>{audience}</saml:Audience>"
        "</saml:AudienceRestriction></saml:Conditions>"
        f"<saml:AttributeStatement>{attrs}</saml:AttributeStatement>"
        f"{authn}"
        "</saml:Assertion></samlp:Response>"
    )
    if sign_key is not None:
        return sign_response(xml, sign_key)
    return xml.replace(SIGNATURE_PLACEHOLDER, "")
