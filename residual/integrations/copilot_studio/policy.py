"""Manifest-shaped Firmware Engineering policy for Copilot Studio."""
from __future__ import annotations

from dataclasses import dataclass

from ...core import ContractError, digest
from .contracts import CopilotAPIError, MissionRequest, VerifiedPrincipal


RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@dataclass(frozen=True)
class MissionTemplate:
    template_id: str
    capabilities: frozenset[str]
    risk: str
    approval_required: bool = False

    def __post_init__(self):
        if self.risk not in RISK_ORDER:
            raise ContractError("unknown mission risk")
        if not isinstance(self.capabilities, frozenset) or not self.capabilities:
            raise ContractError("mission template requires immutable capabilities")


@dataclass(frozen=True)
class PolicyDecision:
    profile_id: str
    template_id: str
    capabilities: tuple[str, ...]
    risk: str
    approval_required: bool
    policy_hash: str


class FirmwarePolicy:
    """Fail-closed department policy.

    Group identifiers are opaque configuration values.  Production deployments
    should replace the example display name with stable Entra group object IDs
    or app-role values exported by their managed solution.
    """

    profile_id = "firmware-engineering"
    risk_ceiling = "medium"
    allowed_capabilities = frozenset({
        "repository.analyze",
        "sandbox.build",
        "tests.run_approved",
        "patch.propose",
        "evidence.read_own",
        "draft_pr.propose",
    })
    denied_capabilities = frozenset({
        "pr.merge",
        "production.write",
        "policy.modify",
        "qualification.bypass",
        "verifier.bypass",
        "secrets.read",
        "shell.host",
        "network.arbitrary",
    })
    templates = {
        "firmware-repository-analysis": MissionTemplate(
            "firmware-repository-analysis",
            frozenset({"repository.analyze", "evidence.read_own"}),
            "low",
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
        ),
        "firmware-test-triage": MissionTemplate(
            "firmware-test-triage",
            frozenset({"repository.analyze", "tests.run_approved", "evidence.read_own"}),
            "low",
        ),
    }

    def __init__(self, allowed_groups: tuple[str, ...] = ("Engineering-Firmware",)):
        if not isinstance(allowed_groups, tuple) or not allowed_groups or any(
            not isinstance(group, str) or not group.strip() for group in allowed_groups
        ):
            raise ContractError("firmware policy requires at least one allowed Entra group")
        self.allowed_groups = frozenset(allowed_groups)
        if self.allowed_capabilities & self.denied_capabilities:
            raise ContractError("firmware policy allow/deny sets overlap")
        for template in self.templates.values():
            if not template.capabilities <= self.allowed_capabilities:
                raise ContractError("template requests capability outside profile allowlist")
            if template.capabilities & self.denied_capabilities:
                raise ContractError("template requests denied capability")
            if RISK_ORDER[template.risk] > RISK_ORDER[self.risk_ceiling]:
                raise ContractError("template exceeds profile risk ceiling")

    @property
    def policy_hash(self) -> str:
        return digest({
            "profile_id": self.profile_id,
            "allowed_groups": sorted(self.allowed_groups),
            "risk_ceiling": self.risk_ceiling,
            "allow": sorted(self.allowed_capabilities),
            "deny": sorted(self.denied_capabilities),
            "templates": {
                name: {
                    "capabilities": sorted(template.capabilities),
                    "risk": template.risk,
                    "approval_required": template.approval_required,
                }
                for name, template in sorted(self.templates.items())
            },
        })

    def authorize(self, principal: VerifiedPrincipal, request: MissionRequest) -> PolicyDecision:
        if not self.allowed_groups.intersection(principal.groups):
            raise CopilotAPIError(403, "department_denied", "the signed-in identity is not authorized for this department")
        template = self.templates.get(request.template_id)
        if template is None:
            raise CopilotAPIError(403, "template_denied", "the requested mission template is not authorized")
        # Re-check invariants at authorization time rather than relying solely on
        # constructor validation; a deployment cannot widen authority by mutating
        # caller input because capabilities never come from the request.
        if (
            not template.capabilities <= self.allowed_capabilities
            or template.capabilities & self.denied_capabilities
            or RISK_ORDER[template.risk] > RISK_ORDER[self.risk_ceiling]
        ):
            raise CopilotAPIError(403, "policy_denied", "the requested mission exceeds the department policy")
        return PolicyDecision(
            profile_id=self.profile_id,
            template_id=template.template_id,
            capabilities=tuple(sorted(template.capabilities)),
            risk=template.risk,
            approval_required=template.approval_required,
            policy_hash=self.policy_hash,
        )
