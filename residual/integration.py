"""Integration layer: quarantine + observation bridge for the existing engine.

This module connects the new loop-layer components (QuarantineStore,
observation emission) to the existing engine without modifying engine.py.
Pass QuarantinedProvider to the engine to hold provider calls for evaluation.
File paths are still enforced by the station workspace executor.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from .core import ContractError
from .quarantine import (
    Policy, PolicyDecision, ProposedAction, QuarantineStore, budget_policy, denylist_policy,
    path_traversal_policy,
)
from .providers import Provider


class QuarantinedProvider:
    """Wraps any Provider so all generate() calls pass through quarantine.

    Usage:
        quarantine = QuarantineStore(emit=emit_fn)
        safe_provider = QuarantinedProvider(raw_provider, quarantine, policies)
        # pass safe_provider to Harness instead of raw_provider
    """

    def __init__(self, inner: Provider, store: QuarantineStore,
                 policies: tuple[Policy, ...] = ()):
        self._inner = inner
        self._store = store
        self._policies = policies
        # Mirror the Provider interface
        self.name = inner.name
        self.placement = inner.placement
        self.prices = inner.prices

    def payload(self, packet: dict, max_output_tokens: int) -> dict:
        return self._inner.payload(packet, max_output_tokens)

    def wire_size(self, packet: dict, max_output_tokens: int) -> int:
        return self._inner.wire_size(packet, max_output_tokens)

    def generate(self, packet: dict, max_output_tokens: int):
        """Hold → evaluate → release or deny."""
        from .core import canonical, strict_json, positive_int
        # The held digest and dispatched body bind the same detached snapshot.
        packet = strict_json(canonical(packet))
        positive_int(max_output_tokens, "max_output_tokens")
        action = ProposedAction(
            action_type="provider_call",
            name=self._inner.name,
            arguments={
                "packet_sha256": _packet_hash(packet),
                "max_output_tokens": max_output_tokens,
            },
        )
        held = self._store.hold(action)
        decision = self._store.evaluate(held, self._policies)
        if decision == PolicyDecision.DENY:
            self._store.deny(held, reason="policy_denied", policy_name="quarantine")
            # Raise a safe error code; the engine handles this as a provider failure.
            from .providers import ProviderError
            raise ProviderError("action_denied_by_policy")
        return self._store.release(held, lambda _: self._inner.generate(packet, max_output_tokens), raise_errors=True).result


def _packet_hash(packet: dict) -> str:
    from .core import digest
    return digest(packet)


def default_policies(max_provider_calls: int = 100) -> tuple[Policy, ...]:
    """Sensible default policy set for provider call quarantine."""
    return (
        denylist_policy(),           # empty denylist; extend at deployment
        budget_policy(max_provider_calls),
    )
