"""IE-001 §10 — hash-bound prototype evidence bundle builder.

The bundle is an external qualification artifact. It intentionally is not a
checked-in source file because binding a bundle to the exact commit/tree that
contains that same bundle would create a self-referential identity problem.
"""

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
import time
from typing import Optional

from .events import EventStream, SCHEMA_REVISION
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
from .policies import frozen_policy_evidence
from .replay import ReplayEngine, metrics_hash, stream_hash
from .stages import Stage


BUNDLE_SCHEMA = "residual.inference-economics.prototype.v1"

NON_CLAIMS = (
    "production speedup",
    "lower real provider cost",
    "model quality improvement",
    "production reliability",
    "live scheduling safety",
    "GPU-level inference optimization",
    "paper-facing research results",
)


@dataclass(frozen=True)
class EvidenceBundle:
    schema: str
    created_unix: float
    source_commit: str
    source_tree: str
    config: dict
    scenario_manifest: dict
    scenario_hashes: dict
    normative_streams: dict
    stream_hashes: dict
    metrics_hashes: dict
    oracle_results: dict
    prototype_results: dict
    policy_results: dict
    replay_results: dict
    test_results: dict
    schema_revision: str
    non_claims: tuple[str, ...]
    bundle_hash: str


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


def _scenario_steps_hash(scenario) -> str:
    payload = [
        {
            "stage": step.stage.value,
            "start_ns": step.start_ns,
            "end_ns": step.end_ns,
            "outcome": step.outcome,
            "obligation_id": step.obligation_id,
            "attempt_id": step.attempt_id,
            "resources": asdict(step.resources),
        }
        for step in scenario.steps
    ]
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _oracle_record(stream: EventStream) -> dict:
    return {
        "bottleneck": IndependentOracle.bottleneck_class(stream).value,
        "wall_time_ns": IndependentOracle.wall_time_ns(stream),
        "throughput": IndependentOracle.throughput_rates(stream),
        "latency": IndependentOracle.latency_breakdown(stream),
        "obligation_latencies": IndependentOracle.obligation_latencies(stream),
        "stage_occupied_ratios": IndependentOracle.stage_occupied_ratios(stream),
        "otx_inputs_ns": IndependentOracle.otx_input_totals_ns(stream),
        "queue_transitions": {
            stage.value: IndependentOracle.queue_transitions(stream, stage)
            for stage in (Stage.QUEUE_WAIT, Stage.VERIFICATION, Stage.INTEGRATION_QUEUE)
        },
    }


def _prototype_record(stream: EventStream) -> dict:
    return {
        "bottleneck": classify_bottleneck(stream).value,
        "throughput": asdict(compute_throughput(stream)),
        "latency": asdict(compute_latency(stream)),
        "obligation_latencies": [asdict(item) for item in obligation_latencies(stream)],
        "pressure": asdict(compute_pressure(stream)),
        "resource_accounting": asdict(compute_resource_accounting(stream)),
        "otx_projection": asdict(otx_projection(stream)),
        "stage_distributions": [asdict(item) for item in stage_distributions(stream)],
        "stage_utilizations": [asdict(item) for item in stage_utilizations(stream)],
    }


def build_bundle(
    scenarios: list,
    streams: dict[str, EventStream],
    source_commit: str,
    source_tree: str,
    *,
    test_results: dict,
    config: Optional[dict] = None,
) -> EvidenceBundle:
    """Build one deterministic qualification artifact for an exact source head.

    ``test_results`` is required so a caller cannot accidentally emit a bundle
    that appears complete while omitting the qualification result record.
    """

    if not source_commit or not source_tree:
        raise ValueError("exact source commit and tree are required")
    if not test_results:
        raise ValueError("test_results are required")
    scenario_names = {scenario.name for scenario in scenarios}
    if set(streams) != scenario_names:
        raise ValueError("streams must exactly match the scenario manifest")
    for name, stream in streams.items():
        for event in stream:
            obs = event.observation
            if obs.source_commit != source_commit or obs.source_tree != source_tree:
                raise ValueError(
                    f"stream {name!r} source identity does not match bundle exact head"
                )

    scenario_manifest = {
        scenario.name: {
            "description": scenario.description,
            "expected_bottleneck": scenario.expected_bottleneck.value,
        }
        for scenario in scenarios
    }
    scenario_hashes = {
        scenario.name: _scenario_steps_hash(scenario) for scenario in scenarios
    }
    normative_streams = {
        name: stream.to_records() for name, stream in sorted(streams.items())
    }
    stream_hashes = {
        name: stream_hash(stream) for name, stream in sorted(streams.items())
    }
    metrics_hashes = {
        name: metrics_hash(stream) for name, stream in sorted(streams.items())
    }
    oracle_results = {
        scenario.name: _oracle_record(streams[scenario.name]) for scenario in scenarios
    }
    prototype_results = {
        scenario.name: _prototype_record(streams[scenario.name]) for scenario in scenarios
    }
    replay_results = {
        scenario.name: ReplayEngine(streams[scenario.name]).replay(streams[scenario.name])
        for scenario in scenarios
    }
    policy_results = frozen_policy_evidence()

    normative_payload = {
        "schema": BUNDLE_SCHEMA,
        "source_commit": source_commit,
        "source_tree": source_tree,
        "config": config or {},
        "scenario_manifest": scenario_manifest,
        "scenario_hashes": scenario_hashes,
        "normative_streams": normative_streams,
        "stream_hashes": stream_hashes,
        "metrics_hashes": metrics_hashes,
        "oracle_results": oracle_results,
        "prototype_results": prototype_results,
        "policy_results": policy_results,
        "replay_results": replay_results,
        "test_results": test_results,
        "schema_revision": SCHEMA_REVISION,
        "non_claims": NON_CLAIMS,
    }
    bundle_hash = hashlib.sha256(_canonical_bytes(normative_payload)).hexdigest()

    return EvidenceBundle(
        schema=BUNDLE_SCHEMA,
        created_unix=time.time(),
        source_commit=source_commit,
        source_tree=source_tree,
        config=config or {},
        scenario_manifest=scenario_manifest,
        scenario_hashes=scenario_hashes,
        normative_streams=normative_streams,
        stream_hashes=stream_hashes,
        metrics_hashes=metrics_hashes,
        oracle_results=oracle_results,
        prototype_results=prototype_results,
        policy_results=policy_results,
        replay_results=replay_results,
        test_results=test_results,
        schema_revision=SCHEMA_REVISION,
        non_claims=NON_CLAIMS,
        bundle_hash=bundle_hash,
    )


def bundle_to_json(bundle: EvidenceBundle) -> str:
    return json.dumps(
        _json_ready(asdict(bundle)),
        indent=2,
        sort_keys=True,
        allow_nan=False,
    )
