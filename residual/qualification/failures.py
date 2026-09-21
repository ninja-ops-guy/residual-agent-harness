from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class FailureClass(str, Enum):
    SUT_DEFECT = "SUT_DEFECT"
    TEST_DEFECT = "TEST_DEFECT"
    ENVIRONMENT_FAILURE = "ENVIRONMENT_FAILURE"
    EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    PROVENANCE_UNKNOWN = "PROVENANCE_UNKNOWN"
    UNCLASSIFIED = "UNCLASSIFIED"


@dataclass(frozen=True)
class FailureObservation:
    gate_id: str
    classification: FailureClass
    summary: str
    evidence: dict[str, Any]
    predecessor_id: str | None = None
    observation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    schema: str = "residual.qualification.failure.v1"

    def to_dict(self) -> dict[str, Any]:
        doc = asdict(self)
        doc["classification"] = self.classification.value
        return doc


def append_failure(path: Path | str, observation: FailureObservation) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(observation.to_dict(), sort_keys=True) + "\n")


def load_failures(path: Path | str) -> list[FailureObservation]:
    path = Path(path)
    if not path.exists():
        return []
    rows: list[FailureObservation] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = json.loads(line)
        if raw.get("schema") != "residual.qualification.failure.v1":
            raise ValueError("unsupported failure ledger schema")
        rows.append(FailureObservation(
            gate_id=raw["gate_id"],
            classification=FailureClass(raw["classification"]),
            summary=raw["summary"],
            evidence=dict(raw.get("evidence") or {}),
            predecessor_id=raw.get("predecessor_id"),
            observation_id=raw["observation_id"],
            observed_at=raw["observed_at"],
        ))
    return rows
