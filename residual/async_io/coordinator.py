"""Run-scoped cancellation for asynchronous periphery components."""
from __future__ import annotations

import asyncio
import threading
from typing import Any


class AsyncRunCoordinator:
    """Cancels registered async I/O when a run aborts without blocking the core.

    Registered components expose ``async cancel(timeout_s=5.0)``. Cancellation is
    scheduled onto the owning event loop when supplied; otherwise it runs in a
    short-lived daemon thread. Each component gets at most five seconds.
    """

    def __init__(self, *, loop: asyncio.AbstractEventLoop | None = None):
        self._loop = loop
        self._components: list[Any] = []
        self._lock = threading.Lock()

    def register(self, component: Any) -> Any:
        cancel = getattr(component, "cancel", None)
        if cancel is None or not asyncio.iscoroutinefunction(cancel):
            raise TypeError("async component must expose async cancel(timeout_s=...)")
        with self._lock:
            if component not in self._components:
                self._components.append(component)
        return component

    def bind(self, lifecycle_bus):
        lifecycle_bus.subscribe("run_closed", self._on_run_closed)
        return self

    async def cancel_all(self) -> None:
        with self._lock:
            components = tuple(self._components)
        if not components:
            return

        async def cancel_one(component):
            try:
                await asyncio.wait_for(component.cancel(timeout_s=5.0), timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
                return

        await asyncio.gather(*(cancel_one(component) for component in components))

    def _on_run_closed(self, event: str, payload: dict) -> None:
        if payload.get("outcome") != "aborted":
            return
        coroutine = self.cancel_all()
        loop = self._loop
        if loop is not None and loop.is_running():
            asyncio.run_coroutine_threadsafe(coroutine, loop)
            return

        def runner():
            try:
                asyncio.run(coroutine)
            except Exception:
                pass

        threading.Thread(target=runner, name="residual-async-cancel", daemon=True).start()
