"""SPEC-004: Quarantine store — every action held before execution.

Design rule: no path skips the hold. No path executes without evaluation.
Denied actions are invisible to the agent but fully observed.
"""
from __future__ import annotations

import hashlib
import copy
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Protocol

from .core import ContractError, canonical, identifier, positive_int
from observation_layer.core import freeze


class ActionType(str, Enum):
    TOOL_CALL = "tool_call"
    FILE_WRITE = "file_write"
    PROVIDER_CALL = "provider_call"


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class ProposedAction:
    """What the agent wants to do."""
    action_type: str           # e.g. "tool_call", "file_write", "provider_call"
    name: str                  # tool name, file path, provider name
    arguments: dict[str, Any] = field(default_factory=dict)
    agent_id: str = "unknown"

    def __post_init__(self):
        try:
            object.__setattr__(self, "action_type", ActionType(self.action_type))
        except (ValueError, TypeError):
            raise ContractError("unknown action type") from None
        identifier(self.agent_id)
        if not isinstance(self.name, str) or not self.name:
            raise ContractError("action requires a name")
        try:
            if not isinstance(self.arguments, dict):
                raise ValueError()
            object.__setattr__(self, "arguments", freeze(self.arguments))
        except Exception:
            raise ContractError("action arguments must be canonicalizable")

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(canonical({
            "action_type": self.action_type,
            "name": self.name,
            "arguments": self.arguments,
            "agent_id": self.agent_id,
        }).encode()).hexdigest()


@dataclass(frozen=True)
class HeldAction:
    """An action in quarantine. Immutable once held."""
    action: ProposedAction
    held_at_ns: int
    hold_id: str

    @property
    def fingerprint(self) -> str:
        return self.action.fingerprint


@dataclass(frozen=True)
class ExecutedAction:
    """An action that was released and executed."""
    held: HeldAction
    executed_at_ns: int
    result: Any = None
    error: Optional[str] = None


@dataclass(frozen=True)
class DeniedAction:
    """An action that was denied. Never executed. Never shown to the agent."""
    held: HeldAction
    denied_at_ns: int
    reason: str
    policy_name: str


# Policy: (ProposedAction) -> Optional[str]
# Returns None to allow, or a denial reason string.
Policy = Callable[[ProposedAction], Optional[str]]


