"""Browser/CLI workbench adapters over the existing RESIDUAL harness.

This package does not replace Factory, the M4 integrator, sandbox policy, or
Station authority.
"""

from .ax_research import (
    AXExperiment,
    AXResearchBench,
    AXTask,
    AXWorkspace,
    FaultInjection,
    FaultKind,
    Invariant,
)

__all__ = [
    "AXExperiment",
    "AXResearchBench",
    "AXTask",
    "AXWorkspace",
    "FaultInjection",
    "FaultKind",
    "Invariant",
]
