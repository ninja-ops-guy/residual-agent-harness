"""Fail-closed contracts for the Copilot Studio -> RESIDUAL boundary."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from observation_layer.core import freeze

from ...core import ContractError, canonical, digest
from ...iam.events import subject_identifier
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
        return {"code": self.code, "message": self.public_message, "request_id": request_id}


def external_id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _EXTERNAL_ID.fullmatch(value):
        raise CopilotAPIError(400, "invalid_request", f"{name} is invalid")
    return value


@dataclass(frozen=True)
class VerifiedPrincipal:
    """Authorization identity derived only from a successfully validated token."""

    subject: str
    tenant_id: str
    issuer: str
    groups: tuple[str, ...] = ()
    amr: tuple[str, ...] = ()

    def __post_init__(self):
        subject_identifier(self.subject)
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip() or len(self.tenant_id) > 128:
            raise ContractError("verified identity requires a tenant id")
        if not isinstance(self.issuer, str) or not self.issuer.strip() or len(self.issuer) > 512:
            raise ContractError("verified identity requires an issuer")
        if not isinstance(self.groups, tuple) or any(
            not isinstance(group, str) or not group.strip() or len(group) > 256 for group in self.groups
        ):
            raise ContractError("verified groups must be nonempty strings")
        if len(set(self.groups)) != len(self.groups):
            raise ContractError("verified groups must be unique")
        if not isinstance(self.amr, tuple) or any(not isinstance(method, str) for method in self.amr):
            raise ContractError("verified authentication methods must be strings")

    @classmethod
    def from_identity(cls, identity: Identity) -> "VerifiedPrincipal":
        if not isinstance(identity, Identity):
            raise ContractError("authenticator must return an Identity")
        attrs = identity.attributes
        tenant = attrs.get("tid") or attrs.get("tenant_id")
        if not isinstance(tenant, str) or not tenant.strip():
            raise ContractError("verified Entra token requires a tenant id claim")
        raw_groups = attrs.get("groups", ())
        if isinstance(raw_groups, str):
            raw_groups = (raw_groups,)
        if not isinstance(raw_groups, (list, tuple)):
            raise ContractError("verified groups claim must be an array of strings")
        groups = tuple(sorted(set(raw_groups)))
        return cls(
            subject=identity.subject,
            tenant_id=tenant,
            issuer=identity.issuer,
            groups=groups,
            amr=tuple(identity.amr),
        )

    @property
    def claims_hash(self) -> str:
        """Non-secret identity binding suitable for receipts/audit references."""
        return digest({
            "subject": self.subject,
            "tenant_id": self.tenant_id,
            "issuer": self.issuer,
            "groups": list(self.groups),
            "amr": list(self.amr),
        })


@dataclass(frozen=True)
class MissionRequest:
    """Strict custom-connector request. Identity/authority fields are forbidden."""

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
            raise CopilotAPIError(413, "request_too_large", "objective exceeds the supported size")
        if not isinstance(self.inputs, dict):
            raise CopilotAPIError(400, "invalid_request", "inputs must be an object")
        try:
            immutable = freeze(self.inputs)
            payload_bytes = len(canonical(immutable).encode("utf-8"))
        except (TypeError, ValueError):
            raise CopilotAPIError(400, "invalid_request", "inputs must contain finite JSON values") from None
        if payload_bytes > MAX_INPUT_BYTES:
            raise CopilotAPIError(413, "request_too_large", "inputs exceed the supported size")
        object.__setattr__(self, "objective", objective)
        object.__setattr__(self, "inputs", immutable)

    @classmethod
    def from_dict(cls, value: Any) -> "MissionRequest":
        if not isinstance(value, dict):
            raise CopilotAPIError(400, "invalid_request", "request body must be an object")
        allowed = {"request_id", "template_id", "objective", "inputs"}
        if set(value) != allowed:
            # This rejects caller-supplied subject, tenant, roles, groups, capabilities,
            # approval flags, or any other authority-bearing field.
            raise CopilotAPIError(400, "invalid_request", "request body has unsupported or missing fields")
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