class QuarantineStore:
    """SPEC-004: hold, evaluate, release or deny. Append-only log."""

    def __init__(self, emit: Optional[Callable[[str, dict], None]] = None):
        self._log: list[dict] = []
        self._emit = emit
        self._counter = 0
        self._lock = threading.RLock()
        self._holds: dict[str, dict] = {}
        self._store_id = uuid.uuid4().hex

    def hold(self, action: ProposedAction) -> HeldAction:
        """SPEC-004-R1: every action enters here before execution."""
        if not isinstance(action, ProposedAction):
            raise ContractError("hold requires a validated action")
        with self._lock:
            self._counter += 1
            held = HeldAction(action, time.time_ns(), f"{self._store_id}-hold-{self._counter:08d}")
            self._holds[held.hold_id] = {"held": held, "state": "held", "decision": None}
            self._log.append({"event": "held", "hold_id": held.hold_id,
                "fingerprint": held.fingerprint, "action_type": action.action_type.value,
                "name": action.name, "agent_id": action.agent_id, "held_at_ns": held.held_at_ns})
            return held

    def _entry(self, held: HeldAction) -> dict:
        entry = self._holds.get(held.hold_id)
        if entry is None or entry["held"] is not held:
            raise ContractError("foreign or forged quarantine hold")
        return entry

    def evaluate(self, held: HeldAction, policies: tuple[Policy, ...]) -> PolicyDecision:
        """Evaluate all host policies once; errors deny, repeated evaluation is cached.

        A budget policy reserves one proposal here. It does not execute the action.
        """
        with self._lock:
            entry = self._entry(held)
            if entry["state"] not in {"held", "evaluated"}:
                raise ContractError("quarantine hold is already consumed")
            if entry["decision"] is not None:
                return entry["decision"]
            denials = []
            for policy in policies:
                try:
                    reason = policy(held.action)
                    if reason is not None and (not isinstance(reason, str) or not reason.strip()):
                        reason = "invalid_policy_result"
                except Exception:
                    reason = "policy_error"
                if reason is not None:
                    denials.append({"policy": getattr(policy, "__name__", "anonymous_policy"), "reason": reason[:1000]})
            decision = PolicyDecision.DENY if denials else PolicyDecision.ALLOW
            entry.update(state="evaluated", decision=decision)
            self._log.append({"event": "evaluated", "hold_id": held.hold_id,
                "fingerprint": held.fingerprint, "decision": decision.value, "denials": denials})
            return decision

    def release(self, held: HeldAction, executor: Callable[[ProposedAction], Any], *, raise_errors: bool = False) -> ExecutedAction:
        """SPEC-004-R5: release and execute. Result is observed."""
        with self._lock:
            entry = self._entry(held)
            if entry["state"] != "evaluated" or entry["decision"] != PolicyDecision.ALLOW:
                raise ContractError("release requires an unconsumed, allowed evaluation")
            # Consume before invoking host code, including concurrent or reentrant release.
            entry["state"] = "executing"
        caught = None
        try:
            result = executor(held.action)
            error = None
        except Exception as exc:
            caught = exc
            result = None
            error = type(exc).__name__
        executed = ExecutedAction(
            held=held,
            executed_at_ns=time.time_ns(),
            result=result,
            error=error,
        )
        with self._lock:
            entry["state"] = "executed"
            self._log.append({"event": "executed", "hold_id": held.hold_id,
                "fingerprint": held.fingerprint, "executed_at_ns": executed.executed_at_ns, "error": error})
        if self._emit:
            # Emitted as tool.completed / tool.failed via the caller's emit bridge.
            self._emit("action_executed", {
                "hold_id": held.hold_id,
                "fingerprint": held.fingerprint,
                "action_type": held.action.action_type,
                "name": held.action.name,
                "error": error,
            })
        if caught is not None and raise_errors:
            raise caught
        return executed

    def deny(self, held: HeldAction, reason: str, policy_name: str) -> DeniedAction:
        """SPEC-004-R3/R4: deny silently to agent, observe fully."""
        if not isinstance(reason, str) or not reason.strip():
            raise ContractError("denial requires a reason")
        with self._lock:
            entry = self._entry(held)
            if entry["state"] != "evaluated" or entry["decision"] != PolicyDecision.DENY:
                raise ContractError("deny requires an unconsumed denied evaluation")
            entry["state"] = "denied"
        denied = DeniedAction(
            held=held,
            denied_at_ns=time.time_ns(),
            reason=reason,
            policy_name=policy_name,
        )
        with self._lock:
            self._log.append({"event": "denied", "hold_id": held.hold_id,
                "fingerprint": held.fingerprint, "denied_at_ns": denied.denied_at_ns,
                "reason": reason, "policy_name": policy_name})
        if self._emit:
            self._emit("action_denied", {
                "hold_id": held.hold_id,
                "fingerprint": held.fingerprint,
                "action_type": held.action.action_type,
                "name": held.action.name,
                "reason": reason,
                "policy_name": policy_name,
            })
        return denied

    def log(self) -> tuple[dict, ...]:
        """SPEC-004-R6: append-only log, queryable."""
        with self._lock:
            return tuple(copy.deepcopy(self._log))

    def query(self, fingerprint: str) -> tuple[dict, ...]:
        """All log entries for a given action fingerprint."""
        return tuple(e for e in self.log() if e.get("fingerprint") == fingerprint)


# --- Built-in policies -------------------------------------------------------

def denylist_policy(*forbidden_names: str) -> Policy:
    """Deny actions whose name appears in the forbidden list."""
    forbidden = set(forbidden_names)
    def _policy(action: ProposedAction) -> Optional[str]:
        if action.name in forbidden:
            return f"action '{action.name}' is on the denylist"
        return None
    _policy.__name__ = "denylist_policy"
    return _policy


def path_traversal_policy(action: ProposedAction) -> Optional[str]:
    """Reject lexical path escapes. The executor must also check resolved symlinks."""
    if action.action_type != "file_write":
        return None
    path = action.arguments.get("path", "")
    if not isinstance(path, str) or not path or "\x00" in path:
        return "file_write path must be a string"
    parts = path.replace("\\", "/").split("/")
    if ".." in parts or path.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", path):
        return "path escapes workspace"
    return None


def budget_policy(max_actions: int) -> Policy:
    """Reserve one slot per evaluated proposal, including denied proposals."""
    positive_int(max_actions, "max_actions", allow_zero=True)
    state = {"count": 0}
    lock = threading.Lock()
    def _policy(action: ProposedAction) -> Optional[str]:
        with lock:
            state["count"] += 1
            if state["count"] > max_actions:
                return f"action budget exhausted ({max_actions})"
            return None
    _policy.__name__ = "budget_policy"
    return _policy
