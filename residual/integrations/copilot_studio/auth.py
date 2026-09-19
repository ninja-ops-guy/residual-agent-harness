"""Fail-closed Microsoft Entra identity adapter for Copilot Studio OBO calls."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from ...core import ContractError, digest, strict_json
from ...iam.crypto import b64url_decode
from ...iam.oidc import OIDCClient

DEFAULT_DELEGATED_SCOPE = "access_as_user"


def _string_set(value: Any, name: str) -> frozenset[str]:
    if value is None:
        return frozenset()
    if isinstance(value, str):
        parts = value.split()
    elif isinstance(value, (list, tuple, set, frozenset)):
        parts = list(value)
    else:
        raise ContractError(f"{name} claim must be a string or string array")
    if any(not isinstance(item, str) or not item.strip() for item in parts):
        raise ContractError(f"{name} claim contains a non-string value")
    return frozenset(item.strip() for item in parts if item.strip())


@dataclass(frozen=True)
class CopilotPrincipal:
    """Verified caller identity. No request-body value can construct this object."""

    tenant_id: str
    subject_id: str
    object_id: str
    issuer: str
    scopes: frozenset[str]
    groups: frozenset[str]
    roles: frozenset[str]

    def __post_init__(self):
        for name in ("tenant_id", "subject_id", "object_id", "issuer"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ContractError(f"{name} is required")
        for name in ("scopes", "groups", "roles"):
            if not isinstance(getattr(self, name), frozenset):
                raise ContractError(f"{name} must be a frozenset")

    @property
    def binding_subject(self) -> str:
        return f"{self.tenant_id}:{self.object_id}"

    @property
    def identity_hash(self) -> str:
        return digest({
            "tenant_id": self.tenant_id,
            "subject_id": self.subject_id,
            "object_id": self.object_id,
            "issuer": self.issuer,
        })


GroupResolver = Callable[[str, str], Iterable[str]]


class CopilotIdentityVerifier:
    """Validate an Entra delegated token through the existing OIDC verifier.

    The wrapped OIDCClient verifies JWT signature, issuer, audience, and time
    claims. This adapter additionally pins Entra signing to RS256, enforces the
    delegated scope, and extracts only verified claims for authorization.
    """

    def __init__(
        self,
        oidc_client: OIDCClient,
        *,
        expected_tenant: str | None = None,
        required_scope: str = DEFAULT_DELEGATED_SCOPE,
        group_resolver: GroupResolver | None = None,
        allowed_client_apps: frozenset[str] = frozenset(),
    ):
        if not isinstance(oidc_client, OIDCClient):
            raise ContractError("oidc_client must be an OIDCClient")
        if expected_tenant is not None and (
            not isinstance(expected_tenant, str) or not expected_tenant.strip()
        ):
            raise ContractError("expected_tenant must be a non-empty string")
        if not isinstance(required_scope, str) or not required_scope.strip():
            raise ContractError("required_scope must be non-empty")
        if group_resolver is not None and not callable(group_resolver):
            raise ContractError("group_resolver must be callable")
        if not isinstance(allowed_client_apps, frozenset) or any(
            not isinstance(app, str) or not app.strip() for app in allowed_client_apps
        ):
            raise ContractError("allowed_client_apps must be a frozenset of app ids")
        self._client = oidc_client
        self._tenant = expected_tenant.strip() if expected_tenant else None
        self._required_scope = required_scope.strip()
        self._group_resolver = group_resolver
        self._allowed_client_apps = allowed_client_apps

    @staticmethod
    def _require_entra_algorithm(token: str) -> None:
        if not isinstance(token, str):
            raise ContractError("delegated token must be a string")
        parts = token.split(".")
        if len(parts) != 3:
            raise ContractError("delegated token must have three segments")
        try:
            header = strict_json(b64url_decode(parts[0]).decode("utf-8"))
        except (ContractError, UnicodeDecodeError) as exc:
            raise ContractError("malformed delegated token header") from exc
        if not isinstance(header, dict) or header.get("alg") != "RS256":
            raise ContractError("delegated token signing algorithm not allowed")

    def verify(self, token: str, *, now: int) -> CopilotPrincipal:
        self._require_entra_algorithm(token)
        identity = self._client.authenticate(token, now=now)
        attrs = dict(identity.attributes)

        tenant_id = attrs.get("tid")
        object_id = attrs.get("oid")
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise ContractError("delegated token requires tid claim")
        if not isinstance(object_id, str) or not object_id.strip():
            raise ContractError("delegated token requires oid claim")
        tenant_id, object_id = tenant_id.strip(), object_id.strip()
        if self._tenant is not None and tenant_id != self._tenant:
            raise ContractError("delegated token tenant mismatch")

        if self._allowed_client_apps:
            client_app = attrs.get("azp") or attrs.get("appid")
            if not isinstance(client_app, str) or client_app not in self._allowed_client_apps:
                raise ContractError("delegated token client application is not allowed")

        scopes = _string_set(attrs.get("scp"), "scp")
        if self._required_scope not in scopes:
            raise ContractError("delegated token missing required scope")

        groups = _string_set(attrs.get("groups"), "groups")
        claim_names = attrs.get("_claim_names")
        group_overage = (
            isinstance(claim_names, dict)
            and isinstance(claim_names.get("groups"), str)
        )
        if group_overage:
            if self._group_resolver is None:
                raise ContractError("group overage requires a configured resolver")
            try:
                groups = _string_set(tuple(self._group_resolver(tenant_id, object_id)), "resolved groups")
            except ContractError:
                raise
            except Exception as exc:
                raise ContractError("group resolution failed") from exc

        return CopilotPrincipal(
            tenant_id=tenant_id,
            subject_id=identity.subject.strip(),
            object_id=object_id,
            issuer=identity.issuer,
            scopes=scopes,
            groups=groups,
            roles=_string_set(attrs.get("roles"), "roles"),
        )
