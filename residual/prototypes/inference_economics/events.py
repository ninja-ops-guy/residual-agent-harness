"""IE-001/IE-002 normative observation-stream validation."""

from dataclasses import asdict, dataclass
from typing import Iterator, Optional

from .stages import Stage, StageObservation, VALID_TRANSITIONS


SCHEMA_REVISION = "residual.inference-economics.observation.v1"


class EventValidationError(Exception):
    """Normative observation stream is invalid; callers must fail closed."""


@dataclass(frozen=True)
class Event:
    seq: int
    observation: StageObservation


def observation_record(obs: StageObservation) -> dict:
    record = asdict(obs)
    record["stage"] = obs.stage.value
    return record


def event_record(ev: Event) -> dict:
    return {"seq": ev.seq, "observation": observation_record(ev.observation)}


class EventStream:
    """Validated ordered lifecycle observations.

    Identity includes attempt id so repeated attempts can be represented
    without silently merging events.  Stage-order validation is likewise
    attempt-scoped.
    """

    def __init__(self, events: list[Event]):
        self._events: list[Event] = []
        self._seen: set[tuple[str, str, str, Stage]] = set()
        self._last_stage: dict[tuple[str, str, str], Stage] = {}
        self._last_seq: Optional[int] = None
        for ev in events:
            self._validate(ev)
            self._events.append(ev)

    def _validate(self, ev: Event) -> None:
        obs = ev.observation
        if ev.seq < 0:
            raise EventValidationError("negative sequence")
        if self._last_seq is not None and ev.seq <= self._last_seq:
            raise EventValidationError(f"non-monotonic sequence: {ev.seq} <= {self._last_seq}")
        if obs.schema_revision != SCHEMA_REVISION:
            raise EventValidationError(
                f"incompatible schema revision: {obs.schema_revision!r} != {SCHEMA_REVISION!r}"
            )
        key = (obs.run_id, obs.obligation_id, obs.attempt_id, obs.stage)
        if key in self._seen:
            raise EventValidationError(f"duplicate normative event identity: {key}")
        attempt_key = (obs.run_id, obs.obligation_id, obs.attempt_id)
        prev = self._last_stage.get(attempt_key)
        if prev is not None:
            allowed = VALID_TRANSITIONS[prev]
            if obs.stage not in allowed:
                raise EventValidationError(
                    f"impossible stage transition: {prev} -> {obs.stage} "
                    f"for obligation {obs.obligation_id} attempt {obs.attempt_id}"
                )
        self._seen.add(key)
        self._last_stage[attempt_key] = obs.stage
        self._last_seq = ev.seq

    def __iter__(self) -> Iterator[Event]:
        return iter(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def filter_by_stage(self, stage: Stage) -> list[Event]:
        return [ev for ev in self._events if ev.observation.stage == stage]

    def obligations(self) -> set[str]:
        return {ev.observation.obligation_id for ev in self._events}

    def to_records(self) -> list[dict]:
        return [event_record(ev) for ev in self._events]
