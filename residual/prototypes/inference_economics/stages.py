"""IE-001 lifecycle and observation models.

Development-only models for deterministic frozen/replayed observations. They
carry identities and optional economics signals but have no execution authority.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Stage(str, Enum):
    MISSION_SUBMIT = "mission_submit"
    PLANNING = "planning"
    SCHEDULING = "scheduling"
    QUEUE_WAIT = "queue_wait"
    CONTEXT_PACKAGING = "context_packaging"
    WORKER_EXECUTION = "worker_execution"
    EVIDENCE_PUBLICATION = "evidence_publication"
    VERIFICATION = "verification"
    INTEGRATION_QUEUE = "integration_queue"
    INTEGRATION = "integration"
    TERMINAL = "terminal"


MINIMUM_STAGES = frozenset(Stage)

VALID_TRANSITIONS: dict[Stage, frozenset[Stage]] = {
    Stage.MISSION_SUBMIT: frozenset({Stage.PLANNING}),
    Stage.PLANNING: frozenset({Stage.SCHEDULING}),
    Stage.SCHEDULING: frozenset({Stage.QUEUE_WAIT, Stage.CONTEXT_PACKAGING}),
    Stage.QUEUE_WAIT: frozenset({Stage.CONTEXT_PACKAGING}),
    Stage.CONTEXT_PACKAGING: frozenset({Stage.WORKER_EXECUTION}),
    Stage.WORKER_EXECUTION: frozenset({Stage.EVIDENCE_PUBLICATION}),
    Stage.EVIDENCE_PUBLICATION: frozenset({Stage.VERIFICATION}),
    Stage.VERIFICATION: frozenset({Stage.INTEGRATION_QUEUE, Stage.TERMINAL}),
    Stage.INTEGRATION_QUEUE: frozenset({Stage.INTEGRATION}),
    Stage.INTEGRATION: frozenset({Stage.TERMINAL}),
    Stage.TERMINAL: frozenset(),
}


@dataclass(frozen=True)
class ResourceSignals:
    """Optional authoritative economics/resource observations.

    ``None`` always means UNKNOWN/unreported. No caller is allowed to infer
    zero cost, zero tokens, zero queue depth, or zero/infinite capacity from a
    missing field.
    """

    ready_frontier_depth: Optional[int] = None
    pending_verification_depth: Optional[int] = None
    integration_queue_depth: Optional[int] = None
    active_workers: Optional[int] = None
    active_verifiers: Optional[int] = None
    active_integrations: Optional[int] = None
    worker_capacity: Optional[int] = None
    verifier_capacity: Optional[int] = None
    integration_capacity: Optional[int] = None
    context_bytes: Optional[int] = None
    context_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cached_input_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    provider_cost: Optional[float] = None
    cache_lookups: Optional[int] = None
    cache_hits: Optional[int] = None
    cache_misses: Optional[int] = None
    cache_revalidations: Optional[int] = None
    retries: Optional[int] = None
    rework: Optional[int] = None
    rejections: Optional[int] = None
    conflicts: Optional[int] = None
    cancellations: Optional[int] = None
    escalations: Optional[int] = None
    provider_throttled: Optional[bool] = None

    def __post_init__(self) -> None:
        int_fields = (
            "ready_frontier_depth",
            "pending_verification_depth",
            "integration_queue_depth",
            "active_workers",
            "active_verifiers",
            "active_integrations",
            "worker_capacity",
            "verifier_capacity",
            "integration_capacity",
            "context_bytes",
            "context_tokens",
            "prompt_tokens",
            "completion_tokens",
            "cached_input_tokens",
            "reasoning_tokens",
            "cache_lookups",
            "cache_hits",
            "cache_misses",
            "cache_revalidations",
            "retries",
            "rework",
            "rejections",
            "conflicts",
            "cancellations",
            "escalations",
        )
        for name in int_fields:
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"negative resource signal {name}={value}")
        if self.provider_cost is not None and self.provider_cost < 0:
            raise ValueError("provider_cost cannot be negative")


@dataclass(frozen=True)
class StageObservation:
    """One hash-bindable lifecycle observation.

    Timestamps are monotonic nanoseconds. ``None`` means missing/UNKNOWN and is
    never synthesized into a zero-duration span.
    """

    run_id: str
    obligation_id: str
    task_class: str
    topology: str
    engine_class: Optional[str]
    source_commit: str
    source_tree: str
    stage: Stage
    monotonic_start_ns: Optional[int]
    monotonic_end_ns: Optional[int]
    outcome: str
    evidence_class: str
    schema_revision: str
    attempt_id: str = "attempt-001"
    resources: ResourceSignals = field(default_factory=ResourceSignals)

    def __post_init__(self) -> None:
        required = {
            "run_id": self.run_id,
            "obligation_id": self.obligation_id,
            "task_class": self.task_class,
            "topology": self.topology,
            "source_commit": self.source_commit,
            "source_tree": self.source_tree,
            "outcome": self.outcome,
            "evidence_class": self.evidence_class,
            "schema_revision": self.schema_revision,
            "attempt_id": self.attempt_id,
        }
        missing = sorted(name for name, value in required.items() if not value)
        if missing:
            raise ValueError(f"required observation identities are empty: {missing}")
        if self.monotonic_start_ns is not None and self.monotonic_start_ns < 0:
            raise ValueError("monotonic_start_ns cannot be negative")
        if self.monotonic_end_ns is not None and self.monotonic_end_ns < 0:
            raise ValueError("monotonic_end_ns cannot be negative")
        if (
            self.monotonic_start_ns is not None
            and self.monotonic_end_ns is not None
            and self.monotonic_end_ns < self.monotonic_start_ns
        ):
            raise ValueError(
                f"negative duration: end={self.monotonic_end_ns} "
                f"< start={self.monotonic_start_ns} "
                f"for {self.obligation_id}@{self.stage}"
            )

    @property
    def duration_ns(self) -> Optional[int]:
        if self.monotonic_start_ns is None or self.monotonic_end_ns is None:
            return None
        return self.monotonic_end_ns - self.monotonic_start_ns
