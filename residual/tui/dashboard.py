"""Track 2: Station TUI — read-only live dashboard.

Consumes observation bus events. Never emits, never modifies state,
never sends control signals. Crash-isolated from the LoopController.
"""
from __future__ import annotations

import threading
import time
import math
import copy
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..core import ContractError


@dataclass
class DashboardState:
    """Mutable snapshot of what the dashboard displays."""
    run_id: str = ""
    status: str = "idle"
    pass_number: int = 0
    tokens_used: int = 0
    token_budget: int = 0
    fingerprint_hits: int = 0
    quarantine_holds: int = 0
    brake_states: dict[str, str] = field(default_factory=dict)
    tasks: list[dict] = field(default_factory=list)
    netops_status: str = "NOT CONFIGURED"
    secops_status: str = "NOT OBSERVED"


class ObservationCollector:
    """Subscribes to observation events and updates DashboardState.

    This is the only write path to DashboardState. The TUI reads
    DashboardState but never writes it.
    """

    def __init__(self):
        self.state = DashboardState()
        self._lock = threading.Lock()

    def on_event(self, kind: str, payload: dict) -> None:
        with self._lock:
            if kind == "checkpoint" and payload.get("event") == "run_opened":
                self.state = DashboardState()
                self.state.run_id = payload.get("run_id", "")
                self.state.status = "running"
                self.state.token_budget = payload.get("token_budget", 0)
            elif kind == "state.transition":
                to_state = payload.get("to_state", "")
                if to_state == "pass_running":
                    self.state.pass_number = payload.get("pass_number", self.state.pass_number)
                elif to_state == "brake_tripped":
                    brake = payload.get("brake_name", "unknown")
                    self.state.brake_states[brake] = "TRIPPED"
                    if brake == "no_progress":
                        self.state.fingerprint_hits += 1
            elif kind == "custom":
                event = payload.get("event", "")
                if event == "verification_report":
                    self.state.tasks.append({
                        "pass": self.state.pass_number,
                        "result": "PASS" if payload.get("overall_pass") else "FAIL",
                    })
                elif event == "brake_decision":
                    decision = payload.get("decision", "")
                    if decision == "abort":
                        self.state.status = "aborted"
                    elif decision == "escalate":
                        self.state.status = "escalated"
                elif event == "netops_brake_checked":
                    self.state.netops_status = payload.get("status", "STABLE")
                elif event == "secops_brake_checked":
                    self.state.secops_status = payload.get("status", "CLEAN")
            elif kind == "llm.response":
                usage = payload.get("usage") or {}
                self.state.tokens_used += int(usage.get("total_tokens") or 0)
            elif kind == "tool.invoked":
                self.state.quarantine_holds += 1
            elif kind == "tool.completed":
                self.state.quarantine_holds = max(0, self.state.quarantine_holds - 1)
            elif kind == "tool.failed":
                self.state.quarantine_holds = max(0, self.state.quarantine_holds - 1)
            elif kind == "checkpoint" and payload.get("event") == "run_closed":
                outcome = payload.get("outcome", "")
                self.state.status = outcome
                self.state.tokens_used = payload.get("total_tokens", self.state.tokens_used)

    def snapshot(self):
        with self._lock:
            return copy.deepcopy(self.state)


class StationTUI:
    """Renders DashboardState to the terminal.

    Runs in a separate thread. Never blocks the execution path.
    Crash here does not affect the LoopController.
    """

    def __init__(self, collector: ObservationCollector, refresh_hz: float = 4.0):
        if type(refresh_hz) not in (int, float) or not math.isfinite(refresh_hz) or refresh_hz <= 0 or refresh_hz > 60:
            raise ContractError("refresh rate must be in (0, 60] Hz")
        self._collector = collector
        self._refresh_hz = refresh_hz
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _run(self) -> None:
        try:
            self._render_loop()
        except Exception:
            # TUI crash must never propagate
            pass

    def _render_loop(self) -> None:
        interval = 1.0 / self._refresh_hz
        while not self._stop.is_set():
            self._render()
            time.sleep(interval)

    def _render(self) -> None:
        s = self._collector.snapshot()
        lines = [
            f"=== Residual Command Station | Run: {s.run_id or '—'} | Status: {s.status.upper()} ===",
            f"Pass: {s.pass_number} | Tokens: {s.tokens_used}/{s.token_budget or '∞'}"
            f" | FP Hits: {s.fingerprint_hits}/3 | Quarantine: {s.quarantine_holds}",
            f"NetOps: {s.netops_status} | SecOps: {s.secops_status}",
        ]
        if s.brake_states:
            brake_str = " | ".join(f"{k}: {v}" for k, v in s.brake_states.items())
            lines.append(f"Brakes: {brake_str}")
        if s.tasks:
            last = s.tasks[-5:]
            lines.append("Recent: " + " → ".join(f"p{t['pass']}:{t['result']}" for t in last))
        lines.append("=" * 60)
        # In production, use rich.Live. Here we print for portability.
        print("\033[2J\033[H" + "\n".join(lines), end="", flush=True)
