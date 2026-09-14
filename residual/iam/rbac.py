"""Role-Based Access Control (RBAC) for Enterprise IAM.

Implements ENT1-R2: fine-grained, role-based permissions definable at
the level of task types, swarm participation, HITL approval authority,
receipt visibility, module installation, and policy modification.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core import ContractError, identifier
from .events import subject_identifier

#: Permission categories implementing ENT1-R2.
PERMISSION_TASK_TYPE = "task_type"
PERMISSION_SWARM = "swarm_participation"
PERMISSION_HITL_APPROVAL = "hitl_approval"
PERMISSION_RECEIPT_VISIBILITY = "receipt_visibility"
PERMISSION_MODULE_INSTALLATION = "module_installation"
PERMISSION_POLICY_MODIFICATION = "policy_modification"

PERMISSION_CATEGORIES = frozenset({
    PERMISSION_TASK_TYPE,
    PERMISSION_SWARM,
    PERMISSION_HITL_APPROVAL,
    PERMISSION_RECEIPT_VISIBILITY,
    PERMISSION_MODULE_INSTALLATION,
    PERMISSION_POLICY_MODIFICATION,
})

WILDCARD = "*"


@dataclass(frozen=True)
class Permission:
    """A fine-grained permission: category + scope. Implements ENT1-R2.

    ``scope`` narrows the permission (e.g. a task-type name, a swarm id,
    a receipt namespace); ``"*"`` means unrestricted within the category.
    """

    category: str
    scope: str = WILDCARD

    def __post_init__(self):
        if self.category not in PERMISSION_CATEGORIES:
            raise ContractError(f"unknown permission category {self.category!r}")
        if not isinstance(self.scope, str) or not self.scope.strip():
            raise ContractError("permission scope must be a non-empty string")

    def grants(self, category: str, scope: str) -> bool:
        if self.category != category:
            return False
        return self.scope == WILDCARD or self.scope == scope


@dataclass(frozen=True)
class Role:
    """A named bundle of fine-grained permissions. Implements ENT1-R2."""

    name: str
    permissions: frozenset[Permission] = field(default_factory=frozenset)
    description: str = ""

    def __post_init__(self):
        identifier(self.name)
        if not isinstance(self.permissions, frozenset):
            raise ContractError("role permissions must be a frozenset")
        if any(not isinstance(p, Permission) for p in self.permissions):
            raise ContractError("role permissions must be Permission objects")
        if not isinstance(self.description, str):
            raise ContractError("role description must be a string")

    def grants(self, category: str, scope: str = WILDCARD) -> bool:
        return any(p.grants(category, scope) for p in self.permissions)


class RoleRegistry:
    """Defines roles and assigns them to subjects. Implements ENT1-R2."""

    def __init__(self):
        self._roles: dict[str, Role] = {}
        self._assignments: dict[str, set[str]] = {}

    def define_role(self, role: Role) -> Role:
        if not isinstance(role, Role):
            raise ContractError("expected a Role")
        self._roles[role.name] = role
        return role

    def get_role(self, name: str) -> Role:
        if name not in self._roles:
            raise ContractError(f"unknown role {name!r}")
        return self._roles[name]

    @property
    def roles(self) -> tuple[Role, ...]:
        return tuple(self._roles.values())

    def assign(self, subject_id: str, role_name: str) -> None:
        subject_identifier(subject_id)
        self.get_role(role_name)
        self._assignments.setdefault(subject_id, set()).add(role_name)

    def unassign(self, subject_id: str, role_name: str) -> None:
        subject_identifier(subject_id)
        self._assignments.get(subject_id, set()).discard(role_name)

    def roles_for(self, subject_id: str) -> tuple[Role, ...]:
        subject_identifier(subject_id)
        return tuple(
            self._roles[name]
            for name in sorted(self._assignments.get(subject_id, set()))
            if name in self._roles
        )

    def is_allowed(self, subject_id: str, category: str, scope: str = WILDCARD) -> bool:
        """Decide whether a subject holds a permission. Implements ENT1-R2."""
        if category not in PERMISSION_CATEGORIES:
            raise ContractError(f"unknown permission category {category!r}")
        return any(role.grants(category, scope) for role in self.roles_for(subject_id))
