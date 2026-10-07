"""Local stub interfaces for the Residual Studio frontend.

SPEC NOTE (Track H, Swarm 8): the Studio frontend MUST consume the M2 swarm
contract shapes defined in docs/studio/STUDIO_SPECS.md (SPEC-STUDIO-003,
STUDIO-R9..R15). The binding ownership rule forbids this swarm from touching
``residual/swarm/**``, so this module provides local stub dataclasses that
mirror the normative ``WorkerContract`` / ``WorkerReceipt`` shape. When the
real M2 runtime lands, these stubs MUST be replaced by imports of the real
types; the JSON wire shape used by the stub API MUST NOT change.

Requirements covered: STUDIO-R9, STUDIO-R11 (field shape), STUDIO-R25
(panel metrics consumed by the UI).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class WorkerContract:
    """Frozen worker contract (stub of SPEC-STUDIO-003; STUDIO-R9)."""

    task_id: str
    inputs: tuple[str, ...]
    allowed_outputs: tuple[str, ...]
    requirements: tuple[str, ...]
    acceptance: tuple[str, ...]
    dependencies: tuple[str, ...]
    forbidden: tuple[str, ...]
    engine_hint: str | None
    token_budget: int
    wall_clock_budget_s: float

    @classmethod
    def from_dict(cls, data: dict) -> "WorkerContract":
        return cls(
            task_id=str(data["task_id"]),
            inputs=tuple(data.get("inputs", ())),
            allowed_outputs=tuple(data.get("allowed_outputs", ())),
            requirements=tuple(data.get("requirements", ())),
            acceptance=tuple(data.get("acceptance", ())),
            dependencies=tuple(data.get("dependencies", ())),
            forbidden=tuple(data.get("forbidden", ())),
            engine_hint=data.get("engine_hint"),
            token_budget=int(data.get("token_budget", 0)),
            wall_clock_budget_s=float(data.get("wall_clock_budget_s", 0.0)),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class WorkerReceipt:
    """Worker receipt binding per STUDIO-R11 (stub).

    A receipt MUST bind task ID, attempt ID, engine identity/version, node
    identity, input commit, output artifact hashes, requirement verdicts,
    verification results, parent receipt hashes, start/end timestamps,
    resource usage, and final status.
    """

    receipt_id: str
    task_id: str
    attempt_id: str
    engine: str
    engine_version: str
    node_id: str
    input_commit: str
    output_artifacts: dict[str, str]
    requirement_verdicts: dict[str, str]
    verification: dict[str, bool]
    parent_receipts: tuple[str, ...]
    started_at: str
    ended_at: str
    resource_usage: dict[str, float]
    status: str  # accepted | rejected | contract_violation
    supersedes: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "WorkerReceipt":
        return cls(
            receipt_id=str(data["receipt_id"]),
            task_id=str(data["task_id"]),
            attempt_id=str(data["attempt_id"]),
            engine=str(data.get("engine", "stub")),
            engine_version=str(data.get("engine_version", "0.0.0")),
            node_id=str(data.get("node_id", "stub-node")),
            input_commit=str(data.get("input_commit", "")),
            output_artifacts=dict(data.get("output_artifacts", {})),
            requirement_verdicts=dict(data.get("requirement_verdicts", {})),
            verification=dict(data.get("verification", {})),
            parent_receipts=tuple(data.get("parent_receipts", ())),
            started_at=str(data.get("started_at", "")),
            ended_at=str(data.get("ended_at", "")),
            resource_usage=dict(data.get("resource_usage", {})),
            status=str(data.get("status", "accepted")),
            supersedes=data.get("supersedes"),
        )

    def to_dict(self) -> dict:
        value = asdict(self)
        value["parent_receipts"] = list(self.parent_receipts)
        return value

    def hash(self) -> str:
        blob = json.dumps(self.to_dict(), sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()
