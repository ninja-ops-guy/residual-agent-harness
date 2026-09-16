"""Relative polling wait for the browser/WebVM workbench.

The WebVM guest has produced ``OverflowError`` from ``time.sleep(0.05)`` even
with a sane wall clock.  CPython's sleep path computes an absolute monotonic
sleep deadline; a broken/oversized virtual monotonic clock can therefore make a
tiny relative sleep unrepresentable.  ``select.select`` accepts the timeout as
a relative interval and does not require that absolute deadline conversion.

This helper is intentionally browser-workbench specific.  It does not repair or
reinterpret clocks, and it does not hide failures from task/provider logic.
"""
from __future__ import annotations

import select


def pause(seconds: float = 0.05) -> None:
    """Wait for a small relative interval without using ``time.sleep``."""
    if type(seconds) not in (int, float) or not 0 <= seconds <= 1:
        raise ValueError("browser poll interval outside [0, 1]")
    select.select([], [], [], seconds)
