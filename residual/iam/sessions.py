"""Enterprise session management for IAM.

Implements ENT1-R8: session management complies with enterprise
policies — configurable session timeout, idle timeout, concurrent
session limits, and IP-based restrictions. Sessions are revocable
immediately on security event, and lifecycle events are observed and
receipted (ENT1-R6).
"""
from __future__ import annotations

import ipaddress
import secrets
from dataclasses import dataclass
from typing import Callable

from ..core import ContractError, identifier
from .events import (
    subject_identifier,
    EVENT_ACCESS_DENIED,
    EVENT_LOGIN,
    EVENT_LOGOUT,
    EVENT_SESSION_REVOKED,
    EventLog,
    validate_ip,
)


@dataclass(frozen=True)
class SessionPolicy:
    """Configurable enterprise session policy. Implements ENT1-R8."""

    session_timeout: int = 8 * 3600  # absolute lifetime, seconds
    idle_timeout: int = 30 * 60  # idle lifetime, seconds
    max_concurrent: int = 3  # per subject
    allowed_networks: tuple[str, ...] = ()  # CIDRs; empty = any IP

    def __post_init__(self):
        for name in ("session_timeout", "idle_timeout", "max_concurrent"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ContractError(f"{name} must be a positive integer")
        if self.idle_timeout > self.session_timeout:
            raise ContractError("idle timeout cannot exceed session timeout")
        if not isinstance(self.allowed_networks, tuple):
            raise ContractError("allowed_networks must be a tuple of CIDRs")
        for cidr in self.allowed_networks:
            try:
                ipaddress.ip_network(cidr)
            except ValueError as exc:
                raise ContractError("invalid CIDR in allowed_networks") from exc

    def ip_allowed(self, ip: str) -> bool:
        """IP-based restriction check. Implements ENT1-R8."""
        validate_ip(ip)
        if not self.allowed_networks:
            return True
        address = ipaddress.ip_address(ip)
        return any(address in ipaddress.ip_network(cidr) for cidr in self.allowed_networks)


@dataclass(frozen=True)
class Session:
    """An authenticated session. Implements ENT1-R8."""

    session_id: str
    subject_id: str
    source_ip: str
    created_at: int
    last_active_at: int
    mfa_verified: bool = False
    subject_type: str = "human"

    def __post_init__(self):
        identifier(self.session_id)
        subject_identifier(self.subject_id)
        validate_ip(self.source_ip)
        if type(self.created_at) is not int or type(self.last_active_at) is not int:
            raise ContractError("session times must be integers")
        if self.last_active_at < self.created_at:
            raise ContractError("last activity precedes session creation")
        if type(self.mfa_verified) is not bool:
            raise ContractError("mfa_verified must be a bool")


class SessionManager:
    """Creates, validates, and revokes sessions. Implements ENT1-R8."""

    def __init__(self, policy: SessionPolicy, log: EventLog, clock: Callable[[], int]):
        if not isinstance(policy, SessionPolicy):
            raise ContractError("policy must be a SessionPolicy")
        if not isinstance(log, EventLog):
            raise ContractError("log must be an EventLog")
        if not callable(clock):
            raise ContractError("clock must be callable")
        self.policy = policy
        self._log = log
        self._clock = clock
        self._sessions: dict[str, Session] = {}
        self._revoked: set[str] = set()

    def _now(self) -> int:
        now = self._clock()
        if type(now) is not int:
            raise ContractError("clock must return integer time")
        return now

    def _active_for(self, subject_id: str) -> list[Session]:
        now = self._now()
        return [
            s for s in self._sessions.values()
            if s.subject_id == subject_id
            and s.session_id not in self._revoked
            and self._within_timeouts(s, now)
        ]

    def _within_timeouts(self, session: Session, now: int) -> bool:
        return (
            now < session.created_at + self.policy.session_timeout
            and now < session.last_active_at + self.policy.idle_timeout
        )

    def create_session(
        self,
        subject_id: str,
        source_ip: str,
        *,
        mfa_verified: bool = False,
        subject_type: str = "human",
    ) -> Session:
        """Create a session, enforcing IP restrictions and the concurrent
        session limit. Implements ENT1-R8; the login is observed (ENT1-R6)."""
        subject_identifier(subject_id)
        validate_ip(source_ip)
        if not self.policy.ip_allowed(source_ip):
            self._log.record(EVENT_ACCESS_DENIED, subject_id, source_ip, "deny",
                             details={"kind": "ip_restriction"}, subject_type=subject_type)
            raise ContractError("source IP is not allowed by session policy")
        if len(self._active_for(subject_id)) >= self.policy.max_concurrent:
            self._log.record(EVENT_ACCESS_DENIED, subject_id, source_ip, "deny",
                             details={"kind": "concurrent_limit"}, subject_type=subject_type)
            raise ContractError("concurrent session limit reached")
        now = self._now()
        session = Session(
            session_id="sess-" + secrets.token_hex(8),
            subject_id=subject_id,
            source_ip=source_ip,
            created_at=now,
            last_active_at=now,
            mfa_verified=mfa_verified,
            subject_type=subject_type,
        )
        self._sessions[session.session_id] = session
        self._log.record(EVENT_LOGIN, subject_id, source_ip, "allow",
                         details={"session_id": session.session_id, "mfa": mfa_verified},
                         subject_type=subject_type)
        return session

    def validate(self, session_id: str, source_ip: str | None = None) -> Session:
        """Validate a session: not revoked, within absolute and idle
        timeouts, and (when supplied) bound to its origin IP.

        Implements ENT1-R8."""
        identifier(session_id)
        if session_id not in self._sessions:
            raise ContractError("unknown session")
        if session_id in self._revoked:
            raise ContractError("session has been revoked")
        session = self._sessions[session_id]
        now = self._now()
        if not self._within_timeouts(session, now):
            raise ContractError("session expired")
        if source_ip is not None and source_ip != session.source_ip:
            raise ContractError("session IP mismatch")
        return session

    def touch(self, session_id: str, source_ip: str | None = None) -> Session:
        """Record activity, refreshing the idle clock. Implements ENT1-R8."""
        session = self.validate(session_id, source_ip)
        now = self._now()
        refreshed = Session(
            session_id=session.session_id,
            subject_id=session.subject_id,
            source_ip=session.source_ip,
            created_at=session.created_at,
            last_active_at=now,
            mfa_verified=session.mfa_verified,
            subject_type=session.subject_type,
        )
        self._sessions[session_id] = refreshed
        return refreshed

    def revoke(self, session_id: str, reason: str) -> None:
        """Revoke a session immediately on security event. ENT1-R8.
        The revocation is observed and receipted (ENT1-R6)."""
        identifier(session_id)
        if not isinstance(reason, str) or not reason.strip():
            raise ContractError("revocation reason is required")
        if session_id not in self._sessions:
            raise ContractError("unknown session")
        session = self._sessions[session_id]
        self._revoked.add(session_id)
        self._log.record(EVENT_SESSION_REVOKED, session.subject_id, session.source_ip, "allow",
                         details={"session_id": session_id, "reason": reason},
                         subject_type=session.subject_type)

    def revoke_all(self, subject_id: str, reason: str) -> int:
        """Revoke every session for a subject (security event). ENT1-R8."""
        subject_identifier(subject_id)
        count = 0
        for session in list(self._sessions.values()):
            if session.subject_id == subject_id and session.session_id not in self._revoked:
                self.revoke(session.session_id, reason)
                count += 1
        return count

    def logout(self, session_id: str) -> None:
        """End a session normally; the logout is observed (ENT1-R6)."""
        session = self.validate(session_id)
        self._revoked.add(session_id)
        self._log.record(EVENT_LOGOUT, session.subject_id, session.source_ip, "allow",
                         details={"session_id": session_id},
                         subject_type=session.subject_type)

    def is_revoked(self, session_id: str) -> bool:
        identifier(session_id)
        return session_id in self._revoked

    def active_sessions(self, subject_id: str) -> tuple[Session, ...]:
        subject_identifier(subject_id)
        return tuple(self._active_for(subject_id))
