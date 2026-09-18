"""Authority-bound Copilot Studio mission service.

The service is transport agnostic.  It validates an end-user bearer token via an
injected OIDC client, derives authority only from verified claims, and compiles a
RESIDUAL control-plane Mission/MissionRevision.  It does not execute Factory
workers yet; a later integration layer consumes the prepared mission.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, replace
from typing import Any, Protocol

from ...control_plane.models import CapabilityGrant, Mission, MissionRevision
from ...core import ContractError, digest
from ...iam.oidc import OIDCClient
from ...iam.saml import Identity
from .contracts import CopilotAPIError, MissionRequest, VerifiedPrincipal
from .policy import FirmwarePolicy, PolicyDecision


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
    evidence_refs: tuple[str, ...] = ()

    def response(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission.mission_id,
            "state": self.state,
            "template_id": self.template_id,
            "risk": self.risk,
            "approval_required": self.approval_required,
            "evidence_ref": self.evidence_refs[-1] if self.evidence_refs else None,
        }


class CopilotMissionStore:
    """Thread-safe idempotency and subject/tenant isolation for gateway records."""

    def __init__(self):
        self._lock = threading.RLock()
        self._records: dict[str, CopilotMissionRecord] = {}
        self._requests: dict[tuple[str, str, str], str] = {}

    def create(self, record: CopilotMissionRecord) -> tuple[CopilotMissionRecord, bool]:
        key = (record.mission.tenant_id, record.mission.principal_id, record.request_id)
        with self._lock:
            existing_id = self._requests.get(key)
            if existing_id is not None:
                existing = self._records[existing_id]
                if existing.request_hash != record.request_hash:
                    raise CopilotAPIError(
                        409,
                        "idempotency_conflict",
                        "request_id was already used with a different request",
                    )
                return existing, False
            if record.mission.mission_id in self._records:
                raise CopilotAPIError(409, "mission_conflict", "mission identity collision")
            self._records[record.mission.mission_id] = record
            self._requests[key] = record.mission.mission_id
            return record, True

    def visible(self, mission_id: str, principal: VerifiedPrincipal) -> CopilotMissionRecord:
        with self._lock:
            record = self._records.get(mission_id)
            # Return not-found for ownership mismatches to avoid existence leaks.
            if (
                record is None
                or record.mission.tenant_id != principal.tenant_id
                or record.mission.principal_id != principal.subject
            ):
                raise CopilotAPIError(404, "mission_not_found", "mission was not found")
            return record

    def cancel(self, mission_id: str, principal: VerifiedPrincipal) -> CopilotMissionRecord:
        with self._lock:
            record = self.visible(mission_id, principal)
            if record.state in {"cancel_requested", "cancelled", "complete", "failed"}:
                return record
            updated = replace(record, state="cancel_requested")
            self._records[mission_id] = updated
            return updated

    def attach_evidence(self, mission_id: str, evidence_refs: tuple[str, ...]) -> CopilotMissionRecord:
        """Internal executor hook; not exposed as a user-controlled endpoint."""
        if not isinstance(evidence_refs, tuple) or any(
            not isinstance(ref, str) or not ref.strip() or len(ref) > 512 for ref in evidence_refs
        ):
            raise ContractError("evidence references must be nonempty strings")
        with self._lock:
            record = self._records.get(mission_id)
            if record is None:
                raise ContractError("unknown mission")
            updated = replace(record, evidence_refs=record.evidence_refs + evidence_refs)
            self._records[mission_id] = updated
            return updated

    def set_state(self, mission_id: str, state: str) -> CopilotMissionRecord:
        """Internal executor hook with deliberately small transition vocabulary."""
        if state not in {"prepared", "running", "approval_required", "complete", "failed", "cancelled"}:
            raise ContractError("invalid Copilot mission state")
        with self._lock:
            record = self._records.get(mission_id)
            if record is None:
                raise ContractError("unknown mission")
            if record.state == "cancel_requested" and state not in {"cancelled", "failed"}:
                raise ContractError("cancel-requested mission cannot resume")
            updated = replace(record, state=state)
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
        policy: FirmwarePolicy | None = None,
        store: CopilotMissionStore | None = None,
    ):
        if not hasattr(authenticator, "authenticate"):
            raise ContractError("Copilot Studio service requires a bearer authenticator")
        self.authenticator = authenticator
        self.policy = policy or FirmwarePolicy()
        self.store = store or CopilotMissionStore()

    def _principal(self, token: str, now: int) -> VerifiedPrincipal:
        if not isinstance(token, str) or not token:
            raise CopilotAPIError(401, "authentication_failed", "authentication is required")
        try:
            identity = self.authenticator.authenticate(token, now=now)
            return VerifiedPrincipal.from_identity(identity)
        except CopilotAPIError:
            raise
        except Exception:
            # Token/parser/key-provider details must never be reflected to Copilot.
            raise CopilotAPIError(401, "authentication_failed", "authentication failed") from None

    @staticmethod
    def _compile(
        principal: VerifiedPrincipal,
        request: MissionRequest,
        decision: PolicyDecision,
        now: int,
    ) -> CopilotMissionRecord:
        binding = {
            "tenant_id": principal.tenant_id,
            "subject": principal.subject,
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
                subject=principal.subject,
                action=capability,
                resource=decision.profile_id,
                scope={
                    "tenant_id": principal.tenant_id,
                    "template_id": decision.template_id,
                    "mission_id": mission_id,
                },
                constraints={
                    "risk": decision.risk,
                    "claims_hash": principal.claims_hash,
                },
                approval_policy={
                    "human_required": decision.approval_required,
                    "copilot_confirmation_is_not_residual_approval": True,
                },
            )
            for capability in decision.capabilities
        )
        revision_id = "rev-" + digest({"mission_id": mission_id, "plan_hash": plan_hash})[:32]
        mission = Mission(
            mission_id=mission_id,
            principal_id=principal.subject,
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
            budget={"risk": decision.risk, "source": "copilot-studio"},
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
        record, _created = self.store.create(candidate)
        return record.response()

    def get(self, token: str, mission_id: str, *, now: int) -> dict[str, Any]:
        principal = self._principal(token, now)
        return self.store.visible(mission_id, principal).response()

    def evidence(self, token: str, mission_id: str, *, now: int) -> dict[str, Any]:
        principal = self._principal(token, now)
        record = self.store.visible(mission_id, principal)
        return {
            "mission_id": record.mission.mission_id,
            "evidence": [{"ref": ref} for ref in record.evidence_refs],
        }

    def cancel(self, token: str, mission_id: str, *, now: int) -> dict[str, Any]:
        principal = self._principal(token, now)
        return self.store.cancel(mission_id, principal).response()
