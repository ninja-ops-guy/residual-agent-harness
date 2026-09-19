"""Arena-aligned local trace schema and signal extraction.

These measurements mirror the public Agent Arena signal definitions where a
local deterministic equivalent exists. They are not official Arena leaderboard
scores and are never labelled as such.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..core import ContractError, canonical, digest, strict_json

TRACE_SCHEMA = "residual.arena-trace.v1"
LANDED_CORRECTION_OUTCOMES = frozenset({"accepted", "extended", "redirected"})
FAILED_CORRECTION_OUTCOMES = frozenset({"rejected", "gave_up"})


def _bounded_text(value, name, limit=500):
    if not isinstance(value, str) or not value or len(value) > limit or any(ord(ch) < 32 for ch in value):
        raise ContractError("invalid " + name)
    return value


def _snapshot(value, name):
    if not isinstance(value, dict):
        raise ContractError(name + " must be an object")
    return canonical(value)


@dataclass(frozen=True)
class ArenaTraceEvent:
    index: int
    kind: str
    data_json: str

    @classmethod
    def build(cls, index: int, kind: str, data: dict):
        if type(index) is not int or index < 0:
            raise ContractError("invalid Arena trace event index")
        _bounded_text(kind, "Arena trace event kind", 100)
        return cls(index=index, kind=kind, data_json=_snapshot(data, "Arena trace event data"))

    @property
    def data(self):
        return strict_json(self.data_json)

    def payload(self):
        return {"index": self.index, "kind": self.kind, "data": self.data}


@dataclass(frozen=True)
class AgentEvaluationTrace:
    experiment_id: str
    observation_id: str
    task_id: str
    condition: str
    model: str
    harness_version: str
    environment_digest: str
    available_tools: tuple[str, ...]
    events: tuple[ArenaTraceEvent, ...]
    usage_json: str
    verdict_json: str
    provider_metadata_json: str

    @classmethod
    def build(
        cls,
        *,
        experiment_id: str,
        observation_id: str,
        task_id: str,
        condition: str,
        model: str,
        harness_version: str,
        environment_digest: str,
        available_tools: Iterable[str],
        events: Iterable[ArenaTraceEvent],
        usage: dict,
        verdict: dict,
        provider_metadata: dict | None = None,
    ):
        for value, name, limit in (
            (experiment_id, "experiment id", 120),
            (observation_id, "observation id", 300),
            (task_id, "task id", 200),
            (model, "model", 500),
            (harness_version, "harness version", 200),
            (environment_digest, "environment digest", 200),
        ):
            _bounded_text(value, name, limit)
        if condition not in {"control", "residual"}:
            raise ContractError("Arena condition must be control or residual")
        tools = tuple(sorted(available_tools))
        if len(tools) != len(set(tools)) or any(
            not isinstance(tool, str) or not tool or len(tool) > 200 for tool in tools
        ):
            raise ContractError("invalid Arena available-tools set")
        frozen_events = tuple(events)
        if tuple(event.index for event in frozen_events) != tuple(range(len(frozen_events))):
            raise ContractError("Arena trace event indexes must be contiguous from zero")
        if not all(isinstance(event, ArenaTraceEvent) for event in frozen_events):
            raise ContractError("invalid Arena trace event")
        return cls(
            experiment_id=experiment_id,
            observation_id=observation_id,
            task_id=task_id,
            condition=condition,
            model=model,
            harness_version=harness_version,
            environment_digest=environment_digest,
            available_tools=tools,
            events=frozen_events,
            usage_json=_snapshot(usage, "usage"),
            verdict_json=_snapshot(verdict, "verdict"),
            provider_metadata_json=_snapshot(provider_metadata or {}, "provider metadata"),
        )

    @property
    def usage(self):
        return strict_json(self.usage_json)

    @property
    def verdict(self):
        return strict_json(self.verdict_json)

    @property
    def provider_metadata(self):
        return strict_json(self.provider_metadata_json)

    def unsigned_payload(self):
        return {
            "schema_version": TRACE_SCHEMA,
            "experiment_id": self.experiment_id,
            "observation_id": self.observation_id,
            "task_id": self.task_id,
            "condition": self.condition,
            "model": self.model,
            "harness_version": self.harness_version,
            "environment_digest": self.environment_digest,
            "available_tools": list(self.available_tools),
            "events": [event.payload() for event in self.events],
            "usage": self.usage,
            "verdict": self.verdict,
            "provider_metadata": self.provider_metadata,
        }

    @property
    def sha256(self):
        return digest(self.unsigned_payload())

    def payload(self):
        return {**self.unsigned_payload(), "trace_sha256": self.sha256}

    @classmethod
    def from_payload(cls, payload):
        if not isinstance(payload, dict) or payload.get("schema_version") != TRACE_SCHEMA:
            raise ContractError("invalid Arena trace document")
        events = tuple(
            ArenaTraceEvent.build(entry["index"], entry["kind"], entry["data"])
            for entry in payload.get("events", [])
        )
        trace = cls.build(
            experiment_id=payload["experiment_id"],
            observation_id=payload["observation_id"],
            task_id=payload["task_id"],
            condition=payload["condition"],
            model=payload["model"],
            harness_version=payload["harness_version"],
            environment_digest=payload["environment_digest"],
            available_tools=payload.get("available_tools", []),
            events=events,
            usage=payload.get("usage", {}),
            verdict=payload.get("verdict", {}),
            provider_metadata=payload.get("provider_metadata", {}),
        )
        claimed = payload.get("trace_sha256")
        if claimed is not None and claimed != trace.sha256:
            raise ContractError("Arena trace digest mismatch")
        return trace


@dataclass(frozen=True)
class ArenaAlignedSignals:
    confirmed_success: bool | None
    praise_count: int
    complaint_count: int
    praise_vs_complaint: bool | None
    corrections: int
    corrections_landed: int
    steerability: float | None
    bash_failure_episodes: int
    bash_recovered_episodes: int
    bash_unrecovered_episodes: int
    bash_recovery_calls_total: int
    bash_recovery_mean_calls: float | None
    tool_calls: int
    tool_hallucinations: int
    tool_hallucination_rate: float | None

    def payload(self):
        return dict(self.__dict__)


def extract_arena_aligned_signals(trace: AgentEvaluationTrace) -> ArenaAlignedSignals:
    approved = None
    praise = complaint = 0
    corrections = set()
    correction_outcomes = {}
    tool_calls = hallucinations = 0
    available = set(trace.available_tools)

    bash_failure_episodes = recovered = unrecovered = recovery_calls_total = 0
    active_recovery_calls = None

    for event in trace.events:
        data = event.data
        if event.kind == "task_feedback":
            value = data.get("approved")
            if type(value) is bool:
                approved = value
        elif event.kind == "feedback":
            sentiment = data.get("sentiment")
            if sentiment == "praise":
                praise += 1
            elif sentiment == "complaint":
                complaint += 1
        elif event.kind == "correction":
            correction_id = data.get("correction_id")
            if isinstance(correction_id, str) and correction_id:
                corrections.add(correction_id)
        elif event.kind == "correction_outcome":
            correction_id, status = data.get("correction_id"), data.get("status")
            if correction_id in corrections and status in LANDED_CORRECTION_OUTCOMES | FAILED_CORRECTION_OUTCOMES:
                correction_outcomes[correction_id] = status
        elif event.kind == "tool_call":
            tool_calls += 1
            name = data.get("name")
            if not isinstance(name, str) or not name or name not in available:
                hallucinations += 1
        elif event.kind == "bash_result":
            ok = data.get("ok")
            if type(ok) is not bool:
                continue
            if active_recovery_calls is None:
                if not ok:
                    bash_failure_episodes += 1
                    active_recovery_calls = 0
            else:
                active_recovery_calls += 1
                if ok:
                    recovered += 1
                    recovery_calls_total += active_recovery_calls
                    active_recovery_calls = None

    if active_recovery_calls is not None:
        unrecovered = 1

    landed = sum(status in LANDED_CORRECTION_OUTCOMES for status in correction_outcomes.values())
    decided_corrections = len(correction_outcomes)
    feedback_total = praise + complaint

    return ArenaAlignedSignals(
        confirmed_success=approved,
        praise_count=praise,
        complaint_count=complaint,
        praise_vs_complaint=(praise > complaint) if feedback_total else None,
        corrections=decided_corrections,
        corrections_landed=landed,
        steerability=(landed / decided_corrections) if decided_corrections else None,
        bash_failure_episodes=bash_failure_episodes,
        bash_recovered_episodes=recovered,
        bash_unrecovered_episodes=unrecovered,
        bash_recovery_calls_total=recovery_calls_total,
        bash_recovery_mean_calls=(recovery_calls_total / recovered) if recovered else None,
        tool_calls=tool_calls,
        tool_hallucinations=hallucinations,
        tool_hallucination_rate=(hallucinations / tool_calls) if tool_calls else None,
    )
