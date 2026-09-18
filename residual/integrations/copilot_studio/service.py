"""Authority-bound Copilot Studio mission service."""
from __future__ import annotations

import threading
from dataclasses import dataclass, replace
from typing import Any, Protocol

from observation_layer.core import freeze

from ...control_plane.models import CapabilityGrant, Mission, MissionRevision
from ...core import ContractError, digest
from ...iam.oidc import OIDCClient
from ...iam.saml import Identity
from .contracts import CopilotAPIError, MissionRequest, VerifiedPrincipal
from .policy import FirmwarePolicy, PolicyDecision


ACTIVE_STATES = frozenset({
    "prepared", "running", "approval_required", "cancel_requested"
})
STATE_TRANSITIONS = {
    "prepared": frozenset({"running", "failed", "cancel_requested"}),
    "running": frozenset({
        "approval_required", "complete", "failed", "cancel_requested"
    }),
    "approval_required": frozenset({"running", "failed", "cancel_requested"}),
    "cancel_requested": frozenset({"cancelled", "failed"}),
    "cancelled": frozenset(),
    "complete": frozenset(),
    "failed": frozenset(),
}


class BearerAuthenticator(Protocol):
    def authenticate(self, token: str, *, now: int) -> Identity:
        ...


class OIDCBearerAuthenticator:
    """Adapter over RESIDUAL's existing OIDC verifier."""

    def __init__(self, client: OIDCClient):
        if not isinstance(client, OIDCClient):
            raise ContractError("OIDCBearerAuthenticator requires an OIDCClient")
        self.client = client

    def authenticate(self, token: str, *, now: int) -> Identity:
        return self.client.authenticate(token, now=now)


@dataclass(frozen=True)
class MissionEvidenceRef:
    """Evidence reference bound to the exact mission authority revision."""

    ref: str
    mission_id: str
    revision_id: str
    plan_hash: str
    policy_hash: str
    claims_hash: str

    def __post_init__(self):
        if not isinstance(self.ref, str) or not self.ref.strip() or len(self.ref) > 512:
            raise ContractError("evidence ref must be a nonempty bounded string")

    @property
    def binding_hash(self) -> str:
        return digest({
            "ref": self.ref,
            "mission_id": self.mission_id,
            "revision_id": self.revision_id,
            "plan_hash": self.plan_hash,
            "policy_hash": self.policy_hash,
            "claims_hash": self.claims_hash,
        })


@dataclass(frozen=True)
class CopilotMissionRecord:
    mission: Mission
    revision: MissionRevision
    request_id: str
    request_hash: str
    claims_hash: str
    profile_id: str
    template_id: str
    state: str
    risk: str
    approval_required: bool
    evidence_refs: tuple[MissionEvidenceRef, ...] = ()

    def __post_init__(self):
        if self.state not in STATE_TRANSITIONS:
            raise ContractError("invalid Copilot mission state")

    def bind_evidence(self, ref: str) -> MissionEvidenceRef:
        return MissionEvidenceRef(
            ref=ref,
            mission_id=self.mission.mission_id,
            revision_id=self.revision.revision_id,
            plan_hash=self.revision.plan_hash,
            policy_hash=self.revision.policy_hash,
            claims_hash=self.claims_hash,
        )

    def response(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission.mission_id,
            "state": self.state,
            "template_id": self.template_id,
            "risk": self.risk,
            "approval_required": self.approval_required,
            "evidence_ref": self.evidence_refs[-1].ref if self.evidence_refs else None,
        }


