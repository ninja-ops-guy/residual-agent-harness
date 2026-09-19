"""Department profiles and server-selected mission templates."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...core import ContractError, identifier
from .auth import CopilotPrincipal

_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _strings(value: Any, name: str, *, nonempty: bool = False) -> frozenset[str]:
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ContractError(f"{name} must be an array")
    out = frozenset(item.strip() for item in value
                    if isinstance(item, str) and item.strip())
    if len(out) != len(value):
        raise ContractError(f"{name} must contain unique non-empty strings")
    if nonempty and not out:
        raise ContractError(f"{name} must not be empty")
    return out


@dataclass(frozen=True)
class MissionTemplate:
    template_id: str
    risk: str
    capabilities: frozenset[str]
    acceptance: tuple[str, ...]
    required_inputs: frozenset[str] = frozenset()
    optional_inputs: frozenset[str] = frozenset()

    def __post_init__(self):
        identifier(self.template_id)
        if self.risk not in _RISK_ORDER:
            raise ContractError("unknown mission risk")
        if not isinstance(self.capabilities, frozenset) or not self.capabilities:
            raise ContractError("mission template capabilities must be a non-empty frozenset")
        if not isinstance(self.acceptance, tuple) or not self.acceptance:
            raise ContractError("mission template acceptance must be a non-empty tuple")
        if any(not isinstance(x, str) or not x.strip() for x in self.acceptance):
            raise ContractError("mission acceptance entries must be non-empty strings")
        for name, values in (
            ("required_inputs", self.required_inputs),
            ("optional_inputs", self.optional_inputs),
        ):
            if not isinstance(values, frozenset):
                raise ContractError(f"{name} must be a frozenset")
            for value in values:
                identifier(value)
        if self.required_inputs & self.optional_inputs:
            raise ContractError("mission input field cannot be both required and optional")

    def validate_inputs(self, inputs: dict[str, Any]) -> dict[str, str]:
        """Validate opaque deployment aliases, never paths or URLs.

        v1 intentionally accepts only identifier-shaped strings. A production
        host resolves these aliases (for example repository_id) through its own
        trusted configuration; caller data never becomes a filesystem path or
        network destination directly.
        """
        if not isinstance(inputs, dict):
            raise ContractError("mission inputs must be an object")
        allowed = self.required_inputs | self.optional_inputs
        keys = set(inputs)
        missing = self.required_inputs - keys
        unknown = keys - allowed
        if missing:
            raise ContractError("missing required mission input: " + sorted(missing)[0])
        if unknown:
            raise ContractError("unknown mission input: " + sorted(unknown)[0])
        normalized: dict[str, str] = {}
        for key, value in inputs.items():
            if not isinstance(value, str):
                raise ContractError(f"{key} must be an opaque identifier")
            normalized[key] = identifier(value.strip())
        return normalized


@dataclass(frozen=True)
class DepartmentProfile:
    profile_id: str
    allowed_groups: frozenset[str]
    approved_templates: frozenset[str]
    allow_capabilities: frozenset[str]
    deny_capabilities: frozenset[str]
    risk_ceiling: str = "medium"

    def __post_init__(self):
        identifier(self.profile_id)
        if not self.allowed_groups:
            raise ContractError("department profile requires at least one Entra group")
        if not self.approved_templates:
            raise ContractError("department profile requires approved templates")
        if self.risk_ceiling not in _RISK_ORDER:
            raise ContractError("unknown department risk ceiling")
        overlap = self.allow_capabilities & self.deny_capabilities
        if overlap:
            raise ContractError(
                "department capability allow/deny conflict: " + sorted(overlap)[0]
            )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DepartmentProfile":
        if not isinstance(data, dict):
            raise ContractError("department profile must be an object")
        allowed = {
            "profile_id", "allowed_groups", "approved_templates",
            "allow_capabilities", "deny_capabilities", "risk_ceiling",
        }
        if set(data) - allowed:
            raise ContractError("unknown department profile keys")
        return cls(
            profile_id=data["profile_id"],
            allowed_groups=_strings(data["allowed_groups"], "allowed_groups", nonempty=True),
            approved_templates=_strings(
                data["approved_templates"], "approved_templates", nonempty=True
            ),
            allow_capabilities=_strings(
                data["allow_capabilities"], "allow_capabilities", nonempty=True
            ),
            deny_capabilities=_strings(data.get("deny_capabilities", []), "deny_capabilities"),
            risk_ceiling=data.get("risk_ceiling", "medium"),
        )

    def require_membership(self, principal: CopilotPrincipal) -> None:
        if not isinstance(principal, CopilotPrincipal):
            raise ContractError("principal must be verified")
        if not (principal.groups & self.allowed_groups):
            raise ContractError("caller is not authorized for this department profile")

    def authorize(self, principal: CopilotPrincipal, template: MissionTemplate) -> None:
        self.require_membership(principal)
        if template.template_id not in self.approved_templates:
            raise ContractError("mission template is not approved for this department")
        if _RISK_ORDER[template.risk] > _RISK_ORDER[self.risk_ceiling]:
            raise ContractError("mission template exceeds department risk ceiling")
        forbidden = template.capabilities & self.deny_capabilities
        if forbidden:
            raise ContractError("mission template contains an explicitly denied capability")
        unknown = template.capabilities - self.allow_capabilities
        if unknown:
            raise ContractError("mission template requests an unapproved capability")


def firmware_templates() -> dict[str, MissionTemplate]:
    """Server-owned v1 template registry. Prompts cannot add capabilities."""
    return {
        "firmware-repository-analysis": MissionTemplate(
            "firmware-repository-analysis",
            "low",
            frozenset({"repository.analyze", "evidence.read_own"}),
            (
                "Produce an evidence-backed analysis.",
                "Do not modify repository, production, policy, or qualification state.",
            ),
            required_inputs=frozenset({"repository_id"}),
        ),
        "firmware-sandbox-build": MissionTemplate(
            "firmware-sandbox-build",
            "medium",
            frozenset({
                "repository.analyze", "sandbox.build",
                "tests.run_approved", "evidence.read_own",
            }),
            (
                "Run only approved build/test operations inside the configured sandbox.",
                "Return evidence for each claimed result.",
                "Do not perform an external write or production action.",
            ),
            required_inputs=frozenset({"repository_id"}),
            optional_inputs=frozenset({"build_profile_id"}),
        ),
        "firmware-test-triage": MissionTemplate(
            "firmware-test-triage",
            "medium",
            frozenset({
                "repository.analyze", "tests.run_approved",
                "patch.propose", "draft_pr.propose", "evidence.read_own",
            }),
            (
                "Identify the failure using approved evidence and tests.",
                "Any code change is a proposal only; do not merge or deploy it.",
                "Return evidence supporting the proposed remediation.",
            ),
            required_inputs=frozenset({"repository_id"}),
            optional_inputs=frozenset({"test_profile_id"}),
        ),
    }


def firmware_profile(*, allowed_groups: frozenset[str] | None = None) -> DepartmentProfile:
    """Build the Firmware profile with deployment-specific Entra group object IDs.

    The friendly-name default is for local fixtures only. Production deployments
    should pass the immutable set of Entra group object IDs configured for the
    Power Platform environment.
    """
    groups = allowed_groups or frozenset({"Engineering-Firmware"})
    return DepartmentProfile(
        profile_id="firmware-engineering",
        allowed_groups=groups,
        approved_templates=frozenset(firmware_templates()),
        allow_capabilities=frozenset({
            "repository.analyze",
            "sandbox.build",
            "tests.run_approved",
            "patch.propose",
            "draft_pr.propose",
            "evidence.read_own",
        }),
        deny_capabilities=frozenset({
            "pr.merge",
            "production.write",
            "policy.modify",
            "qualification.bypass",
            "verifier.bypass",
            "secrets.read",
            "shell.host",
            "network.arbitrary",
        }),
        risk_ceiling="medium",
    )
