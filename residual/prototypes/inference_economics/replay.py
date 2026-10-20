"""IE-001 Q2 — deterministic replay and tamper evidence."""

from dataclasses import asdict
from enum import Enum
import hashlib
import json

from .events import EventStream
from .metrics import (
    classify_bottleneck,
    compute_latency,
    compute_pressure,
    compute_resource_accounting,
    compute_throughput,
    obligation_latencies,
    otx_projection,
    stage_distributions,
    stage_utilizations,
)
from .oracle import IndependentOracle


class ReplayError(Exception):
    """Raised when replay fails closed."""


def _json_ready(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def _canonical_bytes(value) -> bytes:
    return json.dumps(
        _json_ready(value),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def stream_hash(stream: EventStream) -> str:
    """SHA-256 over every normative event, including identity/resources/order."""

    return hashlib.sha256(_canonical_bytes(stream.to_records())).hexdigest()


def metrics_record(stream: EventStream) -> dict:
    """Complete deterministic projection used as the Q1/Q2 replay target."""

    return {
        "throughput": asdict(compute_throughput(stream)),
        "latency": asdict(compute_latency(stream)),
        "obligation_latencies": [asdict(item) for item in obligation_latencies(stream)],
        "pressure": asdict(compute_pressure(stream)),
        "resource_accounting": asdict(compute_resource_accounting(stream)),
        "otx_projection": asdict(otx_projection(stream)),
        "stage_distributions": [asdict(item) for item in stage_distributions(stream)],
        "stage_utilizations": [asdict(item) for item in stage_utilizations(stream)],
        "bottleneck": classify_bottleneck(stream).value,
        "oracle": {
            "wall_time_ns": IndependentOracle.wall_time_ns(stream),
            "throughput": IndependentOracle.throughput_rates(stream),
            "latency": IndependentOracle.latency_breakdown(stream),
            "obligation_latencies": IndependentOracle.obligation_latencies(stream),
            "stage_occupied_ratios": IndependentOracle.stage_occupied_ratios(stream),
            "otx_inputs_ns": IndependentOracle.otx_input_totals_ns(stream),
            "bottleneck": IndependentOracle.bottleneck_class(stream).value,
        },
    }


def metrics_hash(stream: EventStream) -> str:
    return hashlib.sha256(_canonical_bytes(metrics_record(stream))).hexdigest()


class ReplayEngine:
    """Replays a frozen event stream and verifies normative byte identity."""

    def __init__(self, frozen_stream: EventStream):
        self._frozen_stream_hash = stream_hash(frozen_stream)
        self._frozen_metrics_hash = metrics_hash(frozen_stream)

    @property
    def frozen_stream_hash(self) -> str:
        return self._frozen_stream_hash

    @property
    def frozen_metrics_hash(self) -> str:
        return self._frozen_metrics_hash

    def replay(self, candidate: EventStream) -> dict:
        candidate_stream_hash = stream_hash(candidate)
        if candidate_stream_hash != self._frozen_stream_hash:
            raise ReplayError(
                f"stream hash mismatch: {candidate_stream_hash} != {self._frozen_stream_hash}"
            )
        candidate_metrics_hash = metrics_hash(candidate)
        if candidate_metrics_hash != self._frozen_metrics_hash:
            raise ReplayError(
                f"metrics hash mismatch: {candidate_metrics_hash} != {self._frozen_metrics_hash}"
            )
        return {
            "stream_hash": candidate_stream_hash,
            "metrics_hash": candidate_metrics_hash,
            "replay_ok": True,
        }

    def verify_tamper_evidence(self, tampered: EventStream) -> bool:
        try:
            self.replay(tampered)
            return False
        except ReplayError:
            return True
