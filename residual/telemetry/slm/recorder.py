"""SLM economic telemetry recorder (EXP-M6-SLM / SLM-06 pre-freeze instrumentation).

Captures per-model-call economics and per-routing-decision context as JSONL
events conforming to ``telemetry.schema.json`` (schema_version
``slm-telemetry-v0``), with field names aligned to the frozen evaluation
protocol (eval-protocol-v1.0.0) and ``slm-observation-v0``.

Design rules (frozen-protocol aligned):
- Config-gated and fail-open for operation: telemetry NEVER blocks an
  authoritative path (routing, provider calls, escalation). Every
  degradation is recorded in ``degradations`` and emitted as a
  ``telemetry_degradation`` event.
- Counterfactual costs are ALWAYS emitted with ``estimate: true`` and are
  never reported as observed savings (eval-protocol §6).
- Unknown stays unknown: unmeasurable cost/energy fields are null, never
  imputed (eval-protocol §8); nulls are flagged via degradation events.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

SLM_TELEMETRY_SCHEMA_VERSION = "slm-telemetry-v0"
PRICE_TABLE_VERSION_DEFAULT = "slm-prices-v2026.09"

# Frozen metric names from EVALUATION-PROTOCOL.md (eval-protocol-v1.0.0).
FROZEN_METRIC_NAMES = (
    "vmsr", "fner", "avr", "frontier_calls_avoided", "uer",
    "operator_active_minutes", "latency", "schema_invalid_rate",
    "ece", "brier", "throughput", "vsms_per_dollar", "vsms_per_watt",
)

_DEFAULT_PRICE_TABLE = {
    "price_table_version": PRICE_TABLE_VERSION_DEFAULT,
    "price_source": "pinned-program-table",
    "price_date": "2026-09-20",
    "models": {
        # USD per 1M tokens: [input, output]
        "gpt-4o": {"input_usd_per_1m": 2.50, "output_usd_per_1m": 10.00, "class": "frontier"},
        "claude-sonnet-4": {"input_usd_per_1m": 3.00, "output_usd_per_1m": 15.00, "class": "frontier"},
        "ollama-local": {"input_usd_per_1m": 0.0, "output_usd_per_1m": 0.0, "class": "local"},
    },
}


@dataclass(frozen=True)
class TelemetryConfig:
    """Config gate. ``enabled=False`` makes every recorder call a no-op."""
    enabled: bool = False
    output_path: Optional[str] = None          # JSONL sink; None -> in-memory only
    sample_power: bool = True                  # attempt GPU power sampling
    price_table_path: Optional[str] = None     # pinned price table override
    run_id: Optional[str] = None


class PriceTable:
    """Pinned, versioned per-model price table. Fail-closed on lookup:
    unknown models yield no price (cost recorded as null + degradation)."""

    def __init__(self, table: Optional[dict] = None):
        table = table or _DEFAULT_PRICE_TABLE
        self.version = table.get("price_table_version", PRICE_TABLE_VERSION_DEFAULT)
        self.source = table.get("price_source", "unknown")
        self.date = table.get("price_date", "unknown")
        self._models = dict(table.get("models", {}))

    @classmethod
    def from_path(cls, path: str) -> "PriceTable":
        with open(path, "r", encoding="utf-8") as fh:
            return cls(json.load(fh))

    def lookup(self, model: str) -> Optional[dict]:
        return self._models.get(model)

    def cost_usd(self, model: str, tokens_in: int, tokens_out: int) -> Optional[float]:
        entry = self.lookup(model)
        if entry is None:
            return None
        return (tokens_in * entry["input_usd_per_1m"]
                + tokens_out * entry["output_usd_per_1m"]) / 1_000_000.0

    def model_class(self, model: str) -> Optional[str]:
        entry = self.lookup(model)
        return entry.get("class") if entry else None


class Recorder:
    """Fail-open SLM telemetry recorder. Public methods never raise."""

    def __init__(self, config: Optional[TelemetryConfig] = None, *,
                 clock: Callable[[], float] = time.monotonic,
                 wall_clock: Callable[[], float] = time.time,
                 power_sampler: Any = None,
                 sink: Any = None):
        self.config = config or TelemetryConfig()
        self.clock = clock
        self.wall_clock = wall_clock
        self.power_sampler = power_sampler
        self.run_id = self.config.run_id or uuid.uuid4().hex
        self.events: list[dict] = []            # in-memory evidence buffer
        self.degradations: list[dict] = []      # every degradation, logged
        self.model_call_counts: dict[str, int] = {}
        self.frontier_call_count = 0
        self._sink = sink
        self._fh = None
        self._price_table = None
        if self.config.enabled and self.config.output_path and sink is None:
            try:
                self._fh = open(self.config.output_path, "a", encoding="utf-8")
            except OSError as exc:
                self._degrade("sink_open_failed", repr(exc))

    # ------------------------------------------------------------------
    @property
    def price_table(self) -> PriceTable:
        if self._price_table is None:
            if self.config.price_table_path:
                try:
                    self._price_table = PriceTable.from_path(self.config.price_table_path)
                except Exception as exc:  # fail-open: fall back to pinned default
                    self._degrade("price_table_load_failed", repr(exc))
                    self._price_table = PriceTable()
            else:
                self._price_table = PriceTable()
        return self._price_table

    def _degrade(self, reason: str, detail: str = "") -> None:
        entry = {"reason": reason, "detail": detail, "ts": self.wall_clock()}
        self.degradations.append(entry)
        self._write({"kind": "telemetry_degradation",
                     "schema_version": SLM_TELEMETRY_SCHEMA_VERSION,
                     "run_id": self.run_id, **entry})

    def _write(self, event: dict) -> None:
        self.events.append(event)
        try:
            line = json.dumps(event, sort_keys=True, allow_nan=False)
            if self._sink is not None:
                self._sink.write(line + "\n")
            elif self._fh is not None:
                self._fh.write(line + "\n")
                self._fh.flush()
        except Exception as exc:
            # Last-resort: record the degradation in memory only; never raise.
            self.degradations.append({"reason": "sink_write_failed",
                                      "detail": repr(exc), "ts": self.wall_clock()})

    def close(self) -> None:
        try:
            if self._fh is not None:
                self._fh.close()
        except Exception:
            pass
        self._fh = None

    # ------------------------------------------------------------------
    def _sample_power_w(self) -> Optional[float]:
        if not self.config.sample_power or self.power_sampler is None:
            return None
        try:
            watts = self.power_sampler.sample_watts()
        except Exception as exc:
            self._degrade("power_sample_failed", repr(exc))
            return None
        if watts is None:
            self._degrade("power_unmeasurable", "sampler returned None")
        return watts

    def record_inference_call(self, *, model: str, provider: str = "unknown",
                              worker_id: Optional[str] = None,
                              tokens_in: int = 0, tokens_out: int = 0,
                              latency_ms: Optional[float] = None,
                              decision_id: Optional[str] = None,
                              verification_status: str = "unknown",
                              schema_valid: Optional[bool] = None,
                              confidence: Optional[float] = None,
                              frontier_call: Optional[bool] = None) -> dict:
        """Record one realized model call. Cost is realized (measured tokens x
        pinned price); energy only where measurable; both null when unknown."""
        if not self.config.enabled:
            return {}
        try:
            cost = self.price_table.cost_usd(model, tokens_in, tokens_out)
            if cost is None:
                self._degrade("unpriced_model", model)
            watts = self._sample_power_w()
            energy_wh = None
            if watts is not None and latency_ms is not None:
                energy_wh = watts * (latency_ms / 3_600_000.0)
            if frontier_call is None:
                frontier_call = self.price_table.model_class(model) == "frontier"
            self.model_call_counts[model] = self.model_call_counts.get(model, 0) + 1
            if frontier_call:
                self.frontier_call_count += 1
            event = {
                "kind": "inference_call",
                "schema_version": SLM_TELEMETRY_SCHEMA_VERSION,
                "run_id": self.run_id,
                "decision_id": decision_id,
                "ts": self.wall_clock(),
                "worker_id": worker_id,
                "model": model,
                "provider": provider,
                "tokens": {"in": int(tokens_in), "out": int(tokens_out)},
                "cost": {
                    # names aligned to slm-observation-v0 cost block
                    "inference_usd": cost,
                    "energy_wh": energy_wh,
                    "latency_ms": latency_ms,
                    "frontier_calls": 1 if frontier_call else 0,
                },
                "power_w": watts,
                "energy_measurable": energy_wh is not None,
                "price_table_version": self.price_table.version,
                "price_source": self.price_table.source,
                "price_date": self.price_table.date,
                "verification": {"status": verification_status},
                "schema_valid": schema_valid,
                "confidence": confidence,
                "estimate": False,  # realized observation, not a counterfactual
            }
            self._write(event)
            return event
        except Exception as exc:  # fail-open, always
            self._degrade("record_inference_failed", repr(exc))
            return {}

    def record_operator_active(self, *, seconds: float,
                               worker_id: Optional[str] = None) -> dict:
        if not self.config.enabled:
            return {}
        try:
            event = {"kind": "operator_active",
                     "schema_version": SLM_TELEMETRY_SCHEMA_VERSION,
                     "run_id": self.run_id, "ts": self.wall_clock(),
                     "worker_id": worker_id,
                     "cost": {"operator_active_seconds": float(seconds)}}
            self._write(event)
            return event
        except Exception as exc:
            self._degrade("record_operator_failed", repr(exc))
            return {}

    def summary(self) -> dict:
        """Per-run rollup. Counterfactual savings are NOT computed here —
        only realized totals (protocol: never report estimates as observed)."""
        return {
            "run_id": self.run_id,
            "model_call_counts": dict(self.model_call_counts),
            "frontier_calls": self.frontier_call_count,
            "events": len(self.events),
            "degradations": len(self.degradations),
        }
