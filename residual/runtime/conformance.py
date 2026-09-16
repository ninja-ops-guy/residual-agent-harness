"""RUN-R9: reusable ExecutionEngine adapter conformance suite.

``check_adapter_conformance`` runs the SAME checks against any adapter so
that ≥2 adapters can be shown to satisfy the contract identically. Returns a
machine-readable :class:`ConformanceReport`; raises nothing on failed checks
so callers can assert per-check.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core import digest
from ..engines.protocol import (
    ContextAssembly,
    EngineHealth,
    EngineResult,
    ExecutionEngine,
    TaskSpec,
)


@dataclass(frozen=True)
class ConformanceReport:
    engine_name: str
    engine_version: str
    checks: tuple[tuple[str, bool], ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return all(ok for _name, ok in self.checks)

    @property
    def report_hash(self) -> str:
        return digest({
            "engine_name": self.engine_name,
            "engine_version": self.engine_version,
            "checks": list(self.checks),
        })

    def check_names(self) -> tuple[str, ...]:
        return tuple(name for name, _ok in self.checks)


def check_adapter_conformance(engine: ExecutionEngine) -> ConformanceReport:
    checks: list[tuple[str, bool]] = []

    def record(name: str, ok: bool) -> None:
        checks.append((name, bool(ok)))

    # Protocol surface.
    record("protocol_surface", isinstance(engine, ExecutionEngine))
    record("identity_non_empty",
           bool(str(getattr(engine, "name", "")).strip())
           and bool(str(getattr(engine, "version", "")).strip()))
    record("locality_declared", getattr(engine, "locality", "") in {"local", "cloud"})

    # Capability probe behavior.
    declared = getattr(engine, "_capabilities", frozenset()) or frozenset({"agent"})
    cap = sorted(declared)[0]
    record("supports_declared_capability", engine.supports(cap))
    record("rejects_undeclared_capability",
           not engine.supports("__runtime005_no_such_capability__"))

    # Health surface.
    record("health_enum", isinstance(engine.health(), EngineHealth))

    # Execution contract.
    task = TaskSpec(task_id="conformance-1", capability=cap, input={"ping": "pong"})
    result = engine.execute(task, ContextAssembly(values={"k": "v"}))
    record("execute_returns_engine_result", isinstance(result, EngineResult))
    record("candidate_present", result.candidate is not None)
    record("tool_calls_tuple", isinstance(result.tool_calls, tuple))
    record("wall_clock_non_negative", isinstance(result.wall_clock_ms, int)
           and result.wall_clock_ms >= 0)

    # Normalize round-trip.
    record("normalize_roundtrip",
           isinstance(engine.normalize(result), EngineResult))

    # Residual authority metadata present.
    record("residual_policy_authoritative_metadata",
           bool(result.raw_metadata.get("residual_policy_authoritative")))

    return ConformanceReport(engine_name=engine.name, engine_version=engine.version,
                             checks=tuple(checks))
