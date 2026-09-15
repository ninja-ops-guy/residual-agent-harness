"""Authoritative ownership registry (DSM-R1).

Each distributed-state domain has exactly one authoritative writer role.
Writes submitted by any other role are rejected before they reach the
journal, so ownership is enforced mechanically rather than by convention.
"""
from __future__ import annotations

from residual.core import ContractError

# domain -> authoritative writer role
DOMAINS = {
    "task.lease": "scheduler",
    "receipt.publication": "verifier",
    "integration.intent": "integrator",
    "task.terminal": "orchestrator",
}

# Allowed transitions for the terminal task state domain. Terminal states are
# absorbing: no further transition may be accepted once an entity is terminal.
TERMINAL_TRANSITIONS = {
    None: {"running", "succeeded", "failed", "rejected", "unknown"},
    "running": {"succeeded", "failed", "rejected", "unknown"},
    "succeeded": set(),
    "failed": set(),
    "rejected": set(),
    "unknown": set(),
}
TERMINAL_STATES = {"succeeded", "failed", "rejected", "unknown"}


class OwnershipRegistry:
    """Maps state domains to their single authoritative writer role."""

    def __init__(self, mapping=None):
        self._mapping = dict(mapping or DOMAINS)

    def owner_of(self, domain):
        try:
            return self._mapping[domain]
        except KeyError:
            raise ContractError(f"unknown state domain: {domain!r}")

    def check_writer(self, domain, writer):
        """Fail closed unless ``writer`` is the authoritative owner."""
        owner = self.owner_of(domain)
        if writer != owner:
            raise ContractError(
                f"writer {writer!r} is not authoritative for domain {domain!r} "
                f"(owner: {owner!r})"
            )
        return owner

    def domains(self):
        return dict(self._mapping)


_REGISTRY = OwnershipRegistry()


def owner_of(domain):
    return _REGISTRY.owner_of(domain)
