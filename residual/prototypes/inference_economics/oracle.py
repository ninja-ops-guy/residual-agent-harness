"""Independent IE-001 metric/classification oracle.

This module deliberately does not call the primary metric/classifier helpers.
The duplication is intentional: Q3/Q9 compare two implementations so a shared
logic bug is less likely to self-certify.
"""

from typing import Optional

from .events import EventStream
from .metrics import BottleneckClass
from .stages import Stage


class IndependentOracle:
    @staticmethod
    def wall_time_ns(stream: EventStream) -> Optional[int]:
        starts: list[int] = []
        ends: list[int] = []
        for event in stream:
            obs = event.observation
            if obs.monotonic_start_ns is not None:
                starts.append(obs.monotonic_start_ns)
            if obs.monotonic_end_ns is not None:
                ends.append(obs.monotonic_end_ns)
        if not starts or not ends:
            return None
        span = max(ends) - min(starts)
        return span if span > 0 else None

    @staticmethod
    def attempt_count(stream: EventStream) -> int:
        count = 0
        for event in stream:
            obs = event.observation
            if obs.stage is Stage.WORKER_EXECUTION and obs.monotonic_end_ns is not None:
                count += 1
        return count

    @staticmethod
    def verifier_terminal_count(stream: EventStream) -> int:
        identities: set[tuple[str, str]] = set()
        for event in stream:
            obs = event.observation
            if obs.stage is Stage.VERIFICATION and obs.monotonic_end_ns is not None:
                identities.add((obs.obligation_id, obs.attempt_id))
        return len(identities)

    @staticmethod
    def accepted_count(stream: EventStream) -> int:
        identities: set[str] = set()
        for event in stream:
            obs = event.observation
            if obs.stage is Stage.VERIFICATION and obs.outcome == "PASS":
                identities.add(obs.obligation_id)
        return len(identities)

    @staticmethod
    def integrated_count(stream: EventStream) -> int:
        identities: set[str] = set()
        for event in stream:
            obs = event.observation
            if obs.stage is Stage.INTEGRATION and obs.monotonic_end_ns is not None:
                identities.add(obs.obligation_id)
        return len(identities)

    @staticmethod
    def throughput_rates(stream: EventStream) -> dict[str, Optional[float]]:
        wall_ns = IndependentOracle.wall_time_ns(stream)
        if wall_ns is None:
            return {
                "attempt_throughput": None,
                "verifier_terminal_throughput": None,
                "accepted_goodput": None,
                "integrated_goodput": None,
            }
        wall_s = wall_ns / 1_000_000_000
        return {
            "attempt_throughput": IndependentOracle.attempt_count(stream) / wall_s,
            "verifier_terminal_throughput": IndependentOracle.verifier_terminal_count(stream) / wall_s,
            "accepted_goodput": IndependentOracle.accepted_count(stream) / wall_s,
            "integrated_goodput": IndependentOracle.integrated_count(stream) / wall_s,
        }

    @staticmethod
    def latency_breakdown(stream: EventStream) -> dict[str, Optional[int]]:
        def first_start(stage: Stage) -> Optional[int]:
            values: list[int] = []
            for event in stream:
                obs = event.observation
                if obs.stage is stage and obs.monotonic_start_ns is not None:
                    values.append(obs.monotonic_start_ns)
            return min(values) if values else None

        def last_end(stage: Stage) -> Optional[int]:
            values: list[int] = []
            for event in stream:
                obs = event.observation
                if obs.stage is stage and obs.monotonic_end_ns is not None:
                    values.append(obs.monotonic_end_ns)
            return max(values) if values else None

        submit = first_start(Stage.MISSION_SUBMIT)
        worker = first_start(Stage.WORKER_EXECUTION)
        evidence = first_start(Stage.EVIDENCE_PUBLICATION)
        dispatch = None
        for stage in (Stage.QUEUE_WAIT, Stage.CONTEXT_PACKAGING, Stage.WORKER_EXECUTION):
            dispatch = first_start(stage)
            if dispatch is not None:
                break
        verify = last_end(Stage.VERIFICATION)
        integrate = last_end(Stage.INTEGRATION)
        return {
            "ttfw_ns": worker - submit if worker is not None and submit is not None else None,
            "tte_ns": evidence - submit if evidence is not None and submit is not None else None,
            "tta_ns": verify - dispatch if verify is not None and dispatch is not None else None,
            "tti_ns": integrate - submit if integrate is not None and submit is not None else None,
        }

    @staticmethod
    def obligation_latencies(stream: EventStream) -> list[dict[str, object]]:
        grouped: dict[tuple[str, str], list] = {}
        for event in stream:
            obs = event.observation
            grouped.setdefault((obs.obligation_id, obs.attempt_id), []).append(obs)
        result: list[dict[str, object]] = []
        for (obligation_id, attempt_id), observations in sorted(grouped.items()):
            starts = [o.monotonic_start_ns for o in observations if o.monotonic_start_ns is not None]
            ends = [o.monotonic_end_ns for o in observations if o.monotonic_end_ns is not None]
            dispatch = [
                o.monotonic_start_ns
                for o in observations
                if o.stage in {Stage.QUEUE_WAIT, Stage.CONTEXT_PACKAGING, Stage.WORKER_EXECUTION}
                and o.monotonic_start_ns is not None
            ]
            verify = [
                o.monotonic_end_ns
                for o in observations
                if o.stage is Stage.VERIFICATION and o.monotonic_end_ns is not None
            ]
            result.append({
                "obligation_id": obligation_id,
                "attempt_id": attempt_id,
                "dispatch_to_verifier_ns": max(verify) - min(dispatch) if verify and dispatch else None,
                "end_to_end_ns": max(ends) - min(starts) if starts and ends else None,
            })
        return result

    @staticmethod
    def stage_occupied_ratios(stream: EventStream) -> dict[str, Optional[float]]:
        wall = IndependentOracle.wall_time_ns(stream)
        grouped: dict[str, list[Optional[int]]] = {}
        for event in stream:
            obs = event.observation
            duration = (
                obs.monotonic_end_ns - obs.monotonic_start_ns
                if obs.monotonic_start_ns is not None and obs.monotonic_end_ns is not None
                else None
            )
            grouped.setdefault(obs.stage.value, []).append(duration)
        result: dict[str, Optional[float]] = {}
        for name, values in grouped.items():
            if wall is None or any(value is None for value in values):
                result[name] = None
            else:
                result[name] = sum(value for value in values if value is not None) / wall
        return result

    @staticmethod
    def otx_input_totals_ns(stream: EventStream) -> dict[str, Optional[int]]:
        phase_stages = {
            "planning": {Stage.PLANNING},
            "scheduling": {Stage.SCHEDULING},
            "context_packaging": {Stage.CONTEXT_PACKAGING},
            "worker_execution": {Stage.WORKER_EXECUTION},
            "verification": {Stage.VERIFICATION},
            "integration": {Stage.INTEGRATION},
            "coordination": {Stage.QUEUE_WAIT, Stage.EVIDENCE_PUBLICATION, Stage.INTEGRATION_QUEUE},
        }
        output: dict[str, Optional[int]] = {}
        for phase, stages in phase_stages.items():
            matching = [event.observation for event in stream if event.observation.stage in stages]
            if not matching:
                output[phase] = 0
                continue
            if any(
                obs.monotonic_start_ns is None or obs.monotonic_end_ns is None
                for obs in matching
            ):
                output[phase] = None
                continue
            output[phase] = sum(
                obs.monotonic_end_ns - obs.monotonic_start_ns
                for obs in matching
                if obs.monotonic_end_ns is not None and obs.monotonic_start_ns is not None
            )
        return output

    @staticmethod
    def queue_depth_at(stream: EventStream, at_ns: int, stage: Stage) -> int:
        count = 0
        for event in stream:
            obs = event.observation
            if obs.stage is not stage or obs.monotonic_start_ns is None:
                continue
            if obs.monotonic_start_ns <= at_ns and (
                obs.monotonic_end_ns is None or obs.monotonic_end_ns > at_ns
            ):
                count += 1
        return count

    @staticmethod
    def queue_transitions(stream: EventStream, stage: Stage) -> list[dict[str, int]]:
        points: set[int] = set()
        for event in stream:
            obs = event.observation
            if obs.stage is not stage:
                continue
            if obs.monotonic_start_ns is not None:
                points.add(obs.monotonic_start_ns)
            if obs.monotonic_end_ns is not None:
                points.add(obs.monotonic_end_ns)
        return [
            {"at_ns": point, "depth": IndependentOracle.queue_depth_at(stream, point, stage)}
            for point in sorted(points)
        ]

    @staticmethod
    def bottleneck_class(
        stream: EventStream,
        dominant_share: float = 0.5,
    ) -> BottleneckClass:
        if not 0 < dominant_share <= 1:
            raise ValueError("dominant_share must be in (0, 1]")
        durations: dict[Stage, int] = {}
        total = 0
        for event in stream:
            obs = event.observation
            if obs.stage in {Stage.MISSION_SUBMIT, Stage.TERMINAL}:
                continue
            if obs.monotonic_start_ns is None or obs.monotonic_end_ns is None:
                return BottleneckClass.UNKNOWN
            duration = obs.monotonic_end_ns - obs.monotonic_start_ns
            durations[obs.stage] = durations.get(obs.stage, 0) + duration
            total += duration
        if total <= 0:
            return BottleneckClass.UNKNOWN
        stage, duration = sorted(
            durations.items(), key=lambda item: (-item[1], item[0].value)
        )[0]
        if duration / total < dominant_share:
            return BottleneckClass.MIXED
        if stage is Stage.WORKER_EXECUTION:
            provider_throttled = any(
                event.observation.resources.provider_throttled is True
                for event in stream
            )
            return (
                BottleneckClass.PROVIDER_BOUND
                if provider_throttled
                else BottleneckClass.WORKER_BOUND
            )
        mapping = {
            Stage.CONTEXT_PACKAGING: BottleneckClass.CONTEXT_BOUND,
            Stage.VERIFICATION: BottleneckClass.VERIFIER_BOUND,
            Stage.INTEGRATION: BottleneckClass.INTEGRATION_BOUND,
            Stage.INTEGRATION_QUEUE: BottleneckClass.INTEGRATION_BOUND,
            Stage.QUEUE_WAIT: BottleneckClass.SCHEDULER_ADMISSION_BOUND,
            Stage.PLANNING: BottleneckClass.COORDINATION_BOUND,
            Stage.SCHEDULING: BottleneckClass.COORDINATION_BOUND,
            Stage.EVIDENCE_PUBLICATION: BottleneckClass.COORDINATION_BOUND,
        }
        return mapping.get(stage, BottleneckClass.MIXED)
