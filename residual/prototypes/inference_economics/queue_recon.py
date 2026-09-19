"""IE-001/IE-002 per-transition queue reconstruction."""

from dataclasses import dataclass
from typing import Optional

from .events import EventStream
from .oracle import IndependentOracle
from .stages import Stage


@dataclass(frozen=True)
class QueueTransition:
    at_ns: int
    stage: str
    depth: int


class QueueReconstructor:
    """Reconstruct interval occupancy at every observed stage boundary."""

    def __init__(self, stream: EventStream):
        self._stream = stream

    def transitions_for(self, stage: Stage) -> list[QueueTransition]:
        points: set[int] = set()
        intervals: list[tuple[Optional[int], Optional[int]]] = []
        for ev in self._stream:
            obs = ev.observation
            if obs.stage != stage:
                continue
            start = obs.monotonic_start_ns
            end = obs.monotonic_end_ns
            if start is not None:
                points.add(start)
            if end is not None:
                points.add(end)
            intervals.append((start, end))

        result: list[QueueTransition] = []
        for point in sorted(points):
            depth = sum(
                1
                for start, end in intervals
                if start is not None
                and start <= point
                and (end is None or end > point)
            )
            result.append(QueueTransition(point, stage.value, depth))
        return result

    def all_transitions(self) -> list[QueueTransition]:
        stages_present = {ev.observation.stage for ev in self._stream}
        result: list[QueueTransition] = []
        for stage in sorted(stages_present, key=lambda item: item.value):
            result.extend(self.transitions_for(stage))
        return sorted(result, key=lambda transition: (transition.at_ns, transition.stage))

    def verify_against_oracle(self, stage: Stage) -> list[str]:
        mismatches: list[str] = []
        for transition in self.transitions_for(stage):
            expected = IndependentOracle.queue_depth_at(
                self._stream, transition.at_ns, stage
            )
            if expected != transition.depth:
                mismatches.append(
                    f"t={transition.at_ns}: reconstructor={transition.depth} oracle={expected}"
                )
        return mismatches
