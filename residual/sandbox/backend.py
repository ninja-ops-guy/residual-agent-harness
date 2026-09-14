"""SandboxBackend protocol and backend selection.

Requirement IDs (track B):
  B-R5: Every backend MUST implement start(spec) / exec(argv) / stop() and
        MUST be safe to stop() without start() and to garbage-collect after
        stop().
  B-R6: Backend selection MUST degrade gracefully: bwrap -> namespace
        launcher -> restricted subprocess. A weaker backend MUST declare its
        enforcement level so callers can refuse reduced isolation.
  B-R7: Crash containment MUST hold in every backend: nonzero exit, signal,
        and timeout are captured in SandboxResult and MUST NOT propagate.
"""
from __future__ import annotations

import enum
from typing import Protocol, runtime_checkable

from .spec import SandboxResult, SandboxSpec


class Enforcement(enum.IntEnum):
    """Isolation strength a backend can guarantee for fs/network limits."""
    KERNEL = 2        # mount/net namespaces (bwrap or namespace launcher)
    BEST_EFFORT = 1   # rlimits + validation only; fs/network not kernel-forced


@runtime_checkable
class SandboxBackend(Protocol):
    """Containment runtime for one command at a time."""

    name: str
    enforcement: Enforcement

    def start(self, spec: SandboxSpec) -> None:
        """Prepare the sandbox. MUST be idempotent for the same spec."""
        ...

    def exec(self, argv: list[str], *, stdin: str = "") -> SandboxResult:
        """Run argv once, capturing all failure modes as data."""
        ...

    def stop(self) -> None:
        """Release all resources. MUST NOT raise."""
        ...


def select_backend(*, require_kernel: bool = False) -> SandboxBackend:
    """Pick the strongest available backend (B-R6)."""
    from .bwrap import BwrapBackend
    from .subprocess_backend import SubprocessBackend

    if BwrapBackend.available():
        return BwrapBackend()
    backend = SubprocessBackend()
    if require_kernel and backend.enforcement < Enforcement.KERNEL:
        from ..core import ContractError
        raise ContractError("kernel-level sandbox isolation unavailable")
    return backend
