"""SoakTestReport: contents per N9-R10, HMAC-signed per N9-R11.

The report payload is canonical JSON; the signature is HMAC-SHA256 over
that canonical payload using the Station's identity key. Verification
recomputes the HMAC and compares with ``hmac.compare_digest`` so any
modification of the payload invalidates the signature.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional

from .metrics import SoakMetrics

SCHEMA_VERSION = "residual.soak.report.v1"


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_payload(payload: Dict[str, Any], station_key: bytes) -> str:
    return hmac.new(station_key, _canonical(payload), hashlib.sha256).hexdigest()


def sign_report(report: Dict[str, Any], station_key: bytes) -> Dict[str, Any]:
    """Return a signed report envelope: {payload, signature, key_id}."""
    payload = {k: v for k, v in report.items() if k not in ("signature", "key_id")}
    return {
        "payload": payload,
        "signature": sign_payload(payload, station_key),
        "key_id": hashlib.sha256(station_key).hexdigest()[:16],
    }


def verify_report(signed: Dict[str, Any], station_key: bytes) -> bool:
    """Verify an HMAC-signed report envelope."""
    try:
        payload = signed["payload"]
        signature = signed["signature"]
    except (KeyError, TypeError):
        return False
    expected = sign_payload(payload, station_key)
    return hmac.compare_digest(expected, signature)


class SoakTestReport:
    """Builds the N9-R10 report from aggregated soak metrics."""

    def __init__(self, metrics: SoakMetrics, days_completed: int,
                 red_team_results: Optional[List[Dict[str, Any]]] = None):
        self.metrics = metrics
        self.days_completed = days_completed
        self.red_team_results = list(red_team_results or [])

    def build(self) -> Dict[str, Any]:
        m = self.metrics
        checks = m.target_checks()
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at_epoch": int(time.time()),
            "days_completed": self.days_completed,
            "totals": {
                "tasks_executed": m.tasks_executed,
                "accepted": m.accepted,
                "rejected": m.rejected,
                "escalated": m.escalated,
                "unhandled_exceptions": m.unhandled_exceptions,
            },
            "rates": m.to_dict()["rates"],
            "targets": checks,
            "all_targets_passed": all(c["passed"] for c in checks.values()),
            "red_team": {
                "exercises": len({r.get("exercise") for r in self.red_team_results}) if self.red_team_results else 0,
                "attempts": self.red_team_results,
                "blocked": sum(1 for r in self.red_team_results if r.get("blocked")),
                "succeeded": sum(1 for r in self.red_team_results if not r.get("blocked")),
                "all_receipted": all(r.get("receipt_id") for r in self.red_team_results),
            },
        }

    def build_signed(self, station_key: bytes) -> Dict[str, Any]:
        return sign_report(self.build(), station_key)

    @staticmethod
    def verify(signed: Dict[str, Any], station_key: bytes) -> bool:
        return verify_report(signed, station_key)