class CopilotMissionStore:
    """Thread-safe pilot store with strict replay, ownership and state semantics."""

    def __init__(self):
        self._lock = threading.RLock()
        self._records: dict[str, CopilotMissionRecord] = {}
        self._requests: dict[tuple[str, str, str], str] = {}

    @staticmethod
    def _check_retry(
        existing: CopilotMissionRecord,
        candidate: CopilotMissionRecord,
    ) -> None:
        if existing.request_hash != candidate.request_hash:
            raise CopilotAPIError(
                409,
                "idempotency_conflict",
                "request_id was already used with a different request",
            )
        if existing.revision.policy_hash != candidate.revision.policy_hash:
            raise CopilotAPIError(
                409,
                "policy_changed",
                "authorization policy changed since the original request",
            )
        if existing.claims_hash != candidate.claims_hash:
            raise CopilotAPIError(
                409,
                "identity_changed",
                "verified identity claims changed since the original request",
            )

    def create(
        self,
        record: CopilotMissionRecord,
        *,
        max_active: int,
    ) -> tuple[CopilotMissionRecord, bool]:
        key = (
            record.mission.tenant_id,
            record.mission.principal_id,
            record.request_id,
        )
        with self._lock:
            existing_id = self._requests.get(key)
            if existing_id is not None:
                existing = self._records[existing_id]
                self._check_retry(existing, record)
                return existing, False
            active = sum(
                candidate.state in ACTIVE_STATES
                and candidate.mission.tenant_id == record.mission.tenant_id
                and candidate.mission.principal_id == record.mission.principal_id
                for candidate in self._records.values()
            )
            if active >= max_active:
                raise CopilotAPIError(
                    429,
                    "mission_limit",
                    "too many active missions for the signed-in identity",
                )
            if record.mission.mission_id in self._records:
                raise CopilotAPIError(
                    409, "mission_conflict", "mission identity collision"
                )
            self._records[record.mission.mission_id] = record
            self._requests[key] = record.mission.mission_id
            return record, True

    def visible(
        self,
        mission_id: str,
        principal: VerifiedPrincipal,
    ) -> CopilotMissionRecord:
        with self._lock:
            record = self._records.get(mission_id)
            if (
                record is None
                or record.mission.tenant_id != principal.tenant_id
                or record.mission.principal_id != principal.principal_id
            ):
                raise CopilotAPIError(
                    404, "mission_not_found", "mission was not found"
                )
            return record

    def _transition(
        self,
        record: CopilotMissionRecord,
        state: str,
    ) -> CopilotMissionRecord:
        if state not in STATE_TRANSITIONS:
            raise ContractError("invalid Copilot mission state")
        if state not in STATE_TRANSITIONS[record.state]:
            raise ContractError(
                f"invalid Copilot mission transition {record.state}->{state}"
            )
        return replace(record, state=state)

    def cancel(
        self,
        mission_id: str,
        principal: VerifiedPrincipal,
    ) -> CopilotMissionRecord:
        with self._lock:
            record = self.visible(mission_id, principal)
            if record.state in {"cancel_requested", "cancelled", "complete", "failed"}:
                return record
            updated = self._transition(record, "cancel_requested")
            self._records[mission_id] = updated
            return updated

    def attach_evidence(
        self,
        mission_id: str,
        evidence: MissionEvidenceRef,
    ) -> CopilotMissionRecord:
        if not isinstance(evidence, MissionEvidenceRef):
            raise ContractError("evidence must be an authority-bound reference")
        with self._lock:
            record = self._records.get(mission_id)
            if record is None:
                raise ContractError("unknown mission")
            expected = record.bind_evidence(evidence.ref)
            if evidence != expected:
                raise ContractError("evidence binding does not match mission authority")
            if any(item.ref == evidence.ref for item in record.evidence_refs):
                return record
            updated = replace(
                record, evidence_refs=record.evidence_refs + (evidence,)
            )
            self._records[mission_id] = updated
            return updated

    def set_state(
        self,
        mission_id: str,
        state: str,
    ) -> CopilotMissionRecord:
        with self._lock:
            record = self._records.get(mission_id)
            if record is None:
                raise ContractError("unknown mission")
            updated = self._transition(record, state)
            self._records[mission_id] = updated
            return updated

    @property
    def records(self) -> tuple[CopilotMissionRecord, ...]:
        with self._lock:
            return tuple(self._records.values())


