"""Configurable compliance tagging for receipts, observations and HITL decisions.

Implements ENT2-R1: every receipt, observation, and HITL decision is
taggable with framework references (e.g. ``SOX-CC7.2``, ``GDPR-Art32``),
and the mapping is configurable per deployment.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from ..core import ContractError
from .log import ObservationEvent, validate_tag

# Sensible defaults; deployments override via TagPolicy.
DEFAULT_TAGS = {
    "receipt": ("SOX-CC7.2", "GDPR-Art32", "PCI-DSS-Req10"),
    "hitl_decision": ("SOC2-CC2.2",),
    "hitl_escalation": ("SOC2-CC2.2", "ISO27001-A.16.1"),
    "contract_violation": ("ISO27001-A.12.4",),
    "sensitive_access": ("GDPR-Art32", "HIPAA-164.312"),
    "module_install": ("SOC2-CC8.1",),
    "legal_hold": ("SOX-CC7.2",),
    "erasure": ("GDPR-Art17",),
}


@dataclass(frozen=True)
class TagPolicy:
    """Per-deployment kind-to-tags mapping. Implements ENT2-R1."""
    mapping: dict[str, tuple[str, ...]] = field(default_factory=lambda: dict(DEFAULT_TAGS))

    def __post_init__(self):
        if not isinstance(self.mapping, dict):
            raise ContractError("tag policy mapping must be a dict")
        for kind, tags in self.mapping.items():
            if not isinstance(kind, str) or not kind.strip():
                raise ContractError("tag policy kinds must be nonempty strings")
            if not isinstance(tags, (tuple, list)) or not tags:
                raise ContractError("each kind requires at least one tag")
            for tag in tags:
                validate_tag(tag)
            if len(set(tags)) != len(tags):
                raise ContractError("duplicate tags in policy")
            self.mapping[kind] = tuple(tags)

    def tags_for(self, kind: str) -> tuple[str, ...]:
        return tuple(self.mapping.get(kind, ()))


class ComplianceTagger:
    """Applies a TagPolicy to events. Implements ENT2-R1."""

    def __init__(self, policy: TagPolicy | None = None):
        self.policy = policy or TagPolicy()

    def tag(self, event: ObservationEvent, extra: tuple[str, ...] = ()) -> ObservationEvent:
        """Return a tagged copy of an event; strict on tag syntax."""
        for tag in extra:
            validate_tag(tag)
        merged = tuple(sorted(set(event.tags) | set(self.policy.tags_for(event.kind)) | set(extra)))
        return replace(event, tags=merged)
