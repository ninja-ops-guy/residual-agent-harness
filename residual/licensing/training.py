"""Role-specific training progress tracking with hands-on exercises (ENT7-R5, ENT7-R6)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..core import ContractError, identifier


class Role(str, Enum):
    OPERATOR = "operator"        # task execution, HITL approval, brake response
    ADMINISTRATOR = "administrator"  # configuration, module management, troubleshooting
    DEVELOPER = "developer"      # module development, engine adapter development
    AUDITOR = "auditor"          # receipt verification, compliance reporting


# Required hands-on exercises per role; every exercise MUST run against a
# sandboxed Residual instance (ENT7-R6).
REQUIRED_EXERCISES = {
    Role.OPERATOR: ("execute_task", "approve_hitl_challenge", "respond_to_brake"),
    Role.ADMINISTRATOR: ("configure_station", "install_module_with_rollback",
                         "diagnose_station_failure"),
    Role.DEVELOPER: ("build_module", "write_engine_adapter"),
    Role.AUDITOR: ("verify_receipt_chain", "generate_compliance_report"),
}


@dataclass
class TrainingRecord:
    """Per-user training progress; completion requires hands-on exercises
    executed in a sandbox (ENT7-R6)."""
    user_id: str
    role: Role
    videos_watched: set[str] = field(default_factory=set)
    exercises_completed: dict[str, bool] = field(default_factory=dict)

    def __post_init__(self):
        identifier(self.user_id)

    def watch_video(self, lesson: str) -> None:
        self.videos_watched.add(lesson)

    def record_exercise(self, exercise: str, sandboxed: bool) -> None:
        if exercise not in REQUIRED_EXERCISES[self.role]:
            raise ContractError(
                f"exercise {exercise} is not part of the {self.role.value} curriculum")
        if not sandboxed:
            raise ContractError(
                "training exercises MUST run against a sandboxed Residual instance (ENT7-R6)")
        self.exercises_completed[exercise] = True

    def completed(self) -> bool:
        """True only when ALL required hands-on exercises are done.
        Video-only training is insufficient (ENT7-R6)."""
        return set(REQUIRED_EXERCISES[self.role]) == set(self.exercises_completed)

    def progress(self) -> dict:
        required = set(REQUIRED_EXERCISES[self.role])
        done = set(self.exercises_completed)
        return {
            "user_id": self.user_id,
            "role": self.role.value,
            "exercises_completed": sorted(done),
            "exercises_remaining": sorted(required - done),
            "videos_watched": sorted(self.videos_watched),
            "completed": self.completed(),
        }