class CopilotStudioService:
    def __init__(
        self,
        authenticator: BearerAuthenticator,
        *,
        policy: FirmwarePolicy,
        store: CopilotMissionStore | Any | None = None,
    ):
        if not hasattr(authenticator, "authenticate"):
            raise ContractError(
                "Copilot Studio service requires a bearer authenticator"
            )
        if not isinstance(policy, FirmwarePolicy):
            raise ContractError(
                "Copilot Studio service requires an explicit FirmwarePolicy"
            )
        self.authenticator = authenticator
        self.policy = policy
        self.store = store or CopilotMissionStore()

    def _principal(self, token: str, now: int) -> VerifiedPrincipal:
        if not isinstance(token, str) or not token:
            raise CopilotAPIError(
                401, "authentication_failed", "authentication is required"
            )
        try:
            identity = self.authenticator.authenticate(token, now=now)
            return VerifiedPrincipal.from_identity(identity)
        except CopilotAPIError:
            raise
        except Exception:
            raise CopilotAPIError(
                401, "authentication_failed", "authentication failed"
            ) from None

    @staticmethod
    def _compile(
        principal: VerifiedPrincipal,
        request: MissionRequest,
        decision: PolicyDecision,
        now: int,
    ) -> CopilotMissionRecord:
        binding = {
            "tenant_id": principal.tenant_id,
            "object_id": principal.object_id,
            "request_id": request.request_id,
            "request_hash": request.payload_hash,
            "policy_hash": decision.policy_hash,
        }
        mission_id = "cps-" + digest(binding)[:32]
        plan_hash = digest({
            "template_id": decision.template_id,
            "objective": request.objective,
            "inputs": request.inputs,
            "capabilities": list(decision.capabilities),
        })
        grants = tuple(
            CapabilityGrant(
                subject=principal.principal_id,
                action=capability,
                resource=decision.profile_id,
                scope=freeze({
                    "tenant_id": principal.tenant_id,
                    "template_id": decision.template_id,
                    "mission_id": mission_id,
                }),
                constraints=freeze({
                    "risk": decision.risk,
                    "claims_hash": principal.claims_hash,
                }),
                approval_policy=freeze({
                    "human_required": decision.approval_required,
                    "copilot_confirmation_is_not_residual_approval": True,
                }),
            )
            for capability in decision.capabilities
        )
        revision_id = "rev-" + digest(
            {"mission_id": mission_id, "plan_hash": plan_hash}
        )[:32]
        mission = Mission(
            mission_id=mission_id,
            principal_id=principal.principal_id,
            tenant_id=principal.tenant_id,
            created_at=float(now),
        )
        revision = MissionRevision(
            mission_id=mission_id,
            revision_id=revision_id,
            objective=request.objective,
            plan_hash=plan_hash,
            policy_hash=decision.policy_hash,
            capability_grants=grants,
            budget=freeze({
                "risk": decision.risk,
                "source": "copilot-studio",
            }),
        )
        return CopilotMissionRecord(
            mission=mission,
            revision=revision,
            request_id=request.request_id,
            request_hash=request.payload_hash,
            claims_hash=principal.claims_hash,
            profile_id=decision.profile_id,
            template_id=decision.template_id,
            state="prepared",
            risk=decision.risk,
            approval_required=decision.approval_required,
        )

    def submit(self, token: str, body: Any, *, now: int) -> dict[str, Any]:
        principal = self._principal(token, now)
        request = MissionRequest.from_dict(body)
        decision = self.policy.authorize(principal, request)
        candidate = self._compile(principal, request, decision, now)
        record, _created = self.store.create(
            candidate,
            max_active=self.policy.max_active_missions,
        )
        return record.response()

    def get(
        self, token: str, mission_id: str, *, now: int
    ) -> dict[str, Any]:
        principal = self._principal(token, now)
        self.policy.authorize_principal(principal)
        return self.store.visible(mission_id, principal).response()

    def evidence(
        self, token: str, mission_id: str, *, now: int
    ) -> dict[str, Any]:
        principal = self._principal(token, now)
        self.policy.authorize_principal(principal)
        record = self.store.visible(mission_id, principal)
        return {
            "mission_id": record.mission.mission_id,
            "evidence": [
                {
                    "ref": item.ref,
                    "revision_id": item.revision_id,
                    "binding_hash": item.binding_hash,
                }
                for item in record.evidence_refs
            ],
        }

    def cancel(
        self, token: str, mission_id: str, *, now: int
    ) -> dict[str, Any]:
        principal = self._principal(token, now)
        self.policy.authorize_principal(principal)
        return self.store.cancel(mission_id, principal).response()
