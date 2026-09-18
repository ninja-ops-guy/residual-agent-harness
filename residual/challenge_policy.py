"""Governed challenge protocol for challengeable M6 semantic nodes."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .core import ContractError, digest


class ChallengeDisposition(str, Enum):
    OPEN = "open"
    REJECTED = "rejected"
    UPHELD = "upheld"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


@dataclass(frozen=True)
class ChallengePolicy:
    policy_id: str
    eligible_challenger_roles: tuple[str, ...]
    allowed_grounds: tuple[str, ...]
    resolution_authority_roles: tuple[str, ...]
    filing_window_events: int | None = None
    allow_withdrawal: bool = True
    revision: str = "1"

    def __post_init__(self) -> None:
        for name in ("policy_id","revision"):
            value=getattr(self,name)
            if not isinstance(value,str) or not value.strip():
                raise ContractError(f"{name} is required")
        for name in (
            "eligible_challenger_roles","allowed_grounds",
            "resolution_authority_roles",
        ):
            value=getattr(self,name)
            if not isinstance(value,tuple) or not value or any(
                not isinstance(x,str) or not x.strip() for x in value
            ):
                raise ContractError(f"{name} must contain nonempty values")
        if self.filing_window_events is not None and self.filing_window_events < 0:
            raise ContractError("filing_window_events must be >= 0")

    @property
    def policy_hash(self) -> str:
        return digest({
            "policy_id":self.policy_id,
            "eligible_challenger_roles":list(self.eligible_challenger_roles),
            "allowed_grounds":list(self.allowed_grounds),
            "resolution_authority_roles":list(self.resolution_authority_roles),
            "filing_window_events":self.filing_window_events,
            "allow_withdrawal":self.allow_withdrawal,
            "revision":self.revision,
        })


@dataclass(frozen=True)
class ChallengeRecord:
    challenge_id: str
    target_node_id: str
    policy_id: str
    challenger_role: str
    ground: str
    filed_event: int

    def __post_init__(self) -> None:
        for name in (
            "challenge_id","target_node_id","policy_id",
            "challenger_role","ground",
        ):
            value=getattr(self,name)
            if not isinstance(value,str) or not value.strip():
                raise ContractError(f"{name} is required")
        if self.filed_event < 0:
            raise ContractError("filed_event must be >= 0")


@dataclass(frozen=True)
class ChallengeResolution:
    challenge_id: str
    resolver_role: str
    disposition: ChallengeDisposition
    resolved_event: int
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.disposition,ChallengeDisposition):
            object.__setattr__(self,"disposition",ChallengeDisposition(self.disposition))
        if not isinstance(self.reason,str) or not self.reason.strip():
            raise ContractError("resolution reason is required")
        if self.resolved_event < 0:
            raise ContractError("resolved_event must be >= 0")


def validate_filing(
    policy: ChallengePolicy,
    record: ChallengeRecord,
    *,
    target_created_event: int,
) -> None:
    if record.policy_id != policy.policy_id:
        raise ContractError("challenge policy mismatch")
    if record.challenger_role not in policy.eligible_challenger_roles:
        raise ContractError("challenger role is not eligible")
    if record.ground not in policy.allowed_grounds:
        raise ContractError("challenge ground is not allowed")
    if record.filed_event < target_created_event:
        raise ContractError("challenge predates target")
    if (
        policy.filing_window_events is not None
        and record.filed_event - target_created_event > policy.filing_window_events
    ):
        raise ContractError("challenge filing window expired")


def validate_resolution(
    policy: ChallengePolicy,
    record: ChallengeRecord,
    resolution: ChallengeResolution,
) -> None:
    if resolution.challenge_id != record.challenge_id:
        raise ContractError("resolution challenge mismatch")
    if resolution.resolver_role not in policy.resolution_authority_roles:
        raise ContractError("resolver lacks authority")
    if resolution.resolved_event < record.filed_event:
        raise ContractError("resolution predates challenge")
    if (
        resolution.disposition == ChallengeDisposition.WITHDRAWN
        and not policy.allow_withdrawal
    ):
        raise ContractError("challenge withdrawal is not allowed")


def effective_disposition(
    policy: ChallengePolicy,
    record: ChallengeRecord,
    resolutions: Iterable[ChallengeResolution],
    *,
    at_event: int,
) -> ChallengeDisposition:
    validate_filing(policy,record,target_created_event=0)
    applicable=sorted(
        (r for r in resolutions if r.challenge_id==record.challenge_id and r.resolved_event<=at_event),
        key=lambda r:r.resolved_event,
    )
    for resolution in applicable:
        validate_resolution(policy,record,resolution)
    if applicable:
        return applicable[-1].disposition
    if (
        policy.filing_window_events is not None
        and at_event < record.filed_event
    ):
        raise ContractError("at_event predates challenge")
    return ChallengeDisposition.OPEN
