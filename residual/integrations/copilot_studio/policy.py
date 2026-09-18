"""Immutable Firmware Engineering authorization policy for Copilot Studio."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import ClassVar, Mapping

from ...core import ContractError, digest
from .contracts import (
    CopilotAPIError,
    MissionRequest,
    VerifiedPrincipal,
    external_id,
    guid,
)


RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@dataclass(frozen=True)
class MissionTemplate:
    template_id: str
    capabilities: frozenset[str]
    risk: str
    required_inputs: frozenset[str]

    def __post_init__(self):
        external_id(self.template_id, "template_id")
        if self.risk not in RISK_ORDER:
            raise ContractError("unknown mission risk")
        if not self.capabilities or not isinstance(self.capabilities, frozenset):
            raise ContractError("template requires immutable capabilities")
        if not isinstance(self.required_inputs, frozenset):
            raise ContractError("template input contract must be immutable")


TEMPLATES: Mapping[str, MissionTemplate] = MappingProxyType({
    "firmware-repository-analysis": MissionTemplate(
        "firmware-repository-analysis",
        frozenset({"repository.analyze", "evidence.read_own"}),
        "low",
        frozenset({"repository_id", "analysis_profile_id"}),
    ),
    "firmware-sandbox-build": MissionTemplate(
        "firmware-sandbox-build",
        frozenset({
            "repository.analyze",
            "sandbox.build",
            "tests.run_approved",
            "patch.propose",
            "evidence.read_own",
        }),
        "medium",
        frozenset({"repository_id", "build_target_id", "test_suite_id"}),
    ),
    "firmware-test-triage": MissionTemplate(
        "firmware-test-triage",
        frozenset({
            "repository.analyze",
            "tests.run_approved",
            "evidence.read_own",
        }),
        "low",
        frozenset({"repository_id", "test_run_id", "triage_profile_id"}),
    ),
})


@dataclass(frozen=True)
class PolicyDecision:
    profile_id: str
    template_id: str
    capabilities: tuple[str, ...]
    risk: str
    approval_required: bool
    policy_hash: str


@dataclass(frozen=True, init=False)
class FirmwarePolicy:
    """Server-side authority; all configuration is immutable after construction."""

    allowed_tenants: frozenset[str]
    allowed_groups: frozenset[str]
    allowed_roles: frozenset[str]
    required_scopes: frozenset[str]
    allowed_clients: frozenset[str]
    max_active_missions: int

    profile_id: ClassVar[str] = "firmware-engineering"
    risk_ceiling: ClassVar[str] = "medium"
    templates: ClassVar[Mapping[str, MissionTemplate]] = TEMPLATES
    allowed_capabilities: ClassVar[frozenset[str]] = frozenset({
        "repository.analyze",
        "sandbox.build",
        "tests.run_approved",
        "patch.propose",
        "evidence.read_own",
        "draft_pr.propose",
    })
    denied_capabilities: ClassVar[frozenset[str]] = frozenset({
        "pr.merge",
        "production.write",
        "policy.modify",
        "qualification.bypass",
        "verifier.bypass",
        "secrets.read",
        "shell.host",
        "network.arbitrary",
    })

    def __init__(
        self,
        *,
        allowed_tenants: tuple[str, ...],
        allowed_groups: tuple[str, ...] = (),
        allowed_roles: tuple[str, ...] = (),
        required_scopes: tuple[str, ...] = ("access_as_user",),
        allowed_clients: tuple[str, ...],
        max_active_missions: int = 4,
    ):
        tenants = frozenset(guid(value, "allowed tenant") for value in allowed_tenants)
        groups = frozenset(guid(value, "allowed group") for value in allowed_groups)
        roles = frozenset(allowed_roles)
        scopes = frozenset(required_scopes)
        clients = frozenset(guid(value, "allowed client") for value in allowed_clients)
        if not tenants or not clients:
            raise ContractError("tenant and client allowlists must be nonempty")
        if not groups and not roles:
            raise ContractError("at least one department group or app role is required")
        if not scopes or any(not isinstance(value, str) or not value for value in scopes):
            raise ContractError("at least one delegated scope is required")
        if any(not isinstance(value, str) or not value for value in roles):
            raise ContractError("allowed roles must be nonempty strings")
        if type(max_active_missions) is not int or not 1 <= max_active_missions <= 64:
            raise ContractError("max_active_missions must be between 1 and 64")
        object.__setattr__(self, "allowed_tenants", tenants)
        object.__setattr__(self, "allowed_groups", groups)
        object.__setattr__(self, "allowed_roles", roles)
        object.__setattr__(self, "required_scopes", scopes)
        object.__setattr__(self, "allowed_clients", clients)
        object.__setattr__(self, "max_active_missions", max_active_missions)
        self._validate_static_policy()

    def _validate_static_policy(self) -> None:
        if self.allowed_capabilities & self.denied_capabilities:
            raise ContractError("firmware policy allow/deny sets overlap")
        for template in self.templates.values():
            if not template.capabilities <= self.allowed_capabilities:
                raise ContractError("template capability outside profile allowlist")
            if template.capabilities & self.denied_capabilities:
                raise ContractError("template requests denied capability")
            if RISK_ORDER[template.risk] > RISK_ORDER[self.risk_ceiling]:
                raise ContractError("template exceeds profile risk ceiling")

    @property
    def policy_hash(self) -> str:
        return digest({
            "profile_id": self.profile_id,
            "allowed_tenants": sorted(self.allowed_tenants),
            "allowed_groups": sorted(self.allowed_groups),
            "allowed_roles": sorted(self.allowed_roles),
            "required_scopes": sorted(self.required_scopes),
            "allowed_clients": sorted(self.allowed_clients),
            "max_active_missions": self.max_active_missions,
            "risk_ceiling": self.risk_ceiling,
            "allow": sorted(self.allowed_capabilities),
            "deny": sorted(self.denied_capabilities),
            "templates": {
                name: {
                    "capabilities": sorted(template.capabilities),
                    "risk": template.risk,
                    "required_inputs": sorted(template.required_inputs),
                }
                for name, template in sorted(self.templates.items())
            },
        })

    def authorize_principal(self, principal: VerifiedPrincipal) -> None:
        if principal.tenant_id not in self.allowed_tenants:
            raise CopilotAPIError(
                403, "tenant_denied", "the signed-in tenant is not authorized"
            )
        if principal.authorized_party not in self.allowed_clients:
            raise CopilotAPIError(
                403, "client_denied", "the calling client is not authorized"
            )
        if not self.required_scopes <= set(principal.scopes):
            raise CopilotAPIError(
                403, "scope_denied", "the delegated token lacks required scope"
            )
        group_match = bool(self.allowed_groups.intersection(principal.groups))
        role_match = bool(self.allowed_roles.intersection(principal.roles))
        if not group_match and not role_match:
            raise CopilotAPIError(
                403,
                "department_denied",
                "the signed-in identity is not authorized for this department",
            )

    @staticmethod
    def _validate_input_ids(request: MissionRequest, template: MissionTemplate) -> None:
        keys = frozenset(request.inputs)
        if keys != template.required_inputs:
            raise CopilotAPIError(
                400,
                "invalid_template_inputs",
                "inputs do not match the approved mission template",
            )
        for key, value in request.inputs.items():
            external_id(value, key)

    def authorize(
        self, principal: VerifiedPrincipal, request: MissionRequest
    ) -> PolicyDecision:
        self.authorize_principal(principal)
        template = self.templates.get(request.template_id)
        if template is None:
            raise CopilotAPIError(
                403, "template_denied", "the requested mission template is not authorized"
            )
        self._validate_input_ids(request, template)
        if (
            not template.capabilities <= self.allowed_capabilities
            or template.capabilities & self.denied_capabilities
            or RISK_ORDER[template.risk] > RISK_ORDER[self.risk_ceiling]
        ):
            raise CopilotAPIError(
                403, "policy_denied", "the requested mission exceeds department policy"
            )
        return PolicyDecision(
            profile_id=self.profile_id,
            template_id=template.template_id,
            capabilities=tuple(sorted(template.capabilities)),
            risk=template.risk,
            approval_required=False,
            policy_hash=self.policy_hash,
        )
