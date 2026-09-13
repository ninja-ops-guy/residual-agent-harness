"""Track 7: NetOps Station Module.

Implements the StationModule protocol. Registers quarantine policies,
verifiers, and brakes for network operations. Does not modify core code.
"""
from __future__ import annotations

import time
import math
from typing import Any, Callable, Optional

from ..brakes import BrakeAction, BrakeTrip
from ..core import ContractError, canonical
from ..goalspec import CheckType
from ..quarantine import Policy, ProposedAction
from ..verifier import CheckResult


class NetOpsModule:
    """First-Class Station Module for network operations.

    Parameters
    -----------
    telemetry_client:
        Object with get_current_metrics() -> dict[str, float].
        Host-registered; the module never opens network connections.
    safety_thresholds:
        dict[str, float] — metric name to soft limit.
        Hard emergency ceiling is 1.5x soft limit.
    maintenance_window_validator:
        Callable[[str], bool] — validates a maintenance receipt ID.
        Must be mechanical (no network calls). Host-registered.
    """

    name = "netops"
    version = "1.0.0"

    def __init__(self, telemetry_client: Any,
                 safety_thresholds: dict[str, float],
                 maintenance_window_validator: Optional[Callable[[str], bool]] = None,
                 permitted_devices: tuple[str, ...] = ()):
        if not hasattr(telemetry_client, "get_current_metrics"):
            raise ContractError("telemetry_client must provide get_current_metrics()")
        self._telemetry = telemetry_client
        self._thresholds = dict(safety_thresholds)
        if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in self._thresholds.values()):
            raise ContractError("telemetry thresholds must be positive finite numbers")
        self._permitted_devices = frozenset(permitted_devices)
        self._validate_receipt = maintenance_window_validator or (lambda _: False)

    # --- StationModule protocol ------------------------------------------------

    def quarantine_policies(self) -> tuple[Policy, ...]:
        return (self._maintenance_window_policy, self._topology_permission_policy)

    def verifiers(self) -> dict[str, tuple[CheckType, Callable]]:
        return {
            "telemetry_stabilization": (CheckType.MECHANICAL, self._telemetry_stabilization),
            "config_syntax_valid": (CheckType.MECHANICAL, self._config_syntax_valid),
            "bgp_adjacency_assert": (CheckType.STRUCTURAL, self._bgp_adjacency_assert),
        }

    def brakes(self) -> tuple:
        return (TelemetryAnomalyBrake(self._telemetry, self._thresholds),
                TopologyDriftBrake(self._telemetry))

    def on_run_opened(self, spec) -> None:
        pass

    def on_run_closed(self, result) -> None:
        pass

    # --- Quarantine policies ----------------------------------------------------

    def _maintenance_window_policy(self, action: ProposedAction) -> Optional[str]:
        """Deny core-tier mutations without a valid maintenance receipt."""
        tier = action.arguments.get("tier", "")
        receipt = action.arguments.get("maintenance_receipt")
        if tier == "core":
            if receipt is None:
                return "core-tier mutation requires a maintenance receipt"
            if self._validate_receipt(receipt) is not True:
                return f"invalid maintenance receipt: {receipt}"
        return None

    def _topology_permission_policy(self, action: ProposedAction) -> Optional[str]:
        """Deny actions on devices not in the permitted topology."""
        permitted = self._permitted_devices  # host scope, never proposal-supplied authority
        target = action.arguments.get("target_device", "")
        if target and target not in permitted:
            return f"device '{target}' not in permitted topology"
        return None

    # --- Verifiers ----------------------------------------------------------------

    def _telemetry_stabilization(self, candidate: Any, params: dict) -> tuple[CheckResult, str]:
        """Post-execution mechanical check: metrics stable within window."""
        window_s = params.get("evaluation_window_sec", 15)
        poll_s = params.get("poll_interval_sec", 3)
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in (window_s, poll_s)) or not 0 <= window_s <= 60 or not 0 <= poll_s <= 60:
            return CheckResult.UNKNOWN, "invalid_telemetry_window"
        t0 = time.monotonic()
        while True:
            try:
                metrics = self._telemetry.get_current_metrics()
            except Exception:
                return CheckResult.UNKNOWN, "telemetry_client_unreachable"
            for metric, limit in self._thresholds.items():
                val = metrics.get(metric)
                if type(val) not in (int, float) or not math.isfinite(val):
                    return CheckResult.UNKNOWN, "telemetry_metric_missing_or_invalid"
                if val > limit:
                    return CheckResult.FAIL, (
                        f"NetOps stabilization failed: {metric}={val} exceeded {limit}"
                    )
            remaining = window_s - (time.monotonic() - t0)
            if remaining <= 0:
                break
            time.sleep(min(max(poll_s, 0.01), remaining))
        return CheckResult.PASS, "telemetry stable throughout evaluation window"

    def _config_syntax_valid(self, candidate: Any, params: dict) -> tuple[CheckResult, str]:
        """Check that a config candidate parses correctly."""
        config_text = ""
        if isinstance(candidate, dict):
            config_text = candidate.get("config", "")
        elif isinstance(candidate, str):
            config_text = candidate
        if not config_text.strip():
            return CheckResult.UNKNOWN, "no config to validate"
        # Basic syntax checks — extend with YANG validation in production
        if config_text.count("{") != config_text.count("}"):
            return CheckResult.FAIL, "unbalanced braces in config"
        if "!!" in config_text:
            return CheckResult.FAIL, "config contains merge conflict markers"
        return CheckResult.PASS, "config syntax valid"

    def _bgp_adjacency_assert(self, candidate: Any, params: dict) -> tuple[CheckResult, str]:
        """Structural check: BGP adjacencies are established."""
        expected_peers = params.get("expected_peers", [])
        try:
            metrics = self._telemetry.get_current_metrics()
        except Exception:
            return CheckResult.UNKNOWN, "telemetry_client_unreachable"
        established = metrics.get("bgp_established_peers", [])
        missing = [p for p in expected_peers if p not in established]
        if missing:
            return CheckResult.FAIL, f"BGP peers not established: {missing}"
        return CheckResult.PASS, f"all {len(expected_peers)} BGP peers established"

    # --- Module observation helper -------------------------------------------------

    def emit_status(self, emit_fn, status: str, detail: str = "") -> None:
        if emit_fn:
            emit_fn("custom", {"event": "netops_brake_checked", "status": status, "detail": detail})


