"""EVAL-R1: versioned FrozenWorkload schema with an immutable workload hash."""
from __future__ import annotations

from dataclasses import dataclass

from ..core import ContractError, digest, identifier

SCHEMA_VERSION = "residual.frozen-workload.v1"

_VALID_SLICES = ("development", "evaluation")


@dataclass(frozen=True)
class FrozenTask:
    """One immutable task in a frozen workload slice.

    ``fault_label`` marks known-defect cases (used for FCR); ``None`` means
    no injected fault is expected for this task.
    """

    task_id: str
    family: str
    slice: str
    prompt: str
    expected: str
    fault_label: str | None = None

    def __post_init__(self) -> None:
        identifier(self.task_id)
        identifier(self.family)
        if self.slice not in _VALID_SLICES:
            raise ContractError("task slice must be development or evaluation")
        if not isinstance(self.prompt, str) or not self.prompt:
            raise ContractError("task prompt must be a nonempty string")
        if not isinstance(self.expected, str) or not self.expected:
            raise ContractError("task expected answer must be a nonempty string")
        if self.fault_label is not None:
            identifier(self.fault_label)

    def payload(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "family": self.family,
            "slice": self.slice,
            "prompt": self.prompt,
            "expected": self.expected,
            "fault_label": self.fault_label,
        }


@dataclass(frozen=True)
class FrozenWorkload:
    """Versioned, hash-pinned workload. The hash covers every task field."""

    name: str
    seed: int
    tasks: tuple[FrozenTask, ...]

    def __post_init__(self) -> None:
        identifier(self.name)
        if type(self.seed) is not int or self.seed < 0:
            raise ContractError("workload seed must be a nonnegative integer")
        if not self.tasks:
            raise ContractError("workload requires at least one task")
        ids = [task.task_id for task in self.tasks]
        if len(ids) != len(set(ids)):
            raise ContractError("duplicate task id in workload")
        if not self.slice_tasks("evaluation"):
            raise ContractError("workload requires an evaluation slice")

    @property
    def schema_version(self) -> str:
        return SCHEMA_VERSION

    @property
    def sha256(self) -> str:
        """Immutable workload hash; identical inputs always reproduce it."""
        return digest({
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "seed": self.seed,
            "tasks": [task.payload() for task in self.tasks],
        })

    def slice_tasks(self, slice_name: str) -> tuple[FrozenTask, ...]:
        if slice_name not in _VALID_SLICES:
            raise ContractError("unknown workload slice")
        return tuple(task for task in self.tasks if task.slice == slice_name)

    @property
    def slices(self) -> tuple[str, ...]:
        return tuple(sorted({task.slice for task in self.tasks}))

    def task(self, task_id: str) -> FrozenTask:
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        raise ContractError(f"unknown task id {task_id}")


def development_workload() -> FrozenWorkload:
    """Scripted development fixture (EVAL-R10); never a live-model claim."""
    tasks: list[FrozenTask] = []
    # Known-defect (fault-labeled) evaluation cases support FCR (EVAL-R6).
    specs = [
        ("arith-01", "arithmetic", "evaluation", "Compute 17 + 25.", "42", None),
        ("arith-02", "arithmetic", "evaluation", "Compute 99 + 1.", "100", None),
        ("arith-03", "arithmetic", "evaluation", "Compute 7 * 8.", "56", "injected_wrong_operand"),
        ("rev-01", "reverse", "evaluation", "Reverse the string abc.", "cba", None),
        ("rev-02", "reverse", "evaluation", "Reverse the string residual.", "laudiser", None),
        ("rev-03", "reverse", "evaluation", "Reverse the string harness.", "ssenrah", "injected_truncation"),
        ("arith-04", "arithmetic", "development", "Compute 2 + 2.", "4", None),
        ("rev-04", "reverse", "development", "Reverse the string dev.", "ved", None),
    ]
    for task_id, family, slice_name, prompt, expected, fault in specs:
        tasks.append(FrozenTask(task_id=task_id, family=family, slice=slice_name,
                                prompt=prompt, expected=expected, fault_label=fault))
    return FrozenWorkload(name="eval001-development-fixture", seed=20240517, tasks=tuple(tasks))


def workload_from_json(text: str) -> FrozenWorkload:
    """Load a frozen workload from a canonical JSON document (CI/live reuse).

    If the document carries a ``sha256`` field it MUST match the recomputed
    immutable workload hash.
    """
    from ..core import strict_json

    data = strict_json(text)
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("invalid frozen workload document")
    if not {"name", "seed", "tasks"} <= set(data) <= {"schema_version", "name", "seed", "tasks", "sha256"}:
        raise ContractError("invalid frozen workload fields")
    tasks = tuple(FrozenTask(**entry) for entry in data["tasks"])
    workload = FrozenWorkload(name=data["name"], seed=data["seed"], tasks=tasks)
    if data.get("sha256") is not None and data["sha256"] != workload.sha256:
        raise ContractError("workload hash mismatch")
    return workload
