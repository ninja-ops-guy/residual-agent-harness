"""Track 3: Trajectory Regression — record, store, and replay execution traces.

Consumes on_run_closed hook. Records structural traces (tool calls,
verdicts, brakes, outcome). Never compares raw model outputs.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from ..core import ContractError, canonical
from ..receipts import hash_id


@dataclass(frozen=True)
class TrajectoryStep:
    """One step in the execution trace."""
    step_number: int
    tool: str
    fingerprint: str
    verdict: str           # "pass" | "fail" | "unknown"
    duration_ms: float = 0.0


@dataclass(frozen=True)
class Trajectory:
    """Complete execution trace for one run."""
    trajectory_hash: str
    goal_spec_hash: str
    steps: tuple[TrajectoryStep, ...]
    brake_trips: tuple[str, ...]
    outcome: str           # RunOutcome value
    recorded_at_ns: int


class TrajectoryRecorder:
    """Records trajectories at run close. Content-addressed storage."""

    def __init__(self, store_dir: str):
        if not store_dir:
            raise ContractError("trajectory store directory is required")
        self._dir = store_dir
        os.makedirs(store_dir, exist_ok=True)

    def record(self, goal_spec_hash: str, steps: list[TrajectoryStep],
               brake_trips: list[str], outcome: str) -> Trajectory:
        """Serialize a run into a content-addressed trajectory."""
        data = {
            "goal_spec_hash": goal_spec_hash,
            "steps": [{k: v for k, v in asdict(s).items() if k != "duration_ms"} for s in steps],
            "brake_trips": brake_trips,
            "outcome": outcome,
        }
        serialized = canonical(data)
        trajectory_hash = hashlib.sha256(serialized.encode()).hexdigest()
        trajectory = Trajectory(
            trajectory_hash=trajectory_hash,
            goal_spec_hash=goal_spec_hash,
            steps=tuple(steps),
            brake_trips=tuple(brake_trips),
            outcome=outcome,
            recorded_at_ns=time.time_ns(),
        )
        path = os.path.join(self._dir, f"{trajectory_hash}.json")
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump(data, f, indent=2, sort_keys=True)
        return trajectory

    def load(self, trajectory_hash: str) -> Optional[dict]:
        """Load a trajectory by its content hash."""
        hash_id(trajectory_hash)
        path = os.path.join(self._dir, f"{trajectory_hash}.json")
        if not os.path.exists(path):
            return None
        try:
            from ..core import strict_json
            with open(path) as f:
                data = strict_json(f.read())
            if hashlib.sha256(canonical(data).encode()).hexdigest() != trajectory_hash:
                return None
            return data
        except (ValueError, OSError):
            return None


class TrajectoryRegressionEngine:
    """Compares live runs against golden trajectories.

    Regression surface: tool call sequence, verdicts, brake trips, outcome.
    NOT raw model outputs — those are non-deterministic.
    """

    def __init__(self, recorder: TrajectoryRecorder):
        self._recorder = recorder

    def evaluate_regression(self, current: Trajectory,
                            golden_hash: str) -> tuple[bool, str]:
        """Compare current trajectory against a golden standard.

        Returns (passed, reason). FAIL if any structural element differs.
        """
        golden_data = self._recorder.load(golden_hash)
        if golden_data is None:
            return False, f"golden trajectory not found: {golden_hash}"

        # Check goal spec match
        if current.goal_spec_hash != golden_data["goal_spec_hash"]:
            return False, "goal_spec_hash mismatch"

        # Check tool call sequence
        golden_tools = [s["tool"] for s in golden_data["steps"]]
        current_tools = [s.tool for s in current.steps]
        if golden_tools != current_tools:
            return False, (
                f"tool sequence mismatch: "
                f"golden={golden_tools}, current={current_tools}"
            )

        if ([s["fingerprint"] for s in golden_data["steps"]] != [s.fingerprint for s in current.steps]
                or [s["step_number"] for s in golden_data["steps"]] != [s.step_number for s in current.steps]):
            return False, "action fingerprint or logical step mismatch"

        # Check verdicts
        golden_verdicts = [s["verdict"] for s in golden_data["steps"]]
        current_verdicts = [s.verdict for s in current.steps]
        if golden_verdicts != current_verdicts:
            return False, (
                f"verdict mismatch: "
                f"golden={golden_verdicts}, current={current_verdicts}"
            )

        # Check brake trips
        if list(current.brake_trips) != golden_data["brake_trips"]:
            return False, (
                f"brake trip mismatch: "
                f"golden={golden_data['brake_trips']}, current={list(current.brake_trips)}"
            )

        # Check outcome
        if current.outcome != golden_data["outcome"]:
            return False, (
                f"outcome mismatch: "
                f"golden={golden_data['outcome']}, current={current.outcome}"
            )

        return True, "trajectory matches golden standard"
