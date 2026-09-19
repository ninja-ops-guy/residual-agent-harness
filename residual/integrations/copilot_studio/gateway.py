"""Framework-neutral Copilot Studio gateway and authorization boundary."""
from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ...core import ContractError, canonical, digest, identifier
from ...factory.compiler import RequirementCompiler
from ...factory.models import ExecutionPlan
from .auth import CopilotIdentityVerifier, CopilotPrincipal
from .policy import DepartmentProfile, MissionTemplate

_MISSION_RE = re.compile(r"^m-[0-9a-f]{32}$")
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_MAX_INPUT_BYTES = 64 * 1024


def _validate_request_id(value: str) -> str:
    if not isinstance(value, str) or not _REQUEST_ID_RE.fullmatch(value):
        raise ContractError("request_id must be 1-128 safe identifier characters")
    return value
_TERMINAL = frozenset({"completed", "failed", "cancelled", "rejected"})


class CopilotAccessError(ContractError):
    """Stable error carrying an HTTP-oriented code and status."""

    def __init__(self, code: str, message: str, status: int):
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class MissionRequest:
    request_id: str
    template_id: str
    objective: str
    inputs: dict[str, Any]

    def __post_init__(self):
        _validate_request_id(self.request_id)
        identifier(self.template_id)
        if not isinstance(self.objective, str) or not self.objective.strip():
            raise ContractError("objective is required")
        objective = self.objective.strip()
        if len(objective) > 8000:
            raise ContractError("objective exceeds 8000 characters")
        if not isinstance(self.inputs, dict):
            raise ContractError("inputs must be an object")
        encoded = canonical(self.inputs).encode("utf-8")
        if len(encoded) > _MAX_INPUT_BYTES:
            raise ContractError("inputs exceed 64 KB")
        object.__setattr__(self, "objective", objective)
        object.__setattr__(self, "inputs", json.loads(canonical(self.inputs)))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionRequest":
        if not isinstance(data, dict):
            raise ContractError("mission request must be an object")
        required = {"request_id", "template_id", "objective", "inputs"}
        if set(data) != required:
            raise ContractError("mission request fields must exactly match the API contract")
        return cls(
            request_id=data["request_id"],
            template_id=data["template_id"],
            objective=data["objective"],
            inputs=data["inputs"],
        )

    def payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "template_id": self.template_id,
            "objective": self.objective,
            "inputs": self.inputs,
        }

    @property
    def request_hash(self) -> str:
        return digest(self.payload())


