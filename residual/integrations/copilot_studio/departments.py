"""Department template metadata for native Copilot Studio packaging.

These objects describe what gets authored/shared in Copilot Studio and what
RESIDUAL backend profile it may target. They do not grant runtime authority;
the gateway policy remains independently authoritative.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from ...core import ContractError


_ID = re.compile(r"[a-z][a-z0-9-]{1,63}")
_ALLOWED_STATUS = frozenset({"pilot", "planned"})
_ALLOWED_PUBLISH = frozenset({"inactive", "active"})
_ALLOWED_ORCHESTRATION = frozenset({"generative"})
_ALLOWED_OPERATIONS = frozenset({
    "submitResidualMission",
    "getResidualMission",
    "getResidualMissionEvidence",
    "cancelResidualMission",
})


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ContractError(f"invalid {name}")
    return value


def _guid(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{name} must be a GUID")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        raise ContractError(f"{name} must be a GUID") from None
    if str(parsed).lower() != value.lower():
        raise ContractError(f"{name} must use canonical GUID form")
    return str(parsed)


def _strings(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ContractError(f"{name} must be a string array")
    normalized = tuple(item.strip() for item in value)
    if len(normalized) != len(set(normalized)):
        raise ContractError(f"{name} must not contain duplicates")
    return normalized


@dataclass(frozen=True)
class AgentTemplate:
    name: str
    description: str
    instructions: str
    orchestration: str
    publish_status: str
    chat_security_group_id: str
    maker_security_group_id: str
    solution_name: str
    connector_reference: str
    connector_operations: tuple[str, ...]
    knowledge_slots: tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ContractError("agent template name is required")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ContractError("agent template description is required")
        if (
            not isinstance(self.instructions, str)
            or not self.instructions.strip()
            or len(self.instructions) > 8_000
        ):
            raise ContractError("agent template instructions are required and bounded")
        if self.orchestration not in _ALLOWED_ORCHESTRATION:
            raise ContractError("unsupported Copilot orchestration mode")
        if self.publish_status not in _ALLOWED_PUBLISH:
            raise ContractError("invalid Agent Library publish status")
        object.__setattr__(
            self,
            "chat_security_group_id",
            _guid(self.chat_security_group_id, "chat_security_group_id"),
        )
        object.__setattr__(
            self,
            "maker_security_group_id",
            _guid(self.maker_security_group_id, "maker_security_group_id"),
        )
        _identifier(self.solution_name, "solution_name")
        _identifier(self.connector_reference, "connector_reference")
        operations = _strings(self.connector_operations, "connector_operations")
        if not set(operations) <= _ALLOWED_OPERATIONS:
            raise ContractError("department template references unknown connector operation")
        object.__setattr__(self, "connector_operations", tuple(sorted(operations)))
        object.__setattr__(
            self,
            "knowledge_slots",
            tuple(sorted(_strings(self.knowledge_slots, "knowledge_slots"))),
        )


@dataclass(frozen=True)
class ResidualDepartmentBinding:
    mission_profile_id: str
    executable_templates: tuple[str, ...]
    planned_templates: tuple[str, ...]
    assigned_agent_roles: tuple[str, ...]
    evidence_scope: str
    external_write_policy: str

    def __post_init__(self):
        _identifier(self.mission_profile_id, "mission_profile_id")
        executable = tuple(sorted(_strings(
            self.executable_templates, "executable_templates"
        )))
        planned = tuple(sorted(_strings(
            self.planned_templates, "planned_templates"
        )))
        if set(executable) & set(planned):
            raise ContractError("template cannot be both executable and planned")
        object.__setattr__(self, "executable_templates", executable)
        object.__setattr__(self, "planned_templates", planned)
        roles = tuple(sorted(_strings(
            self.assigned_agent_roles, "assigned_agent_roles"
        )))
        if not roles:
            raise ContractError("department requires at least one assigned agent role")
        object.__setattr__(self, "assigned_agent_roles", roles)
        if self.evidence_scope not in {
            "own-missions",
            "own-department",
            "authorized-cross-department-review",
        }:
            raise ContractError("invalid evidence scope")
        if self.external_write_policy not in {"prohibited", "human-approval"}:
            raise ContractError("invalid external write policy")


@dataclass(frozen=True)
class DepartmentProfile:
    schema_version: str
    department_id: str
    display_name: str
    backend_status: str
    agent: AgentTemplate
    residual: ResidualDepartmentBinding

    def __post_init__(self):
        if self.schema_version != "copilot-department-v1":
            raise ContractError("unsupported department profile schema")
        _identifier(self.department_id, "department_id")
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise ContractError("department display name is required")
        if self.backend_status not in _ALLOWED_STATUS:
            raise ContractError("invalid department backend status")
        if self.backend_status == "planned" and self.residual.executable_templates:
            raise ContractError(
                "planned department cannot advertise executable backend templates"
            )
        if self.agent.publish_status == "active" and self.backend_status != "pilot":
            raise ContractError(
                "planned department cannot be published active in Agent Library"
            )

    @classmethod
    def from_dict(cls, value: Any) -> "DepartmentProfile":
        if not isinstance(value, dict):
            raise ContractError("department profile must be an object")
        allowed = {
            "schema_version",
            "department_id",
            "display_name",
            "backend_status",
            "agent",
            "residual",
        }
        if set(value) != allowed:
            raise ContractError("department profile fields do not match schema")
        agent = value["agent"]
        residual = value["residual"]
        if not isinstance(agent, dict) or not isinstance(residual, dict):
            raise ContractError("agent and residual blocks must be objects")
        if set(agent) != {
            "name",
            "description",
            "instructions",
            "orchestration",
            "publish_status",
            "chat_security_group_id",
            "maker_security_group_id",
            "solution_name",
            "connector_reference",
            "connector_operations",
            "knowledge_slots",
        }:
            raise ContractError("agent fields do not match schema")
        if set(residual) != {
            "mission_profile_id",
            "executable_templates",
            "planned_templates",
            "assigned_agent_roles",
            "evidence_scope",
            "external_write_policy",
        }:
            raise ContractError("residual department fields do not match schema")
        return cls(
            schema_version=value["schema_version"],
            department_id=value["department_id"],
            display_name=value["display_name"],
            backend_status=value["backend_status"],
            agent=AgentTemplate(**agent),
            residual=ResidualDepartmentBinding(**residual),
        )


class DepartmentRegistry:
    """Immutable collection used by packaging/validation tooling."""

    def __init__(self, profiles: tuple[DepartmentProfile, ...]):
        if not isinstance(profiles, tuple) or not profiles:
            raise ContractError("department registry requires profiles")
        mapping: dict[str, DepartmentProfile] = {}
        solution_names: set[str] = set()
        for profile in profiles:
            if not isinstance(profile, DepartmentProfile):
                raise ContractError("department registry entries must be profiles")
            if profile.department_id in mapping:
                raise ContractError("duplicate department id")
            if profile.agent.solution_name in solution_names:
                raise ContractError("duplicate Copilot solution name")
            mapping[profile.department_id] = profile
            solution_names.add(profile.agent.solution_name)
        self._profiles: Mapping[str, DepartmentProfile] = MappingProxyType(
            dict(sorted(mapping.items()))
        )

    @property
    def profiles(self) -> Mapping[str, DepartmentProfile]:
        return self._profiles

    def get(self, department_id: str) -> DepartmentProfile:
        _identifier(department_id, "department_id")
        try:
            return self._profiles[department_id]
        except KeyError:
            raise ContractError("unknown department") from None
