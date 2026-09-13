"""
observation_layer.hooks
=======================
Framework-agnostic instrumentation points. These are decorators/context
managers that wrap agent harness primitives (tool calls, LLM calls, agent
lifecycles) and emit standardized observations.

Design rule: instrumentation must be a no-op when the bus is absent,
and must never change the return value or raise into the wrapped code.
"""

from __future__ import annotations

import functools
import inspect
import time
from typing import Any, Callable, Optional

from .bus import ObservationBus
from .core import ObservationKind


def instrument_tool(bus: Optional[ObservationBus], tool_name: str, agent_id: Optional[str] = None):
    """Decorator for tool functions. Emits invoked/completed or invoked/failed."""
    def decorator(fn: Callable) -> Callable:
        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def asynchronous(*args, **kwargs):
                if bus is None: return await fn(*args, **kwargs)
                tags={"tool":tool_name, **({"agent":agent_id} if agent_id else {})}
                _emit(bus, ObservationKind.TOOL_INVOKED, {"tool":tool_name,"arg_count":len(args),"kwarg_count":len(kwargs)}, tags=tags, source="hooks.instrument_tool")
                start=time.perf_counter()
                try: result=await fn(*args, **kwargs)
                except Exception as error:
                    _emit(bus, ObservationKind.TOOL_FAILED, {"tool":tool_name,"error":type(error).__name__},tags=tags,source="hooks.instrument_tool")
                    raise
                _emit(bus, ObservationKind.TOOL_COMPLETED, {"tool":tool_name,"duration_ms":round((time.perf_counter()-start)*1000,3)},tags=tags,source="hooks.instrument_tool")
                return result
            return asynchronous
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if bus is None:
                return fn(*args, **kwargs)
            tags = {"tool": tool_name}
            if agent_id:
                tags["agent"] = agent_id
            _emit(bus, 
                ObservationKind.TOOL_INVOKED,
                {"tool": tool_name, "arg_count": len(args), "kwarg_count": len(kwargs)},
                tags=tags,
                source="hooks.instrument_tool",
            )
            t0 = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
            except Exception as e:
                _emit(bus, 
                    ObservationKind.TOOL_FAILED,
                    {"tool": tool_name, "error": type(e).__name__},
                    tags=tags,
                    source="hooks.instrument_tool",
                )
                raise
            dt_ms = (time.perf_counter() - t0) * 1000
            _emit(bus, 
                ObservationKind.TOOL_COMPLETED,
                {"tool": tool_name, "duration_ms": round(dt_ms, 3)},
                tags=tags,
                source="hooks.instrument_tool",
            )
            return result
        return wrapper
    return decorator


class llm_call:
    """Context manager for LLM invocations. Captures latency, token usage if present."""

    def __init__(self, bus: Optional[ObservationBus], model: str, agent_id: Optional[str] = None, capture_content: bool = False):
        self.bus = bus
        self.model = model
        self.agent_id = agent_id
        self.capture_content = capture_content
        self._t0 = None

    def __enter__(self):
        if self.bus:
            self._t0 = time.perf_counter()
            _emit(self.bus, 
                ObservationKind.LLM_REQUEST,
                {"model": self.model},
                tags={"model": self.model, **({"agent": self.agent_id} if self.agent_id else {})},
                source="hooks.llm_call",
            )
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.bus and self._t0 is not None:
            dt_ms = (time.perf_counter() - self._t0) * 1000
            if exc_type is None:
                _emit(self.bus, 
                    ObservationKind.LLM_RESPONSE,
                    {"model": self.model, "duration_ms": round(dt_ms, 3)},
                    tags={"model": self.model, **({"agent": self.agent_id} if self.agent_id else {})},
                    source="hooks.llm_call",
                )
            else:
                _emit(self.bus, 
                    ObservationKind.LLM_FAILED,
                    {"model": self.model, "error": exc_type.__name__, "duration_ms": round(dt_ms, 3)},
                    tags={"model": self.model},
                    source="hooks.llm_call",
                )
        return False  # never swallow exceptions


def emit_agent_lifecycle(bus: Optional[ObservationBus], event: str, agent_id: str, **extra):
    """One-shot emit for spawn/terminate. `event` must be 'spawned' or 'terminated'."""
    if bus is None:
        return
    if event not in {"spawned", "terminated"}:
        raise ValueError("Unknown lifecycle event")
    kind = ObservationKind.AGENT_SPAWNED if event == "spawned" else ObservationKind.AGENT_TERMINATED
    _emit(bus, kind, {"agent_id": agent_id, **extra}, tags={"agent": agent_id}, source="hooks.agent_lifecycle")


def emit_state_transition(bus: Optional[ObservationBus], from_state: str, to_state: str, reason: Optional[str] = None, **extra):
    if bus is None:
        return
    _emit(bus, 
        ObservationKind.STATE_TRANSITION,
        {"from": from_state, "to": to_state, "reason": reason, **extra},
        tags={"from": from_state, "to": to_state},
        source="hooks.state_transition",
    )


def emit_handoff(bus: Optional[ObservationBus], from_agent: str, to_agent: str, summary: Optional[str] = None, **extra):
    if bus is None:
        return
    _emit(bus, 
        ObservationKind.HANDOFF,
        {"from": from_agent, "to": to_agent, "summary": summary, **extra},
        tags={"from": from_agent, "to": to_agent},
        source="hooks.handoff",
    )


def _safe_repr(obj: Any, max_len: int = 2000) -> str:
    try:
        r = repr(obj)
        return r if len(r) <= max_len else r[:max_len] + f"...<truncated {len(r) - max_len} chars>"
    except Exception:
        return f"<unrepresentable {type(obj).__name__}>"


def _emit(bus, *args, **kwargs):
    try:
        return bus.emit(*args, **kwargs)
    except Exception:
        return None