@dataclass(frozen=True)
class MissionBinding:
    mission_id: str
    tenant_id: str
    subject_id: str
    object_id: str
    department: str
    request_id: str
    request_hash: str
    template_id: str
    plan_hash: str
    capabilities: tuple[str, ...]

    def __post_init__(self):
        if not _MISSION_RE.fullmatch(self.mission_id):
            raise ContractError("invalid mission id")
        identifier(self.department)
        _validate_request_id(self.request_id)
        identifier(self.template_id)
        for name in ("tenant_id", "subject_id", "object_id", "request_hash", "plan_hash"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ContractError(f"{name} is required")
        if not isinstance(self.capabilities, tuple) or not self.capabilities:
            raise ContractError("capabilities must be a non-empty tuple")

    @property
    def binding_hash(self) -> str:
        return digest({
            "mission_id": self.mission_id,
            "tenant_id": self.tenant_id,
            "subject_id": self.subject_id,
            "object_id": self.object_id,
            "department": self.department,
            "request_id": self.request_id,
            "request_hash": self.request_hash,
            "template_id": self.template_id,
            "plan_hash": self.plan_hash,
            "capabilities": list(self.capabilities),
        })


@runtime_checkable
class MissionBackend(Protocol):
    """Host adapter. Implementations must preserve the supplied mission binding."""

    def submit(self, binding: MissionBinding, request: MissionRequest,
               plan: ExecutionPlan) -> dict[str, Any]: ...
    def status(self, mission_id: str) -> dict[str, Any]: ...
    def evidence(self, mission_id: str) -> tuple[dict[str, Any], ...]: ...
    def cancel(self, mission_id: str) -> dict[str, Any]: ...


class InMemoryMissionBackend:
    """Deterministic development/test backend. It never executes tools."""

    def __init__(self):
        self._missions: dict[str, dict[str, Any]] = {}
        self._evidence: dict[str, list[dict[str, Any]]] = {}

    def submit(self, binding: MissionBinding, request: MissionRequest,
               plan: ExecutionPlan) -> dict[str, Any]:
        if binding.mission_id in self._missions:
            return dict(self._missions[binding.mission_id])
        row = {
            "mission_id": binding.mission_id,
            "state": "queued",
            "template_id": binding.template_id,
            "approval_required": False,
            "binding_hash": binding.binding_hash,
            "plan_hash": plan.graph_hash,
        }
        self._missions[binding.mission_id] = row
        self._evidence[binding.mission_id] = [{
            "kind": "mission_binding",
            "binding_hash": binding.binding_hash,
            "request_hash": binding.request_hash,
            "plan_hash": binding.plan_hash,
        }]
        return dict(row)

    def status(self, mission_id: str) -> dict[str, Any]:
        if mission_id not in self._missions:
            raise ContractError("unknown mission")
        return dict(self._missions[mission_id])

    def evidence(self, mission_id: str) -> tuple[dict[str, Any], ...]:
        if mission_id not in self._missions:
            raise ContractError("unknown mission")
        return tuple(json.loads(canonical(item)) for item in self._evidence[mission_id])

    def cancel(self, mission_id: str) -> dict[str, Any]:
        row = self.status(mission_id)
        if row["state"] not in _TERMINAL:
            row["state"] = "cancelled"
            self._missions[mission_id] = row
        return dict(row)


@dataclass(frozen=True)
class _OwnershipRecord:
    tenant_id: str
    object_id: str
    department: str
    request_hash: str
    mission_id: str
    template_id: str


class CopilotMissionGateway:
    """Authenticate -> authorize -> compile -> bind -> submit.

    The gateway never derives capabilities from free text. A server-owned
    MissionTemplate is selected after identity verification and department
    authorization; the objective can influence work content, not authority.
    """

    def __init__(
        self,
        identity_verifier: CopilotIdentityVerifier,
        profile: DepartmentProfile,
        templates: dict[str, MissionTemplate],
        backend: MissionBackend,
        *,
        compiler: RequirementCompiler | None = None,
    ):
        if not isinstance(identity_verifier, CopilotIdentityVerifier):
            raise ContractError("identity_verifier is required")
        if not isinstance(profile, DepartmentProfile):
            raise ContractError("profile is required")
        if not isinstance(templates, dict) or not templates:
            raise ContractError("templates are required")
        if not isinstance(backend, MissionBackend):
            raise ContractError("backend does not satisfy MissionBackend")
        for key, template in templates.items():
            if not isinstance(key, str) or not isinstance(template, MissionTemplate):
                raise ContractError("templates must map ids to MissionTemplate objects")
            if key != template.template_id:
                raise ContractError("template registry key/id mismatch")
        self._identity = identity_verifier
        self._profile = profile
        self._templates = dict(templates)
        self._backend = backend
        self._compiler = compiler or RequirementCompiler()
        self._idempotency: dict[tuple[str, str, str], _OwnershipRecord] = {}
        self._owners: dict[str, _OwnershipRecord] = {}
        self._lock = threading.RLock()

    def _principal(self, token: str, now: int) -> CopilotPrincipal:
        try:
            return self._identity.verify(token, now=now)
        except ContractError as exc:
            raise CopilotAccessError("unauthorized", str(exc), 401) from exc

    def _template(self, template_id: str) -> MissionTemplate:
        template = self._templates.get(template_id)
        if template is None:
            raise CopilotAccessError("template_not_found", "unknown mission template", 400)
        return template

    def _authorize(self, principal: CopilotPrincipal, template: MissionTemplate) -> None:
        try:
            self._profile.authorize(principal, template)
        except ContractError as exc:
            raise CopilotAccessError("forbidden", str(exc), 403) from exc

    def _compile(self, request: MissionRequest, template: MissionTemplate) -> ExecutionPlan:
        result = self._compiler.compile({
            "intent": f"{template.template_id}: {request.objective}",
            "requirements": [{
                "id": "mission",
                "statement": request.objective,
                "acceptance": list(template.acceptance),
                "depends_on": [],
            }],
        })
        if not result.ready or result.plan is None:
            raise CopilotAccessError(
                "mission_ambiguous",
                "; ".join(result.questions) or "mission could not be compiled",
                400,
            )
        return result.plan

    def submit(self, token: str, payload: dict[str, Any], *, now: int) -> dict[str, Any]:
        principal = self._principal(token, now)
        try:
            request = MissionRequest.from_dict(payload)
        except ContractError as exc:
            raise CopilotAccessError("invalid_request", str(exc), 400) from exc
        template = self._template(request.template_id)
        self._authorize(principal, template)
        plan = self._compile(request, template)

        key = (principal.tenant_id, principal.object_id, request.request_id)
        with self._lock:
            prior = self._idempotency.get(key)
            if prior is not None:
                if prior.request_hash != request.request_hash:
                    raise CopilotAccessError(
                        "idempotency_conflict",
                        "request_id was already used with a different canonical payload",
                        409,
                    )
                return self._response(
                    self._backend.status(prior.mission_id),
                    self._template(prior.template_id),
                    prior.mission_id,
                )

            mission_id = "m-" + digest({
                "tenant_id": principal.tenant_id,
                "object_id": principal.object_id,
                "department": self._profile.profile_id,
                "request_id": request.request_id,
                "request_hash": request.request_hash,
                "template_id": template.template_id,
                "plan_hash": plan.graph_hash,
            })[:32]
            binding = MissionBinding(
                mission_id=mission_id,
                tenant_id=principal.tenant_id,
                subject_id=principal.subject_id,
                object_id=principal.object_id,
                department=self._profile.profile_id,
                request_id=request.request_id,
                request_hash=request.request_hash,
                template_id=template.template_id,
                plan_hash=plan.graph_hash,
                capabilities=tuple(sorted(template.capabilities)),
            )
            row = self._backend.submit(binding, request, plan)
            record = _OwnershipRecord(
                tenant_id=principal.tenant_id,
                object_id=principal.object_id,
                department=self._profile.profile_id,
                request_hash=request.request_hash,
                mission_id=mission_id,
                template_id=template.template_id,
            )
            self._idempotency[key] = record
            self._owners[mission_id] = record
            return self._response(row, template, mission_id)

    def _require_owner(self, token: str, mission_id: str, *, now: int) -> _OwnershipRecord:
        if not isinstance(mission_id, str) or not _MISSION_RE.fullmatch(mission_id):
            raise CopilotAccessError("not_found", "unknown mission", 404)
        principal = self._principal(token, now)
        try:
            self._profile.require_membership(principal)
        except ContractError as exc:
            raise CopilotAccessError("forbidden", str(exc), 403) from exc
        record = self._owners.get(mission_id)
        if record is None:
            raise CopilotAccessError("not_found", "unknown mission", 404)
        if record.tenant_id != principal.tenant_id or record.object_id != principal.object_id:
            raise CopilotAccessError("not_found", "unknown mission", 404)
        return record

    def status(self, token: str, mission_id: str, *, now: int) -> dict[str, Any]:
        record = self._require_owner(token, mission_id, now=now)
        return self._response(
            self._backend.status(mission_id),
            self._template(record.template_id),
            mission_id,
        )

    def evidence(self, token: str, mission_id: str, *, now: int) -> dict[str, Any]:
        self._require_owner(token, mission_id, now=now)
        evidence = self._backend.evidence(mission_id)
        return {"mission_id": mission_id, "evidence": list(evidence)}

    def cancel(self, token: str, mission_id: str, *, now: int) -> dict[str, Any]:
        record = self._require_owner(token, mission_id, now=now)
        return self._response(
            self._backend.cancel(mission_id),
            self._template(record.template_id),
            mission_id,
        )

    @staticmethod
    def _response(row: dict[str, Any], template: MissionTemplate,
                  mission_id: str) -> dict[str, Any]:
        state = row.get("state", "unknown")
        return {
            "mission_id": mission_id,
            "state": state,
            "template_id": template.template_id,
            "risk": template.risk,
            "approval_required": bool(row.get("approval_required", False)),
            "evidence_ref": (
                f"/v1/copilot/missions/{mission_id}/evidence"
                if row.get("binding_hash") else None
            ),
        }


@dataclass(frozen=True)
class APIResponse:
    status: int
    body: dict[str, Any]


class CopilotAPI:
    """Small framework-neutral router matching the frozen OpenAPI surface."""

    def __init__(self, gateway: CopilotMissionGateway):
        if not isinstance(gateway, CopilotMissionGateway):
            raise ContractError("gateway is required")
        self._gateway = gateway

    @staticmethod
    def _token(authorization: str | None) -> str:
        if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
            raise CopilotAccessError("unauthorized", "bearer token required", 401)
        token = authorization[7:].strip()
        if not token:
            raise CopilotAccessError("unauthorized", "bearer token required", 401)
        return token

    def handle(self, method: str, path: str, authorization: str | None,
               payload: dict[str, Any] | None, *, now: int) -> APIResponse:
        try:
            token = self._token(authorization)
            method = method.upper()
            if method == "POST" and path == "/v1/copilot/missions":
                body = self._gateway.submit(token, payload or {}, now=now)
                return APIResponse(202, body)

            prefix = "/v1/copilot/missions/"
            if not path.startswith(prefix):
                raise CopilotAccessError("not_found", "route not found", 404)
            suffix = path[len(prefix):]
            parts = suffix.split("/")
            mission_id = parts[0]
            if len(parts) == 1 and method == "GET":
                return APIResponse(200, self._gateway.status(token, mission_id, now=now))
            if len(parts) == 2 and parts[1] == "evidence" and method == "GET":
                return APIResponse(200, self._gateway.evidence(token, mission_id, now=now))
            if len(parts) == 2 and parts[1] == "cancel" and method == "POST":
                return APIResponse(202, self._gateway.cancel(token, mission_id, now=now))
            raise CopilotAccessError("not_found", "route not found", 404)
        except CopilotAccessError as exc:
            return APIResponse(exc.status, {"code": exc.code, "message": str(exc)})
        except ContractError:
            return APIResponse(
                500,
                {"code": "internal_contract_error", "message": "internal contract failure"},
            )
