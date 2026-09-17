"""IE-001 metric projection from validated lifecycle observations."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .events import EventStream
from .stages import Stage


@dataclass(frozen=True)
class ThroughputBreakdown:
    attempt_throughput: Optional[float]
    verifier_terminal_throughput: Optional[float]
    accepted_goodput: Optional[float]
    integrated_goodput: Optional[float]
    correct_accepted_goodput: Optional[float] = None
    correct_integrated_goodput: Optional[float] = None


@dataclass(frozen=True)
class LatencyBreakdown:
    ttfw_ns: Optional[int]
    tte_ns: Optional[int]
    tta_ns: Optional[int]
    tti_ns: Optional[int]


@dataclass(frozen=True)
class ObligationLatency:
    obligation_id: str
    attempt_id: str
    dispatch_to_verifier_ns: Optional[int]
    end_to_end_ns: Optional[int]


@dataclass(frozen=True)
class StageDistribution:
    stage: str
    samples: int
    p50_ns: Optional[float]
    p95_ns: Optional[float]
    p99_ns: Optional[float]


@dataclass(frozen=True)
class StageUtilization:
    stage: str
    occupied_ns: Optional[int]
    wall_ns: Optional[int]
    utilization: Optional[float]


@dataclass(frozen=True)
class PressureSnapshot:
    ready_frontier_depth: Optional[int]
    active_workers: Optional[int]
    worker_capacity: Optional[int]
    pending_verifications: Optional[int]
    active_verifiers: Optional[int]
    verifier_capacity: Optional[int]
    integration_queue_depth: Optional[int]
    active_integrations: Optional[int]
    integration_capacity: Optional[int]


@dataclass(frozen=True)
class ResourceAccounting:
    context_bytes: Optional[int]
    context_tokens: Optional[int]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    cached_input_tokens: Optional[int]
    reasoning_tokens: Optional[int]
    provider_cost: Optional[float]
    cache_lookups: Optional[int]
    cache_hits: Optional[int]
    cache_misses: Optional[int]
    cache_revalidations: Optional[int]
    retries: Optional[int]
    rework: Optional[int]
    rejections: Optional[int]
    conflicts: Optional[int]
    cancellations: Optional[int]
    escalations: Optional[int]


@dataclass(frozen=True)
class OTXProjection:
    """Projection into existing ``residual.otx.PhaseTiming`` phase names.

    A phase with a retained observation but missing timing remains ``None``.
    A genuinely absent phase is represented as 0.0, matching the existing OTX
    model's inactive-phase convention. Queue/evidence-publication/
    integration-queue are residual control overhead and map to coordination.
    """

    phase_seconds: dict[str, Optional[float]]
    worker_execution_s: Optional[float]
    coordination_overhead_s: Optional[float]
    observed_tax: Optional[float]
    complete: bool


class BottleneckClass(str, Enum):
    WORKER_BOUND = "WORKER_BOUND"
    CONTEXT_BOUND = "CONTEXT_BOUND"
    VERIFIER_BOUND = "VERIFIER_BOUND"
    INTEGRATION_BOUND = "INTEGRATION_BOUND"
    SCHEDULER_ADMISSION_BOUND = "SCHEDULER_ADMISSION_BOUND"
    COORDINATION_BOUND = "COORDINATION_BOUND"
    PROVIDER_BOUND = "PROVIDER_BOUND"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


def _bounds(stream: EventStream) -> tuple[Optional[int], Optional[int]]:
    starts = [
        ev.observation.monotonic_start_ns
        for ev in stream
        if ev.observation.monotonic_start_ns is not None
    ]
    ends = [
        ev.observation.monotonic_end_ns
        for ev in stream
        if ev.observation.monotonic_end_ns is not None
    ]
    return (min(starts) if starts else None, max(ends) if ends else None)


def _wall_ns(stream: EventStream) -> Optional[int]:
    start, end = _bounds(stream)
    if start is None or end is None or end <= start:
        return None
    return end - start


def _wall_seconds(stream: EventStream) -> Optional[float]:
    wall = _wall_ns(stream)
    return None if wall is None else wall / 1e9


def compute_throughput(stream: EventStream) -> ThroughputBreakdown:
    wall_s = _wall_seconds(stream)
    if wall_s is None:
        return ThroughputBreakdown(None, None, None, None)

    attempts = sum(
        1
        for ev in stream
        if ev.observation.stage == Stage.WORKER_EXECUTION
        and ev.observation.monotonic_end_ns is not None
    )
    verifier_terminal = {
        (ev.observation.obligation_id, ev.observation.attempt_id)
        for ev in stream
        if ev.observation.stage == Stage.VERIFICATION
        and ev.observation.monotonic_end_ns is not None
    }
    accepted = {
        ev.observation.obligation_id
        for ev in stream
        if ev.observation.stage == Stage.VERIFICATION
        and ev.observation.outcome == "PASS"
    }
    integrated = {
        ev.observation.obligation_id
        for ev in stream
        if ev.observation.stage == Stage.INTEGRATION
        and ev.observation.monotonic_end_ns is not None
    }
    return ThroughputBreakdown(
        attempt_throughput=attempts / wall_s,
        verifier_terminal_throughput=len(verifier_terminal) / wall_s,
        accepted_goodput=len(accepted) / wall_s,
        integrated_goodput=len(integrated) / wall_s,
    )


def _first_start(stream: EventStream, stage: Stage) -> Optional[int]:
    vals = [
        ev.observation.monotonic_start_ns
        for ev in stream
        if ev.observation.stage == stage
        and ev.observation.monotonic_start_ns is not None
    ]
    return min(vals) if vals else None


def _last_end(stream: EventStream, stage: Stage) -> Optional[int]:
    vals = [
        ev.observation.monotonic_end_ns
        for ev in stream
        if ev.observation.stage == stage
        and ev.observation.monotonic_end_ns is not None
    ]
    return max(vals) if vals else None


def _dispatch_anchor(stream: EventStream) -> Optional[int]:
    # queue_wait is the closest explicit ready/admission point in IE-001. If a
    # trace omits it, fall back deterministically toward the worker dispatch.
    for stage in (Stage.QUEUE_WAIT, Stage.CONTEXT_PACKAGING, Stage.WORKER_EXECUTION):
        value = _first_start(stream, stage)
        if value is not None:
            return value
    return None


def compute_latency(stream: EventStream) -> LatencyBreakdown:
    submit = _first_start(stream, Stage.MISSION_SUBMIT)
    first_worker = _first_start(stream, Stage.WORKER_EXECUTION)
    first_evidence = _first_start(stream, Stage.EVIDENCE_PUBLICATION)
    dispatch = _dispatch_anchor(stream)
    last_verify = _last_end(stream, Stage.VERIFICATION)
    last_integrate = _last_end(stream, Stage.INTEGRATION)
    return LatencyBreakdown(
        ttfw_ns=(first_worker - submit)
        if submit is not None and first_worker is not None
        else None,
        tte_ns=(first_evidence - submit)
        if submit is not None and first_evidence is not None
        else None,
        tta_ns=(last_verify - dispatch)
        if dispatch is not None and last_verify is not None
        else None,
        tti_ns=(last_integrate - submit)
        if submit is not None and last_integrate is not None
        else None,
    )


def obligation_latencies(stream: EventStream) -> list[ObligationLatency]:
    grouped: dict[tuple[str, str], list] = {}
    for ev in stream:
        obs = ev.observation
        grouped.setdefault((obs.obligation_id, obs.attempt_id), []).append(obs)

    result: list[ObligationLatency] = []
    for (obligation_id, attempt_id), observations in sorted(grouped.items()):
        starts = [o.monotonic_start_ns for o in observations if o.monotonic_start_ns is not None]
        ends = [o.monotonic_end_ns for o in observations if o.monotonic_end_ns is not None]
        dispatch_candidates = [
            o.monotonic_start_ns
            for o in observations
            if o.stage in {Stage.QUEUE_WAIT, Stage.CONTEXT_PACKAGING, Stage.WORKER_EXECUTION}
            and o.monotonic_start_ns is not None
        ]
        verify_ends = [
            o.monotonic_end_ns
            for o in observations
            if o.stage == Stage.VERIFICATION and o.monotonic_end_ns is not None
        ]
        result.append(
            ObligationLatency(
                obligation_id=obligation_id,
                attempt_id=attempt_id,
                dispatch_to_verifier_ns=(max(verify_ends) - min(dispatch_candidates))
                if dispatch_candidates and verify_ends
                else None,
                end_to_end_ns=(max(ends) - min(starts)) if starts and ends else None,
            )
        )
    return result


def percentile(values: list[float], p: float) -> Optional[float]:
    if not 0 <= p <= 100:
        raise ValueError("percentile must be between 0 and 100")
    if not values:
        return None
    # A one-sample median is well-defined. Tail percentiles require at least
    # two samples so they do not fabricate a distribution from one point.
    if p != 50 and len(values) < 2:
        return None
    vals = sorted(values)
    k = (len(vals) - 1) * (p / 100.0)
    lo = int(k)
    hi = lo + 1
    if hi >= len(vals):
        return vals[lo]
    return vals[lo] + (vals[hi] - vals[lo]) * (k - lo)


def stage_distributions(stream: EventStream) -> list[StageDistribution]:
    by_stage: dict[str, list[int]] = {}
    observed_stages: set[str] = set()
    for ev in stream:
        observed_stages.add(ev.observation.stage.value)
        duration = ev.observation.duration_ns
        if duration is not None:
            by_stage.setdefault(ev.observation.stage.value, []).append(duration)
    result = []
    for name in sorted(observed_stages):
        values = by_stage.get(name, [])
        result.append(
            StageDistribution(
                stage=name,
                samples=len(values),
                p50_ns=percentile(values, 50),
                p95_ns=percentile(values, 95),
                p99_ns=percentile(values, 99),
            )
        )
    return result


def stage_utilizations(stream: EventStream) -> list[StageUtilization]:
    wall = _wall_ns(stream)
    by_stage: dict[str, list[Optional[int]]] = {}
    for ev in stream:
        by_stage.setdefault(ev.observation.stage.value, []).append(ev.observation.duration_ns)
    result = []
    for name, durations in sorted(by_stage.items()):
        occupied = None if any(value is None for value in durations) else sum(value for value in durations if value is not None)
        utilization = (
            occupied / wall
            if occupied is not None and wall is not None and wall > 0
            else None
        )
        result.append(StageUtilization(name, occupied, wall, utilization))
    return result


def _last_known_resource(stream: EventStream, name: str):
    value = None
    for ev in stream:
        candidate = getattr(ev.observation.resources, name)
        if candidate is not None:
            value = candidate
    return value


def _infer_active_at_end(stream: EventStream, stage: Stage) -> Optional[int]:
    _, end = _bounds(stream)
    stage_events = [ev.observation for ev in stream if ev.observation.stage == stage]
    if end is None:
        return None
    if not stage_events:
        return 0
    if any(obs.monotonic_start_ns is None for obs in stage_events):
        return None
    return sum(
        1
        for obs in stage_events
        if obs.monotonic_start_ns is not None
        and obs.monotonic_start_ns <= end
        and (obs.monotonic_end_ns is None or obs.monotonic_end_ns > end)
    )


def compute_pressure(stream: EventStream) -> PressureSnapshot:
    active_workers = _last_known_resource(stream, "active_workers")
    if active_workers is None:
        active_workers = _infer_active_at_end(stream, Stage.WORKER_EXECUTION)
    active_verifiers = _last_known_resource(stream, "active_verifiers")
    if active_verifiers is None:
        active_verifiers = _infer_active_at_end(stream, Stage.VERIFICATION)
    active_integrations = _last_known_resource(stream, "active_integrations")
    if active_integrations is None:
        active_integrations = _infer_active_at_end(stream, Stage.INTEGRATION)
    integration_depth = _last_known_resource(stream, "integration_queue_depth")
    if integration_depth is None:
        integration_depth = _infer_active_at_end(stream, Stage.INTEGRATION_QUEUE)
    return PressureSnapshot(
        ready_frontier_depth=_last_known_resource(stream, "ready_frontier_depth"),
        active_workers=active_workers,
        worker_capacity=_last_known_resource(stream, "worker_capacity"),
        pending_verifications=_last_known_resource(stream, "pending_verification_depth"),
        active_verifiers=active_verifiers,
        verifier_capacity=_last_known_resource(stream, "verifier_capacity"),
        integration_queue_depth=integration_depth,
        active_integrations=active_integrations,
        integration_capacity=_last_known_resource(stream, "integration_capacity"),
    )


def _sum_optional(stream: EventStream, field: str, *, float_value: bool = False):
    vals = [getattr(ev.observation.resources, field) for ev in stream]
    vals = [value for value in vals if value is not None]
    if not vals:
        return None
    return float(sum(vals)) if float_value else int(sum(vals))


def compute_resource_accounting(stream: EventStream) -> ResourceAccounting:
    return ResourceAccounting(
        context_bytes=_sum_optional(stream, "context_bytes"),
        context_tokens=_sum_optional(stream, "context_tokens"),
        prompt_tokens=_sum_optional(stream, "prompt_tokens"),
        completion_tokens=_sum_optional(stream, "completion_tokens"),
        cached_input_tokens=_sum_optional(stream, "cached_input_tokens"),
        reasoning_tokens=_sum_optional(stream, "reasoning_tokens"),
        provider_cost=_sum_optional(stream, "provider_cost", float_value=True),
        cache_lookups=_sum_optional(stream, "cache_lookups"),
        cache_hits=_sum_optional(stream, "cache_hits"),
        cache_misses=_sum_optional(stream, "cache_misses"),
        cache_revalidations=_sum_optional(stream, "cache_revalidations"),
        retries=_sum_optional(stream, "retries"),
        rework=_sum_optional(stream, "rework"),
        rejections=_sum_optional(stream, "rejections"),
        conflicts=_sum_optional(stream, "conflicts"),
        cancellations=_sum_optional(stream, "cancellations"),
        escalations=_sum_optional(stream, "escalations"),
    )


def _phase_total_seconds(stream: EventStream, stages: set[Stage]) -> Optional[float]:
    matching = [ev.observation for ev in stream if ev.observation.stage in stages]
    if not matching:
        return 0.0
    durations = [obs.duration_ns for obs in matching]
    if any(value is None for value in durations):
        return None
    return sum(value for value in durations if value is not None) / 1e9


def otx_projection(stream: EventStream) -> OTXProjection:
    direct = {
        "planning": {Stage.PLANNING},
        "scheduling": {Stage.SCHEDULING},
        "context_packaging": {Stage.CONTEXT_PACKAGING},
        "worker_execution": {Stage.WORKER_EXECUTION},
        "verification": {Stage.VERIFICATION},
        "integration": {Stage.INTEGRATION},
        "coordination": {
            Stage.QUEUE_WAIT,
            Stage.EVIDENCE_PUBLICATION,
            Stage.INTEGRATION_QUEUE,
        },
    }
    seconds = {phase: _phase_total_seconds(stream, stages) for phase, stages in direct.items()}
    complete = all(value is not None for value in seconds.values())
    worker = seconds["worker_execution"]
    overhead_values = [value for name, value in seconds.items() if name != "worker_execution"]
    overhead = sum(value for value in overhead_values if value is not None) if all(value is not None for value in overhead_values) else None
    tax = (
        overhead / worker
        if complete and worker is not None and worker > 0 and overhead is not None
        else None
    )
    return OTXProjection(seconds, worker, overhead, tax, complete)


def _stage_totals_ns(stream: EventStream) -> Optional[dict[Stage, int]]:
    totals: dict[Stage, int] = {}
    for ev in stream:
        obs = ev.observation
        if obs.stage in {Stage.MISSION_SUBMIT, Stage.TERMINAL}:
            continue
        duration = obs.duration_ns
        if duration is None:
            return None
        totals[obs.stage] = totals.get(obs.stage, 0) + duration
    return totals


def classify_bottleneck(stream: EventStream, dominant_share: float = 0.5) -> BottleneckClass:
    """Deterministic primary classifier frozen by IE-001.

    A dominant worker span is provider-bound only when an authoritative
    provider-throttle signal is retained. Queue-wait dominance is classified
    as scheduler/admission bound. Planning/scheduling/evidence residual
    overhead maps to coordination. Missing required timing fails to UNKNOWN.
    """

    if not 0 < dominant_share <= 1:
        raise ValueError("dominant_share must be in (0, 1]")
    totals = _stage_totals_ns(stream)
    if totals is None:
        return BottleneckClass.UNKNOWN
    occupied = sum(totals.values())
    if occupied <= 0:
        return BottleneckClass.UNKNOWN
    stage, value = max(totals.items(), key=lambda item: (item[1], item[0].value))
    if value / occupied < dominant_share:
        return BottleneckClass.MIXED
    if stage == Stage.WORKER_EXECUTION:
        provider_signal = any(
            ev.observation.resources.provider_throttled is True for ev in stream
        )
        return (
            BottleneckClass.PROVIDER_BOUND
            if provider_signal
            else BottleneckClass.WORKER_BOUND
        )
    if stage == Stage.CONTEXT_PACKAGING:
        return BottleneckClass.CONTEXT_BOUND
    if stage == Stage.VERIFICATION:
        return BottleneckClass.VERIFIER_BOUND
    if stage in {Stage.INTEGRATION, Stage.INTEGRATION_QUEUE}:
        return BottleneckClass.INTEGRATION_BOUND
    if stage == Stage.QUEUE_WAIT:
        return BottleneckClass.SCHEDULER_ADMISSION_BOUND
    if stage in {Stage.PLANNING, Stage.SCHEDULING, Stage.EVIDENCE_PUBLICATION}:
        return BottleneckClass.COORDINATION_BOUND
    return BottleneckClass.MIXED
