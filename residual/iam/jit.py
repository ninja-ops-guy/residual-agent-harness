"""Just-In-Time (JIT) access elevation for Enterprise IAM.

Implements ENT1-R4: a user may request temporary elevation for a
specific task or time window. Elevation expires automatically, is
observed, produces a receipt, and requires pre-authorization from a
designated approver.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Callable

from ..core import ContractError, identifier
from .events import EVENT_ACCESS_DENIED, EVENT_ELEVATION, EventLog, subject_identifier
from .rbac import PERMISSION_CATEGORIES, WILDCARD, RoleRegistry

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_DENIED = "denied"
STATUS_EXPIRED = "expired"

MAX_ELEVATION_SECONDS = 24 * 3600


@dataclass(frozen=True)
class ElevationRequest:
    """A pending or decided JIT elevation request. Implements ENT1-R4."""

    request_id: str
    subject_id: str
    category: str
    scope: str
    reason: str
    duration_seconds: int
    requested_at: int
    task_id: str | None = None

    def __post_init__(self):
        identifier(self.request_id)
        subject_identifier(self.subject_id)
        if self.category not in PERMISSION_CATEGORIES:
            raise ContractError(f"unknown permission category {self.category!r}")
        if not isinstance(self.scope, str) or not self.scope.strip():
            raise ContractError("elevation scope must be a non-empty string")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ContractError("elevation requires a reason")
        if type(self.duration_seconds) is not int or not (
                0 < self.duration_seconds <= MAX_ELEVATION_SECONDS):
            raise ContractError("elevation duration out of range")
        if type(self.requested_at) is not int:
            raise ContractError("requested_at must be an integer")
        if self.task_id is not None:
            identifier(self.task_id)


@dataclass(frozen=True)
class ElevationGrant:
    """An approved, time-boxed elevation grant. Implements ENT1-R4."""

    request: ElevationRequest
    approver_id: str
    granted_at: int
    expires_at: int

    def __post_init__(self):
        if not isinstance(self.request, ElevationRequest):
            raise ContractError("grant requires an ElevationRequest")
        identifier(self.approver_id)
        if type(self.granted_at) is not int or type(self.expires_at) is not int:
            raise ContractError("grant times must be integers")
        if self.expires_at <= self.granted_at:
            raise ContractError("grant must expire after it is granted")

    def is_active(self, now: int) -> bool:
        return self.granted_at <= now < self.expires_at


class JITManager:
    """Manages JIT elevation lifecycle. Implements ENT1-R4.

    Pre-authorization: only subjects registered via ``add_approver``
    may approve requests, and approvers may not approve their own
    requests.
    """

    def __init__(self, roles: RoleRegistry, log: EventLog, clock: Callable[[], int]):
        if not isinstance(roles, RoleRegistry):
            raise ContractError("roles must be a RoleRegistry")
        if not isinstance(log, EventLog):
            raise ContractError("log must be an EventLog")
        if not callable(clock):
            raise ContractError("clock must be callable")
        self._roles = roles
        self._log = log
        self._clock = clock
        self._approvers: set[str] = set()
        self._requests: dict[str, ElevationRequest] = {}
        self._grants: list[ElevationGrant] = []
        self._denied: set[str] = set()

    def add_approver(self, approver_id: str) -> None:
        identifier(approver_id)
        self._approvers.add(approver_id)

    @property
    def approvers(self) -> tuple[str, ...]:
        return tuple(sorted(self._approvers))

    @property
    def grants(self) -> tuple[ElevationGrant, ...]:
        return tuple(self._grants)

    def request_elevation(
        self,
        subject_id: str,
        category: str,
        *,
        scope: str = WILDCARD,
        reason: str,
        duration_seconds: int,
        task_id: str | None = None,
    ) -> ElevationRequest:
        """Create a pending elevation request. Implements ENT1-R4."""
        now = self._clock()
        if type(now) is not int:
            raise ContractError("clock must return integer time")
        request = ElevationRequest(
            request_id="jit-" + secrets.token_hex(8),
            subject_id=subject_id,
            category=category,
            scope=scope,
            reason=reason,
            duration_seconds=duration_seconds,
            requested_at=now,
            task_id=task_id,
        )
        self._requests[request.request_id] = request
        return request

    def approve(self, request_id: str, approver_id: str, source_ip: str) -> ElevationGrant:
        """Approve a pending request; emits observation + receipt (ENT1-R4)."""
        identifier(approver_id)
        if request_id not in self._requests:
            raise ContractError("unknown elevation request")
        request = self._requests.pop(request_id)
        if request_id in self._denied:
            raise ContractError("elevation request already denied")
        if approver_id not in self._approvers or approver_id == request.subject_id:
            self._log.record(
                EVENT_ACCESS_DENIED,
                request.subject_id,
                source_ip,
                "deny",
                details={"kind": "jit_approval", "approver": approver_id,
                         "category": request.category, "scope": request.scope},
            )
            raise ContractError("approver is not designated for JIT pre-authorization")
        now = self._clock()
        grant = ElevationGrant(
            request=request,
            approver_id=approver_id,
            granted_at=now,
            expires_at=now + request.duration_seconds,
        )
        self._grants.append(grant)
        self._log.record(
            EVENT_ELEVATION,
            request.subject_id,
            source_ip,
            "allow",
            details={
                "kind": "jit_elevation",
                "approver": approver_id,
                "category": request.category,
                "scope": request.scope,
                "task_id": request.task_id,
                "expires_at": grant.expires_at,
                "reason": request.reason,
            },
        )
        return grant

    def deny(self, request_id: str, approver_id: str, source_ip: str) -> None:
        """Deny a pending request; the denial is observed (ENT1-R4/R6)."""
        identifier(approver_id)
        if request_id not in self._requests or request_id in self._denied:
            raise ContractError("unknown elevation request")
        request = self._requests.pop(request_id)
        self._denied.add(request_id)
        self._log.record(
            EVENT_ACCESS_DENIED,
            request.subject_id,
            source_ip,
            "deny",
            details={"kind": "jit_denied", "approver": approver_id,
                     "category": request.category, "scope": request.scope},
        )

    def is_elevated(self, subject_id: str, category: str, scope: str = WILDCARD) -> bool:
        """Check for an active (unexpired) grant. Implements ENT1-R4:
        elevation expires automatically once the window passes."""
        subject_identifier(subject_id)
        if category not in PERMISSION_CATEGORIES:
            raise ContractError(f"unknown permission category {category!r}")
        now = self._clock()
        for grant in self._grants:
            if grant.request.subject_id != subject_id:
                continue
            if grant.request.category != category:
                continue
            if grant.request.scope not in (WILDCARD, scope):
                continue
            if grant.is_active(now):
                return True
        return False

    def active_grants(self, subject_id: str) -> tuple[ElevationGrant, ...]:
        subject_identifier(subject_id)
        now = self._clock()
        return tuple(
            g for g in self._grants
            if g.request.subject_id == subject_id and g.is_active(now)
        )

    def is_allowed(self, subject_id: str, category: str, scope: str = WILDCARD) -> bool:
        """Combined RBAC + JIT decision. Implements ENT1-R2 + ENT1-R4."""
        return self._roles.is_allowed(subject_id, category, scope) or self.is_elevated(
            subject_id, category, scope
        )
