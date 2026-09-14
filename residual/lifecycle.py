"""Crash-isolated lifecycle fan-out for runtime modules.

The loop remains authoritative. Subscribers observe detached payload copies and
cannot veto or mutate control flow.
"""
from __future__ import annotations

import copy
from collections import defaultdict
from dataclasses import dataclass
from threading import RLock
from typing import Callable


class ModuleLifecycleBus:
    def __init__(self, *, include_metrics: bool = True):
        self._handlers = defaultdict(list)
        self._lock = RLock()
        self._handler_failures = 0
        if include_metrics:
            from .observability import DEFAULT_BRIDGE
            self.subscribe("*", DEFAULT_BRIDGE)

    @property
    def handler_failures(self):
        with self._lock:
            return self._handler_failures

    def subscribe(self, event, handler):
        if not isinstance(event, str) or not event or not callable(handler):
            raise TypeError("lifecycle subscriptions require an event name and callable handler")
        with self._lock:
            if handler not in self._handlers[event]:
                self._handlers[event].append(handler)

    def unsubscribe(self, event, handler):
        with self._lock:
            if handler in self._handlers.get(event, ()):
                self._handlers[event].remove(handler)

    def emit(self, event, payload):
        if not isinstance(payload, dict):
            raise TypeError("lifecycle payload must be a dict")
        with self._lock:
            handlers = tuple(self._handlers.get(event, ())) + (() if event == "*" else tuple(self._handlers.get("*", ())))
        for handler in handlers:
            try:
                handler(event, copy.deepcopy(payload))
            except Exception:
                # Diagnostics must never become authority over the run.
                with self._lock:
                    self._handler_failures += 1


@dataclass
class LifecycleBinding:
    """A detachable group of lifecycle subscriptions."""
    bus: ModuleLifecycleBus
    handlers: tuple[tuple[str, Callable], ...]

    cleanup: Callable | None = None

    def close(self):
        for event, handler in self.handlers:
            self.bus.unsubscribe(event, handler)
        if self.cleanup is not None:
            cleanup, self.cleanup = self.cleanup, None
            cleanup()


def bind_trajectory(bus: ModuleLifecycleBus, recorder, *, publish=None) -> LifecycleBinding:
    """Automatically record a structural trajectory when a run closes."""
    from .core import digest
    from .trajectory import TrajectoryStep

    steps_by_run: dict[str, list[TrajectoryStep]] = {}

    def on_open(_event, payload):
        steps_by_run[payload.get("run_id", "")] = []

    def on_custom(_event, payload):
        if payload.get("event") != "check_evaluated":
            return
        run_id = payload.get("run_id", "")
        steps = steps_by_run.setdefault(run_id, [])
        steps.append(TrajectoryStep(
            len(steps) + 1,
            payload.get("check_name", "unknown"),
            digest({"check": payload.get("check_name"), "type": payload.get("check_type")}),
            payload.get("result", "unknown"),
            float(payload.get("duration_ms", 0.0) or 0.0),
        ))

    def on_close(_event, payload):
        result = payload.get("result")
        if result is None:
            return
        trajectory = recorder.record(
            result.spec_hash,
            steps_by_run.pop(result.run_id, []),
            list(result.tripped_brakes),
            result.outcome.value,
        )
        if publish:
            publish(trajectory)

    handlers = (("run_opened", on_open), ("custom", on_custom), ("run_closed", on_close))
    for event, handler in handlers:
        bus.subscribe(event, handler)
    return LifecycleBinding(bus, handlers)


def bind_memory(bus: ModuleLifecycleBus, store, receipt_resolver: Callable, *, publish=None) -> LifecycleBinding:
    """Index host-validated receipts on successful run closure only.

    ``receipt_resolver(result)`` returns ``(description, receipt, value)`` tuples.
    The resolver is host-owned because the LoopController itself does not grant
    receipt authority to an execution engine.
    """
    from .core import ContractError, digest
    from .loop import RunOutcome
    from .receipts import StationReceipt

    def on_close(_event, payload):
        result = payload.get("result")
        if result is None or result.outcome != RunOutcome.SUCCESS:
            return
        for description, receipt, value in receipt_resolver(result):
            if (not isinstance(receipt, StationReceipt)
                    or receipt.verdict.value != "pass"
                    or receipt.value_hash != digest(value)):
                raise ContractError("memory requires a bound passing host receipt")
            entry = store.index(description, receipt.receipt_hash,
                {"receipt": receipt.to_dict(), "value": value}, receipt.verifier_revision)
            if publish:
                publish(entry)

    handlers = (("run_closed", on_close),)
    bus.subscribe("run_closed", on_close)
    return LifecycleBinding(bus, handlers)


def bind_tui(bus: ModuleLifecycleBus, collector, tui=None) -> LifecycleBinding:
    """Subscribe the dashboard collector to every observation and start its TUI thread."""
    def on_event(event, payload):
        collector.on_event(event, payload)

    bus.subscribe("*", on_event)
    if tui is not None:
        tui.start()
    return LifecycleBinding(bus, (("*", on_event),), tui.stop if tui is not None else None)
