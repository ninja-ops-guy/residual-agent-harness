"""Fail-closed contracts for the Copilot Studio -> RESIDUAL boundary."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from observation_layer.core import freeze

from ...core import ContractError, canonical, digest
from ...iam.saml import Identity


_EXTERNAL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
MAX_OBJECTIVE_CHARS = 8_000
MAX_INPUT_BYTES = 256 * 1024


class CopilotAPIError(ContractError):
    """Public API failure with a stable status/code and non-sensitive message."""

    def __init__(self, status: int, code: str, message: str):
        if type(status) is not int or not 400 <= status <= 599:
            raise ContractError("invalid API error status")
        if not _EXTERNAL_ID.fullmatch(code):
            raise ContractError("invalid API error code")
        if not isinstance(message, str) or not message:
            raise ContractError("API error message is required")
        super().__init__(message)
        self.status = status
        self.code = code
        self.public_message = message

    def to_dict(self, request_id: str | None = None) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.public_message,
            "request_id": request_id,
        }


def external_id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _EXTERNAL_ID.fullmatch(value):
        raise CopilotAPIError(400, "invalid_request", f"{name} is invalid")
    return value


def guid(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{name} must be a GUID")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        raise ContractError(f"{name} must be a GUID") from None
    canonical_value = str(parsed)
    if canonical_value.lower() != value.lower():
        raise ContractError(f"{name} must use canonical GUID form")
    return canonical_value


def _string_tuple(
    value: Any,
    name: str,
    *,
    space_delimited: bool = False,
) -> tuple[str, ...]:
    if value is None:
        return ()
    if space_delimited and isinstance(value, str):
        value = value.split()
    elif isinstance(value, str):
        value = (value,)
    if not isinstance(value, (list, tuple)) or any(
        not isinstance(item, str) or not item.strip() or len(item) > 256
        for item in value
    ):
        raise ContractError(f"{name} claim must contain strings")
    return tuple(sorted(set(item.strip() for item in value)))


@dataclass(frozen=True)
class VerifiedPrincipal:
    """Authorization identity projected only from a validated Entra token."""

    object_id: str
    subject: str
    tenant_id: str
    issuer: str
    authorized_party: str
    scopes: tuple[str, ...]
    groups: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()
    amr: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "object_id", guid(self.object_id, "oid"))
        object.__setattr__(self, "tenant_id", guid(self.tenant_id, "tid"))
        object.__setattr__(
            self, "authorized_party", guid(self.authorized_party, "azp/appid")
        )
        if not isinstance(self.subject, str) or not self.subject.strip():
            raise ContractError("verified identity requires a token subject")
        if not isinstance(self.issuer, str) or not self.issuer.strip():
            raise ContractError("verified identity requires an issuer")
        for name in ("scopes", "groups", "roles", "amr"):
            value = getattr(self, name)
            if not isinstance(value, tuple) or any(
                not isinstance(item, str) or not item
                for item in value
            ):
                raise ContractError(f"verified {name} must be a tuple of strings")
            if len(set(value)) != len(value):
                raise ContractError(f"verified {name} must be unique")

    @classmethod
    def from_identity(cls, identity: Identity) -> "VerifiedPrincipal":
        if not isinstance(identity, Identity):
            raise ContractError("authenticator must return an Identity")
        attrs = identity.attributes
        tenant = attrs.get("tid")
        object_id = attrs.get("oid")
        authorized_party = attrs.get("azp") or attrs.get("appid")
        if tenant is None or object_id is None or authorized_party is None:
            raise ContractError(
                "verified Entra token requires tid, oid, and azp/appid claims"
            )
        scopes = _string_tuple(attrs.get("scp"), "scp", space_delimited=True)
        groups = _string_tuple(attrs.get("groups"), "groups")
        roles = _string_tuple(attrs.get("roles"), "roles")
        amr = _string_tuple(identity.amr, "amr")
        return cls(
            object_id=object_id,
            subject=identity.subject,
            tenant_id=tenant,
            issuer=identity.issuer,
            authorized_party=authorized_party,
            scopes=scopes,
            groups=groups,
            roles=roles,
            amr=amr,
        )

    @property
    def principal_id(self) -> str:
        """Stable authorization key within tenant; do not use display names."""
        return self.object_id

    @property
    def claims_hash(self) -> str:
        return digest({
            "object_id": self.object_id,
            "subject": self.subject,
            "tenant_id": self.tenant_id,
            "issuer": self.issuer,
            "authorized_party": self.authorized_party,
            "scopes": list(self.scopes),
            "groups": list(self.groups),
            "roles": list(self.roles),
            "amr": list(self.amr),
        })


@dataclass(frozen=True)
class MissionRequest:
    """Strict request: identity and authority fields are never caller supplied."""

    request_id: str
    template_id: str
    objective: str
    inputs: dict[str, Any]

    def __post_init__(self):
        external_id(self.request_id, "request_id")
        external_id(self.template_id, "template_id")
        if not isinstance(self.objective, str) or not self.objective.strip():
            raise CopilotAPIError(400, "invalid_request", "objective is required")
        objective = self.objective.strip()
        if len(objective) > MAX_OBJECTIVE_CHARS:
            raise CopilotAPIError(
                413, "request_too_large", "objective exceeds the supported size"
            )
        if not isinstance(self.inputs, dict):
            raise CopilotAPIError(
                400, "invalid_request", "inputs must be an object"
            )
        try:
            immutable = freeze(self.inputs)
            payload_bytes = len(canonical(immutable).encode("utf-8"))
        except (TypeError, ValueError):
            raise CopilotAPIError(
                400,
                "invalid_request",
                "inputs must contain finite JSON values",
            ) from None
        if payload_bytes > MAX_INPUT_BYTES:
            raise CopilotAPIError(
                413, "request_too_large", "inputs exceed the supported size"
            )
        object.__setattr__(self, "objective", objective)
        object.__setattr__(self, "inputs", immutable)

    @classmethod
    def from_dict(cls, value: Any) -> "MissionRequest":
        if not isinstance(value, dict):
            raise CopilotAPIError(
                400, "invalid_request", "request body must be an object"
            )
        allowed = {"request_id", "template_id", "objective", "inputs"}
        if set(value) != allowed:
            raise CopilotAPIError(
                400,
                "invalid_request",
                "request body has unsupported or missing fields",
            )
        return cls(
            request_id=value["request_id"],
            template_id=value["template_id"],
            objective=value["objective"],
            inputs=value["inputs"],
        )

    def payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "template_id": self.template_id,
            "objective": self.objective,
            "inputs": self.inputs,
        }

    @property
    def payload_hash(self) -> str:
        return digest(self.payload())
