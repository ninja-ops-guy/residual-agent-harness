"""VQ-R6: minimal local frozen-workload fixture for verifier benchmarking.

Swarm A (EVAL-001) owns the full FrozenWorkload schema. This module
defines a *labeled-defect fixture* — the minimal slice VQ-002 needs to
measure verifier recall against known-defect cases. Every case carries
an immutable ground-truth label; defect cases (`ground_truth: false`)
are mandatory, because recall/false-accept cannot be measured without
them.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from residual.core import ContractError
from .identity import hash_payload

FIXTURE_SCHEMA = "residual.vq.frozen_fixture.v1"


@dataclass(frozen=True)
class FixtureCase:
    case_id: str
    artifact: Any            # candidate artifact presented to the verifier
    ground_truth: bool       # True = correct, False = KNOWN DEFECT
    defect_kind: str = ""    # e.g. "wrong_value", "missing_field"
    safety_critical: bool = False

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "artifact": self.artifact,
            "ground_truth": self.ground_truth,
            "defect_kind": self.defect_kind,
            "safety_critical": self.safety_critical,
        }


@dataclass(frozen=True)
class FrozenWorkloadFixture:
    """Immutable, hash-bound labeled-defect fixture."""
    name: str
    cases: tuple[FixtureCase, ...]

    def __post_init__(self):
        if not self.name:
            raise ContractError("fixture name required")
        if not self.cases:
            raise ContractError("fixture must contain at least one case")
        ids = [c.case_id for c in self.cases]
        if len(set(ids)) != len(ids):
            raise ContractError("duplicate case_id in fixture")
        if not any(not c.ground_truth for c in self.cases):
            raise ContractError(
                "VQ-R6: fixture must include known-defect cases to measure recall")
        if not any(c.ground_truth for c in self.cases):
            raise ContractError("fixture must include correct cases")

    @property
    def fixture_hash(self) -> str:
        return hash_payload({
            "schema": FIXTURE_SCHEMA,
            "name": self.name,
            "cases": [c.to_dict() for c in self.cases],
        })

    @property
    def defect_cases(self) -> tuple[FixtureCase, ...]:
        return tuple(c for c in self.cases if not c.ground_truth)

    def to_dict(self) -> dict:
        return {
            "schema": FIXTURE_SCHEMA,
            "name": self.name,
            "fixture_hash": self.fixture_hash,
            "cases": [c.to_dict() for c in self.cases],
        }


def load_frozen_fixture(payload: dict) -> FrozenWorkloadFixture:
    """Validate and load a fixture from a JSON-compatible dict."""
    if payload.get("schema") != FIXTURE_SCHEMA:
        raise ContractError(f"unsupported fixture schema: {payload.get('schema')}")
    cases = tuple(FixtureCase(
        case_id=c["case_id"],
        artifact=c["artifact"],
        ground_truth=bool(c["ground_truth"]),
        defect_kind=c.get("defect_kind", ""),
        safety_critical=bool(c.get("safety_critical", False)),
    ) for c in payload["cases"])
    fixture = FrozenWorkloadFixture(name=payload["name"], cases=cases)
    declared = payload.get("fixture_hash")
    if declared is not None and declared != fixture.fixture_hash:
        raise ContractError("fixture hash mismatch: payload was modified")
    return fixture


def dumps_fixture(fixture: FrozenWorkloadFixture) -> str:
    return json.dumps(fixture.to_dict(), indent=2, sort_keys=True)


def loads_fixture(text: str) -> FrozenWorkloadFixture:
    return load_frozen_fixture(json.loads(text))
