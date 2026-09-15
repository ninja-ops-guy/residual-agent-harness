"""RUN-R5: Residual HITL/policy authoritative over provider-native behavior.

Provider engines (SDK agents, CrewAI, LangGraph, chat providers) may ship
their own autonomous loops or native HITL flags. Residual policy is the sole
authority: provider-native HITL/autonomy is disabled at dispatch and any
provider refusal/self-approval metadata is treated as advisory only — it can
never satisfy or bypass a Residual policy decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..core import ContractError
from ..engines.protocol import EngineResult

#: Metadata keys a provider may set that must never override Residual policy.
_PROVIDER_AUTHORITY_KEYS = (
    "auto_approved",
    "self_approved",
    "provider_approved",
    "hitl_satisfied",
    "policy_bypass",
    "autonomous",
)


@dataclass(frozen=True)
class PolicyDecision:
    """Residual-authoritative decision for one execution."""

    verdict: str  # "allow" | "deny" | "escalate"
    reason: str
    authority: str = "residual"

    def __post_init__(self):
        if self.verdict not in {"allow", "deny", "escalate"}:
            raise ContractError(f"invalid policy verdict: {self.verdict}")
        if self.authority != "residual":
            raise ContractError("policy authority must be residual")


class PolicyAuthority:
    """Gate that keeps Residual HITL/policy authoritative over the engine."""

    def __init__(self, policy: Mapping[str, Any] | None = None):
        self._policy = dict(policy or {})

    def sanitize_dispatch_config(self, config: Mapping[str, Any]) -> dict[str, Any]:
        """Strip provider-native autonomy/HITL settings before dispatch."""
        sanitized = dict(config)
        for key in _PROVIDER_AUTHORITY_KEYS:
            sanitized[key] = False
        for key in ("human_input", "human_input_enabled", "hitl",
                    "require_human_input", "auto_approve", "yolo"):
            if key in sanitized:
                sanitized[key] = False
        sanitized["residual_policy_authoritative"] = True
        return sanitized

    def decide(self, task_capability: str, engine_metadata: Mapping[str, Any]) -> PolicyDecision:
        """Decide from Residual policy only; provider metadata is advisory.

        Provider claims of approval/satisfaction are explicitly ignored. A
        provider refusal advisory is honored only in the fail-closed direction
        (escalate), never as an approval.
        """
        provider_claims = {k: engine_metadata.get(k) for k in _PROVIDER_AUTHORITY_KEYS
                           if engine_metadata.get(k)}
        denied = tuple(self._policy.get("deny_capabilities", ()))
        escalated = tuple(self._policy.get("escalate_capabilities", ()))
        if task_capability in denied:
            return PolicyDecision("deny", "residual_policy_deny")
        if task_capability in escalated or engine_metadata.get("sdk_refusal_advisory"):
            return PolicyDecision("escalate", "residual_policy_escalate")
        if provider_claims:
            # Logged but never authoritative.
            return PolicyDecision("allow", "residual_policy_allow_provider_claims_ignored")
        return PolicyDecision("allow", "residual_policy_allow")

    def apply(self, result: EngineResult) -> EngineResult:
        """Fail closed on provider authority leakage in an engine result."""
        metadata = dict(result.raw_metadata)
        leaked = [k for k in _PROVIDER_AUTHORITY_KEYS if metadata.get(k)]
        if leaked:
            raise ContractError(
                f"provider-native authority metadata must not enter results: {leaked}")
        metadata["residual_policy_authoritative"] = True
        return EngineResult(
            candidate=result.candidate,
            tool_calls=result.tool_calls,
            token_usage=result.token_usage,
            wall_clock_ms=result.wall_clock_ms,
            engine_trace=result.engine_trace,
            raw_metadata=metadata,
        )