class TelemetryAnomalyBrake:
    """Emergency brake: trips when any metric exceeds 1.5x soft limit."""

    def __init__(self, telemetry_client: Any, thresholds: dict[str, float]):
        self.name = "netops_telemetry_anomaly"
        self._telemetry = telemetry_client
        self._thresholds = thresholds

    def update(self, event: dict) -> Optional[BrakeTrip]:
        try:
            metrics = self._telemetry.get_current_metrics()
        except Exception:
            return BrakeTrip(self.name, "telemetry_unavailable", "", BrakeAction.ABORT)
        for metric, limit in self._thresholds.items():
            hard = limit * 1.5
            val = metrics.get(metric)
            if type(val) not in (int, float) or not math.isfinite(val):
                return BrakeTrip(self.name, "telemetry_metric_missing_or_invalid", "", BrakeAction.ABORT)
            if val > hard:
                return BrakeTrip(
                    brake_name=self.name,
                    trip_reason=f"Emergency: {metric}={val} exceeded hard ceiling {hard}",
                    triggering_obs_hash="",
                    recommended_action=BrakeAction.ABORT,
                )
        return None

    def reset(self) -> None:
        pass


class TopologyDriftBrake:
    """Trips when observed topology differs from baseline without declared cause."""

    def __init__(self, telemetry_client: Any):
        self.name = "netops_topology_drift"
        self._telemetry = telemetry_client
        self._baseline: Optional[str] = None

    def update(self, event: dict) -> Optional[BrakeTrip]:
        if event.get("kind") == "checkpoint" and event.get("payload", {}).get("event") == "run_opened":
            # Capture baseline at run open
            try:
                topology = self._telemetry.get_current_metrics().get("topology_hash", "")
                self._baseline = topology
            except Exception:
                pass
            return None
        # Check for drift on pass transitions
        if event.get("kind") == "state.transition" and event.get("to_state") == "pass_complete":
            if self._baseline is None:
                return None
            try:
                current = self._telemetry.get_current_metrics().get("topology_hash", "")
            except Exception:
                return None
            declared = event.get("payload", {}).get("topology_change_declared", False)
            if current != self._baseline and not declared:
                return BrakeTrip(
                    brake_name=self.name,
                    trip_reason="topology drifted without declared change",
                    triggering_obs_hash="",
                    recommended_action=BrakeAction.ESCALATE,
                )
        return None

    def reset(self) -> None:
        self._baseline = None
