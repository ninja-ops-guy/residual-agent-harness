"""Track D: universal side-effect gateway over the quarantine store.

Requirement IDs (RFC 2119):
- D-R4: EVERY mutating action MUST pass through ``SideEffectGateway.execute``;
  the gateway MUST route it through the SPEC-004 quarantine hold/evaluate/
  release-or-deny cycle. The gateway exposes no other execution path.
- D-R5: Registration is allowlist-only: an intent whose (action_kind, target)
  pair has no registered executor MUST be denied (deny-by-default) and the
  denial MUST be observed in the quarantine log.
- D-R6: An intent that is IRREVERSIBLE or whose blast radius is SYSTEM MUST
  additionally satisfy the host approval policy before release; without an
  approval verifier it MUST fail closed.
- D-R7: Executors are invoked exactly once per allowed hold; a consumed hold
  MUST NOT be reusable (enforced by the quarantine store).
"""
from __future__ import annotations

import fnmatch
import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional

from ..core import ContractError
from ..quarantine import (
    PolicyDecision,
    ProposedAction,
    QuarantineStore,
)
from .intents import ActionKind, BlastRadius, Reversibility, SideEffectIntent

Executor = Callable[[SideEffectIntent], Any]
ApprovalVerifier = Callable[[SideEffectIntent], bool]

_KIND_TO_QUARANTINE_TYPE = {
    ActionKind.FILE_WRITE: "file_write",
    ActionKind.FILE_DELETE: "file_write",
    ActionKind.PROCESS_SPAWN: "tool_call",
    ActionKind.NETWORK_EGRESS: "tool_call",
    ActionKind.CONFIG_CHANGE: "config_change",
    ActionKind.PROVIDER_CALL: "provider_call",
    ActionKind.TOOL_CALL: "tool_call",
    ActionKind.STATE_MUTATION: "config_change",
}


@dataclass(frozen=True)
class GatewayResult:
    """Observed outcome of one gateway submission. Never raises for denials."""

    intent: SideEffectIntent
    status: str                    # "executed" | "denied" | "approval_required"
    result: Any = None
    error: Optional[str] = None
    denial_reason: Optional[str] = None
    hold_id: Optional[str] = None


class SideEffectGateway:
    """D-R4: the single choke point for every mutating action.

    Executors are held privately and are reachable only through the
    quarantine release path. There is deliberately no public method that
    invokes an executor directly.
    """

    def __init__(self, quarantine: Optional[QuarantineStore] = None, *,
                 emit: Optional[Callable[[str, dict], None]] = None,
                 approval_verifier: Optional[ApprovalVerifier] = None):
        if approval_verifier is not None and not callable(approval_verifier):
            raise ContractError("approval verifier must be a host callable")
        self._quarantine = quarantine if quarantine is not None else QuarantineStore(emit=emit)
        self._executors: dict[tuple[ActionKind, str], Executor] = {}
        self._approval_verifier = approval_verifier
        self._lock = threading.RLock()

    def register(self, action_kind: ActionKind, target_pattern: str, executor: Executor) -> None:
        """Allowlist one (kind, target glob) → executor. The only way an intent
        can ever become executable."""
        try:
            kind = ActionKind(action_kind)
        except (ValueError, TypeError):
            raise ContractError("unknown action kind") from None
        if not isinstance(target_pattern, str) or not target_pattern.strip():
            raise ContractError("target pattern is required")
        if not callable(executor):
            raise ContractError("executor must be callable")
        with self._lock:
            self._executors[(kind, target_pattern)] = executor

    def _resolve(self, intent: SideEffectIntent) -> Optional[Executor]:
        with self._lock:
            entries = tuple(self._executors.items())
        for (kind, pattern), executor in entries:
            if kind is intent.action_kind and fnmatch.fnmatchcase(intent.target, pattern):
                return executor
        return None

    def _to_action(self, intent: SideEffectIntent) -> ProposedAction:
        return ProposedAction(
            action_type=_KIND_TO_QUARANTINE_TYPE[intent.action_kind],
            name=f"{intent.action_kind.value}:{intent.target}",
            arguments={
                "intent_id": intent.intent_id,
                "target": intent.target,
                "reversibility": intent.reversibility.value,
                "blast_radius": intent.blast_radius.value,
                "parameters": intent.parameters,
            },
            agent_id=intent.agent_id,
        )

    def execute(self, intent: SideEffectIntent, *, raise_errors: bool = False) -> GatewayResult:
        """D-R4/D-R5/D-R6: hold, evaluate, release-or-deny. Deny-by-default."""
        if not isinstance(intent, SideEffectIntent):
            raise ContractError("gateway only executes validated SideEffectIntents")
        executor = self._resolve(intent)

        def registration_policy(_action):
            if executor is None:
                return (f"deny-by-default: no registered executor for "
                        f"{intent.action_kind.value}:{intent.target}")
            return None

        def approval_policy(_action):
            if intent.reversibility is Reversibility.IRREVERSIBLE or intent.blast_radius is BlastRadius.SYSTEM:
                if self._approval_verifier is None:
                    return "irreversible/system intent requires a host approval verifier"
                try:
                    if self._approval_verifier(intent) is not True:
                        return "host approval verifier rejected the intent"
                except Exception:
                    return "approval verifier error"
            return None

        held = self._quarantine.hold(self._to_action(intent))
        decision = self._quarantine.evaluate(held, (registration_policy, approval_policy))
        if decision is not PolicyDecision.ALLOW:
            evaluated = [e for e in self._quarantine.log()
                         if e.get("event") == "evaluated" and e.get("hold_id") == held.hold_id]
            reasons = [d["reason"] for e in evaluated for d in e.get("denials", [])]
            denied = self._quarantine.deny(
                held,
                reason="; ".join(reasons) or "policy denial",
                policy_name="side_effect_gateway",
            )
            return GatewayResult(intent=intent, status="denied",
                                 denial_reason=denied.reason, hold_id=held.hold_id)
        executed = self._quarantine.release(
            held, lambda _action: executor(intent), raise_errors=raise_errors)
        return GatewayResult(intent=intent, status="executed", result=executed.result,
                             error=executed.error, hold_id=held.hold_id)

    def audit_log(self) -> tuple[dict, ...]:
        """D-R5: every hold, evaluation, execution, and denial is observable."""
        return self._quarantine.log()
