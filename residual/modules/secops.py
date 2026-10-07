"""Track 8: SecOps Station Module.

Implements the StationModule protocol. Registers quarantine policies,
verifiers, and brakes for security operations. Does not modify core code.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Callable, Optional

from ..brakes import BrakeAction, BrakeTrip
from ..core import ContractError
from ..goalspec import CheckType
from ..quarantine import ActionType, Policy, ProposedAction
from ..verifier import CheckResult


class SecOpsModule:
    """First-Class Station Module for security operations.

    Parameters
    -----------
    prohibited_patterns:
        List of regex strings. Compiled at construction. Applied to
        every string in ProposedAction.arguments (recursive descent).
    allowed_licenses:
        List of SPDX license identifiers permitted in dependencies.
    """

    name = "secops"
    version = "1.0.0"

    def __init__(self, prohibited_patterns: list[str], allowed_licenses: list[str]):
        self._patterns = [re.compile(p) for p in prohibited_patterns]
        self._allowed = set(allowed_licenses)

    # --- StationModule protocol ------------------------------------------------

    def quarantine_policies(self) -> tuple[Policy, ...]:
        return (
            self._secret_exfiltration_policy,
            self._dependency_disclosure_policy,
            self._prohibited_pattern_policy,
        )

    def verifiers(self) -> dict[str, tuple[CheckType, Callable]]:
        return {
            "sast_scan": (CheckType.MECHANICAL, self._sast_scan),
            "sbom_check": (CheckType.STRUCTURAL, self._sbom_check),
            "policy_as_code_eval": (CheckType.STRUCTURAL, self._policy_as_code_eval),
        }

    def brakes(self) -> tuple:
        return (VulnerabilityDeltaBrake(), SecretExposureBrake(self._patterns))

    def on_run_opened(self, spec) -> None:
        pass

    def on_run_closed(self, result) -> None:
        pass

    # --- Quarantine policies ----------------------------------------------------

    def _scan_tree(self, obj: Any) -> Optional[str]:
        """Recursive descent over arguments tree. Returns first match or None."""
        if isinstance(obj, Mapping):
            for v in obj.values():
                result = self._scan_tree(v)
                if result:
                    return result
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                result = self._scan_tree(v)
                if result:
                    return result
        elif isinstance(obj, str):
            for pattern in self._patterns:
                if pattern.search(obj):
                    return f"pattern match: {pattern.pattern[:50]}"
        return None

    def _secret_exfiltration_policy(self, action: ProposedAction) -> Optional[str]:
        """Scan arguments tree for prohibited patterns (secrets, credentials)."""
        match = self._scan_tree(action.arguments)
        if match:
            return f"potential secret exfiltration: {match}"
        return None

    def _dependency_disclosure_policy(self, action: ProposedAction) -> Optional[str]:
        """Deny actions that would disclose dependency manifests externally."""
        if action.action_type == ActionType.PROVIDER_CALL:
            payload = action.arguments.get("payload", {})
            if isinstance(payload, Mapping) and "dependencies" in payload:
                return "dependency manifest disclosure blocked"
        return None

    def _prohibited_pattern_policy(self, action: ProposedAction) -> Optional[str]:
        """General prohibited pattern scan on action name and arguments."""
        match = self._scan_tree({"name": action.name, "args": action.arguments})
        if match:
            return f"prohibited pattern: {match}"
        return None

    # --- Verifiers ----------------------------------------------------------------

    def _sast_scan(self, candidate: Any, params: dict) -> tuple[CheckResult, str]:
        """Mechanical: scan modified files for hardcoded secrets."""
        files = []
        if isinstance(candidate, dict):
            files = candidate.get("modified_files", [])
        if not files:
            return CheckResult.UNKNOWN, "no modified files to scan"
        for path in files:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                return CheckResult.UNKNOWN, f"cannot read {path}"
            if "BEGIN PRIVATE KEY" in content or "BEGIN RSA PRIVATE KEY" in content:
                return CheckResult.FAIL, f"private key block in {path}"
            if "BEGIN OPENSSH PRIVATE KEY" in content:
                return CheckResult.FAIL, f"OpenSSH private key in {path}"
            # Hardcoded credential assignment heuristic
            cred_patterns = [
                r"api_secret\s*=\s*['\"][^'\"]+['\"]",
                r"api_key\s*=\s*['\"][^'\"]+['\"]",
                r"password\s*=\s*['\"][^'\"]+['\"]",
                r"token\s*=\s*['\"][^'\"]+['\"]",
                r"secret\s*=\s*['\"][^'\"]+['\"]",
            ]
            for pat in cred_patterns:
                if re.search(pat, content):
                    return CheckResult.FAIL, f"hardcoded credential in {path}"
        return CheckResult.PASS, f"SAST clean across {len(files)} files"

    def _sbom_check(self, candidate: Any, params: dict) -> tuple[CheckResult, str]:
        """Structural: verify dependency licenses against allowed list."""
        manifest = {}
        if isinstance(candidate, dict):
            manifest = candidate.get("dependencies", {})
        if not manifest:
            return CheckResult.UNKNOWN, "no dependency manifest"
        violations = []
        for pkg, info in manifest.items():
            license_id = info.get("license", "") if isinstance(info, dict) else str(info)
            if license_id not in self._allowed:
                violations.append(f"{pkg} ({license_id})")
        if violations:
            return CheckResult.FAIL, f"license violations: {', '.join(violations)}"
        return CheckResult.PASS, f"all {len(manifest)} dependencies licensed correctly"

    def _policy_as_code_eval(self, candidate: Any, params: dict) -> tuple[CheckResult, str]:
        """Structural: evaluate config against policy bundle.

        Returns UNKNOWN (not FAIL) when policy engine is unavailable.
        """
        engine = params.get("policy_engine")
        if engine is None:
            return CheckResult.UNKNOWN, "policy_engine_unavailable"
        config = {}
        if isinstance(candidate, dict):
            config = candidate.get("config", {})
        try:
            result = engine.evaluate(config)
        except Exception:
            return CheckResult.UNKNOWN, "policy_engine_error"
        if result is True:
            return CheckResult.PASS, "policy evaluation passed"
        return CheckResult.FAIL, f"policy violation: {result}"

    # --- Module observation helper -------------------------------------------------

    def emit_status(self, emit_fn, status: str, detail: str = "") -> None:
        if emit_fn:
            emit_fn("custom", {"event": "secops_brake_checked", "status": status, "detail": detail})


class VulnerabilityDeltaBrake:
    """Trips when a pass introduces new vulnerabilities (regression detection)."""

    def __init__(self):
        self.name = "secops_vulnerability_delta"
        self._baseline: Optional[int] = None

    def update(self, event: dict) -> Optional[BrakeTrip]:
        payload = event.get("payload") or {}
        vuln_count = payload.get("vulnerability_count")
        if vuln_count is None:
            return None
        if self._baseline is None:
            self._baseline = vuln_count
            return None
        delta = vuln_count - self._baseline
        if delta > 0:
            return BrakeTrip(
                brake_name=self.name,
                trip_reason=f"agent actions introduced {delta} new vulnerabilities",
                triggering_obs_hash="",
                recommended_action=BrakeAction.ESCALATE,
            )
        return None

    def reset(self) -> None:
        self._baseline = None


class SecretExposureBrake:
    """Trips when an observed event payload contains a prohibited pattern."""

    def __init__(self, patterns: list):
        self.name = "secops_secret_exposure"
        self._patterns = patterns

    def update(self, event: dict) -> Optional[BrakeTrip]:
        payload = event.get("payload")
        if payload is None:
            return None
        text = str(payload)
        for pattern in self._patterns:
            if pattern.search(text):
                return BrakeTrip(
                    brake_name=self.name,
                    trip_reason=f"secret pattern detected in observation payload",
                    triggering_obs_hash="",
                    recommended_action=BrakeAction.ABORT,
                )
        return None

    def reset(self) -> None:
        pass
