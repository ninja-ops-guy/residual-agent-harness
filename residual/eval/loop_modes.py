from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from residual.core import Obligation


class LoopMode(str, Enum):
    SINGLE = "single"
    NAIVE = "naive"
    HOST_OWNED = "host-owned"
    ADAPTIVE = "adaptive"


@dataclass(frozen=True)
class NaiveIterationResult:
    worker_reports_done: bool


class NaiveFactoryAdapter(Protocol):
    def run_all(self, obligations: tuple[Obligation, ...]) -> NaiveIterationResult: ...


class NaiveLoopRunner:
    """Frozen experimental baseline: worker self-report owns completion.

    This intentionally re-runs the full original obligation set every iteration.
    It is not used by production M5 control flow.
    """

    def __init__(self, factory: NaiveFactoryAdapter):
        self.factory = factory

    def run(self, obligations: tuple[Obligation, ...], *, max_iterations: int) -> bool:
        if max_iterations < 1:
            raise ValueError("max_iterations must be positive")
        for _ in range(max_iterations):
            result = self.factory.run_all(obligations)
            if result.worker_reports_done:
                return True
        return False
