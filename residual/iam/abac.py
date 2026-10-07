"""Attribute-Based Access Control (ABAC) for Enterprise IAM.

Implements ENT1-R3: permission decisions are evaluable against user
attributes — department, region, clearance level, employment status,
and custom attributes asserted by the IdP (SAML attribute statements
or OIDC claims, see residual.iam.saml / residual.iam.oidc).

Evaluation uses deny-overrides combining: any matching deny policy
rejects the request; otherwise at least one matching allow policy is
required.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core import ContractError, canonical, identifier
from .rbac import PERMISSION_CATEGORIES, WILDCARD

#: Well-known IdP attributes implementing ENT1-R3.
ATTR_DEPARTMENT = "department"
ATTR_REGION = "region"
ATTR_CLEARANCE_LEVEL = "clearance_level"
ATTR_EMPLOYMENT_STATUS = "employment_status"

KNOWN_ATTRIBUTES = frozenset({
    ATTR_DEPARTMENT,
    ATTR_REGION,
    ATTR_CLEARANCE_LEVEL,
    ATTR_EMPLOYMENT_STATUS,
})

OPERATORS = ("eq", "neq", "in", "gte", "lte", "contains")

ALLOW = "allow"
DENY = "deny"


@dataclass(frozen=True)
class UserAttributes:
    """Attributes asserted by the IdP for a user. Implements ENT1-R3."""

    department: str | None = None
    region: str | None = None
    clearance_level: int | None = None
    employment_status: str | None = None
    custom: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.clearance_level is not None and (
                type(self.clearance_level) is not int or self.clearance_level < 0):
            raise ContractError("clearance_level must be a nonnegative integer")
        if not isinstance(self.custom, dict):
            raise ContractError("custom attributes must be a dict")
        canonical(self.custom)

    @classmethod
    def from_idp(cls, attributes: dict) -> "UserAttributes":
        """Build from raw IdP attributes (SAML/OIDC). Implements ENT1-R3."""
        if not isinstance(attributes, dict):
            raise ContractError("idp attributes must be a dict")
        known = {}
        custom = {}
        for key, value in attributes.items():
            if key in KNOWN_ATTRIBUTES:
                known[key] = value
            else:
                custom[key] = value
        if "clearance_level" in known:
            try:
                known["clearance_level"] = int(known["clearance_level"])
            except (TypeError, ValueError) as exc:
                raise ContractError("clearance_level must be an integer") from exc
        return cls(**known, custom=custom)

    def get(self, attribute: str) -> Any:
        if attribute in KNOWN_ATTRIBUTES:
            return getattr(self, attribute)
        return self.custom.get(attribute)


@dataclass(frozen=True)
class Condition:
    """A single attribute condition. Implements ENT1-R3."""

    attribute: str
    operator: str
    value: Any

    def __post_init__(self):
        if not isinstance(self.attribute, str) or not self.attribute.strip():
            raise ContractError("condition attribute is required")
        if self.operator not in OPERATORS:
            raise ContractError(f"unknown condition operator {self.operator!r}")
        canonical(self.value)

    def matches(self, attributes: UserAttributes) -> bool:
        actual = attributes.get(self.attribute)
        if actual is None:
            return False
        if self.operator == "eq":
            return actual == self.value
        if self.operator == "neq":
            return actual != self.value
        if self.operator == "in":
            return isinstance(self.value, (list, tuple)) and actual in self.value
        if self.operator == "contains":
            return isinstance(actual, (list, tuple, str)) and self.value in actual
        if self.operator in ("gte", "lte"):
            if type(actual) not in (int, float) or type(self.value) not in (int, float):
                return False
            return actual >= self.value if self.operator == "gte" else actual <= self.value
        return False  # pragma: no cover - OPERATORS is exhaustive


@dataclass(frozen=True)
class ABACPolicy:
    """An allow/deny policy over IdP attributes. Implements ENT1-R3.

    ``category``/``scope`` bind the policy to a permission (same
    categories as RBAC, ENT1-R2); all conditions must match for the
    policy to apply.
    """

    name: str
    effect: str
    category: str
    conditions: tuple[Condition, ...] = ()
    scope: str = WILDCARD

    def __post_init__(self):
        identifier(self.name)
        if self.effect not in (ALLOW, DENY):
            raise ContractError("policy effect must be 'allow' or 'deny'")
        if self.category not in PERMISSION_CATEGORIES:
            raise ContractError(f"unknown permission category {self.category!r}")
        if not isinstance(self.conditions, tuple) or any(
                not isinstance(c, Condition) for c in self.conditions):
            raise ContractError("policy conditions must be a tuple of Condition")
        if not isinstance(self.scope, str) or not self.scope.strip():
            raise ContractError("policy scope must be a non-empty string")

    def applies(self, attributes: UserAttributes, category: str, scope: str) -> bool:
        if self.category != category:
            return False
        if self.scope != WILDCARD and self.scope != scope:
            return False
        return all(c.matches(attributes) for c in self.conditions)


@dataclass(frozen=True)
class ABACDecision:
    """Result of an ABAC evaluation. Implements ENT1-R3."""

    allowed: bool
    matched_allow: tuple[str, ...] = ()
    matched_deny: tuple[str, ...] = ()

    def __post_init__(self):
        if type(self.allowed) is not bool:
            raise ContractError("decision allowed must be a bool")


class ABACEvaluator:
    """Evaluates ABAC policies with deny-overrides. Implements ENT1-R3."""

    def __init__(self, policies: tuple[ABACPolicy, ...] = ()): 
        if any(not isinstance(p, ABACPolicy) for p in policies):
            raise ContractError("policies must be ABACPolicy objects")
        names = [p.name for p in policies]
        if len(set(names)) != len(names):
            raise ContractError("duplicate policy names")
        self._policies = tuple(policies)

    @property
    def policies(self) -> tuple[ABACPolicy, ...]:
        return self._policies

    def add_policy(self, policy: ABACPolicy) -> None:
        if not isinstance(policy, ABACPolicy):
            raise ContractError("expected an ABACPolicy")
        if policy.name in {p.name for p in self._policies}:
            raise ContractError("duplicate policy name")
        self._policies += (policy,)

    def evaluate(
        self,
        attributes: UserAttributes,
        category: str,
        scope: str = WILDCARD,
    ) -> ABACDecision:
        """Evaluate a permission request against attributes (ENT1-R3)."""
        if not isinstance(attributes, UserAttributes):
            raise ContractError("attributes must be UserAttributes")
        if category not in PERMISSION_CATEGORIES:
            raise ContractError(f"unknown permission category {category!r}")
        matched_allow = []
        matched_deny = []
        for policy in self._policies:
            if not policy.applies(attributes, category, scope):
                continue
            (matched_allow if policy.effect == ALLOW else matched_deny).append(policy.name)
        return ABACDecision(
            allowed=not matched_deny and bool(matched_allow),
            matched_allow=tuple(matched_allow),
            matched_deny=tuple(matched_deny),
        )
