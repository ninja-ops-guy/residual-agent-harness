"""Topology-choice observations for SPEC-SWARM-OTX-003.

OTX-R8: every topology choice emits an observation containing the inputs,
the predicted utility/tax per candidate, the selected topology, and —
once the run completes — the eventual observed result. OTX-R4 attaches a
predicted-vs-observed tax comparison to every completed observation.

Observations are serialised as JSON lines so the stored log can be
replayed exactly (Gate C).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CandidatePrediction:
    topology: str
    predicted_tax: float
    tax_std: float
    predicted_worker_s: float
    predicted_total_s: float
    predicted_reliability: float
    predicted_utility: float

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class ObservedResult:
    timing_breakdown: Dict[str, float]
    observed_tax: float
    observed_total_s: float
    success: bool
    quality_score: float

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class TaxComparison:
    """OTX-R4: predicted vs observed tax for one experimental task."""

    predicted_tax: float
    observed_tax: float
    error: float
    abs_error: float
    within_1_std: bool

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class TopologyObservation:
    observation_id: str
    sequence: int
    inputs: Dict[str, Any]                 # task descriptor + config snapshot
    candidates: List[CandidatePrediction]  # predicted utility/tax per topology
    selected_topology: str
    selection_reason: str                  # "max_utility" | "deployment_threshold"
    model_snapshot: Dict[str, Any]         # estimator state at decision time
    result: Optional[ObservedResult] = None
    comparison: Optional[TaxComparison] = None

    # -- serialisation -----------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "sequence": self.sequence,
            "inputs": self.inputs,
            "candidates": [c.to_dict() for c in self.candidates],
            "selected_topology": self.selected_topology,
            "selection_reason": self.selection_reason,
            "model_snapshot": self.model_snapshot,
            "result": None if self.result is None else self.result.to_dict(),
            "comparison": None if self.comparison is None else self.comparison.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TopologyObservation":
        obs = cls(
            observation_id=d["observation_id"],
            sequence=d["sequence"],
            inputs=d["inputs"],
            candidates=[CandidatePrediction(**c) for c in d["candidates"]],
            selected_topology=d["selected_topology"],
            selection_reason=d["selection_reason"],
            model_snapshot=d["model_snapshot"],
        )
        if d.get("result"):
            obs.result = ObservedResult(**d["result"])
        if d.get("comparison"):
            obs.comparison = TaxComparison(**d["comparison"])
        return obs


class ObservationLog:
    """In-memory observation store with JSONL persistence (OTX-R8, Gate B)."""

    def __init__(self) -> None:
        self._observations: List[TopologyObservation] = []

    def append(self, obs: TopologyObservation) -> None:
        self._observations.append(obs)

    def __len__(self) -> int:
        return len(self._observations)

    def __iter__(self):
        return iter(self._observations)

    def by_id(self, observation_id: str) -> TopologyObservation:
        for o in self._observations:
            if o.observation_id == observation_id:
                return o
        raise KeyError(observation_id)

    def completed(self) -> List[TopologyObservation]:
        return [o for o in self._observations if o.result is not None]

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(o.to_dict(), sort_keys=True) for o in self._observations) + "\n"

    @classmethod
    def from_jsonl(cls, text: str) -> "ObservationLog":
        log = cls()
        for line in text.splitlines():
            line = line.strip()
            if line:
                log.append(TopologyObservation.from_dict(json.loads(line)))
        return log

    def write(self, path: str) -> None:
        if ".." in path:
            raise Exception("Invalid file path")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_jsonl())

    @classmethod
    def read(cls, path: str) -> "ObservationLog":
        if ".." in path:
            raise Exception("Invalid file path")
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_jsonl(fh.read())
