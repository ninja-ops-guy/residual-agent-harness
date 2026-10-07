"""M2 contract and mediated-attempt accounting; NOT an OS sandbox or launcher.

Filesystem access decisions are lexical policy checks. A production worker must
still run behind an OS-enforced backend and an independently driven watchdog.
This module deliberately contains no subprocess or execution-engine entry point.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import time
from dataclasses import dataclass, fields
from pathlib import PurePosixPath
from typing import Any, Callable, Protocol


class WorkerContractError(ValueError):
    """Invalid contract, plan binding, or operation on a terminal attempt."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,95}", value):
        raise WorkerContractError(f"invalid {name}")
    return value


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise WorkerContractError(f"invalid {name}")
    return value


def _number(value: Any, name: str, minimum: float = 0) -> float:
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value >= minimum
    except OverflowError:
        valid = False
    if not valid:
        raise WorkerContractError(f"invalid {name}")
    return float(value)


def _strings(value: Any, name: str, *, required: bool = False) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)) or any(
        not isinstance(x, str) or not x.strip() for x in value
    ):
        raise WorkerContractError(f"{name} must be a sequence of nonempty strings")
    if len(set(value)) != len(value) or (required and not value):
        raise WorkerContractError(f"empty or duplicate {name}")
    return tuple(value)


def _path(value: str, *, selector: bool = False) -> str:
    """Accept exact relative paths, or an explicit directory prefix ending '/'."""
    if not isinstance(value, str) or not value or any(
        ch in value for ch in "\\:*?[]"
    ) or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise WorkerContractError("invalid workspace path")
    body = value[:-1] if selector and value.endswith("/") else value
    if any(part in {"", ".", ".."} for part in body.split("/")):
        raise WorkerContractError("workspace path must be relative and normalized")
    return value


def _matches(path: str, selector: str) -> bool:
    return path.startswith(selector) if selector.endswith("/") else path == selector


class PlanSource(Protocol):
    """Implemented by the existing ExecutionPlan; no alternate DAG is defined."""
    @property
    def graph_hash(self) -> str: ...
    def canonical_payload(self) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class WorkerContract:
    task_id: str
    worker_id: str
    swarm_id: str
    execution_plan_hash: str
    attempt_id: str
    lease_id: str
    lease_generation: int
    input_commit: str
    workspace_root: str
    inputs: tuple[str, ...]
    allowed_outputs: tuple[str, ...]
    forbidden: tuple[str, ...]
    requirements: tuple[str, ...]
    acceptance: tuple[str, ...]
    dependencies: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    forbidden_tools: tuple[str, ...]
    token_budget: int
    wall_clock_budget_s: float
    max_tool_calls: int
    max_file_writes: int
    memory_limit_mb: int
    engine_hint: str | None = None
    engine_class: str = "local"
    schema_version: str = "factory-worker-contract-v1"

    def __post_init__(self) -> None:
        for name in ("task_id", "worker_id", "swarm_id", "attempt_id", "lease_id"):
            _identifier(getattr(self, name), name)
        if self.schema_version != "factory-worker-contract-v1":
            raise WorkerContractError("unsupported worker contract schema")
        if not isinstance(self.execution_plan_hash, str) or not re.fullmatch(
            r"[0-9a-f]{64}", self.execution_plan_hash
        ):
            raise WorkerContractError("invalid execution_plan_hash")
        if not isinstance(self.input_commit, str) or not re.fullmatch(
            r"(?:[0-9a-f]{40}|[0-9a-f]{64})", self.input_commit
        ):
            raise WorkerContractError("input_commit must be a full Git object ID")
        _integer(self.lease_generation, "lease_generation", 1)
        root = self.workspace_root
        if not isinstance(root, str) or not root.startswith("/") or root == "/" or \
                any(ord(ch) < 32 or ord(ch) == 127 for ch in root) or "\\" in root:
            raise WorkerContractError("workspace_root must be an absolute POSIX path")
        if str(PurePosixPath(root)) != root or ".." in PurePosixPath(root).parts or root.startswith("//"):
            raise WorkerContractError("workspace_root must be normalized")
        for name in ("inputs", "allowed_outputs", "forbidden", "requirements", "acceptance",
                     "dependencies", "allowed_tools", "forbidden_tools"):
            values = _strings(getattr(self, name), name, required=name in {"requirements", "acceptance"})
            if name in {"inputs", "allowed_outputs", "forbidden"}:
                for value in values:
                    _path(value, selector=True)
            elif name != "acceptance":
                for value in values:
                    _identifier(value, name)
            # Defensive copies remove mutable list aliases. These fields are sets.
            object.__setattr__(self, name, tuple(sorted(values)))
        if self.task_id in self.dependencies:
            raise WorkerContractError("self dependency")
        if set(self.allowed_tools) & set(self.forbidden_tools):
            raise WorkerContractError("contradictory tool permissions")
        for name in ("token_budget", "max_tool_calls", "max_file_writes"):
            _integer(getattr(self, name), name)
        _integer(self.memory_limit_mb, "memory_limit_mb", 1)
        wall = _number(self.wall_clock_budget_s, "wall_clock_budget_s")
        if wall <= 0:
            raise WorkerContractError("wall_clock_budget_s must be positive")
        object.__setattr__(self, "wall_clock_budget_s", wall)
        if self.engine_class not in {"local", "cloud", "any"}:
            raise WorkerContractError("invalid engine_class")
        if self.engine_hint is not None and (not isinstance(self.engine_hint, str) or not self.engine_hint.strip()):
            raise WorkerContractError("invalid engine_hint")

    def to_dict(self) -> dict[str, Any]:
        return {f.name: list(v) if isinstance(v := getattr(self, f.name), tuple) else v
                for f in fields(self)}

    @property
    def contract_hash(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkerContract:
        if not isinstance(data, dict) or set(data) - {f.name for f in fields(cls)}:
            raise WorkerContractError("unknown worker contract fields")
        try:
            return cls(**data)
        except TypeError as exc:
            raise WorkerContractError("missing or invalid worker contract fields") from exc

    def assert_matches_plan(self, plan: PlanSource) -> None:
        # Snapshot the existing model's public canonical payload, not its private state.
        payload = json.loads(_canonical(plan.canonical_payload()))
        if _digest(payload) != self.execution_plan_hash or plan.graph_hash != self.execution_plan_hash:
            raise WorkerContractError("worker contract does not match ExecutionPlan.graph_hash")
        tasks = [task for task in payload["tasks"] if task["id"] == self.task_id]
        if len(tasks) != 1:
            raise WorkerContractError("unknown or duplicate plan task")
        task = tasks[0]
        if set(task["requirement_ids"]) != set(self.requirements) or \
                set(task["depends_on"]) != set(self.dependencies):
            raise WorkerContractError("worker task bindings differ from approved plan")
        if task.get("swarm") is not None and task["swarm"] != self.swarm_id:
            raise WorkerContractError("worker swarm differs from approved plan")
        needed = {check for req in payload["requirements"] if req["id"] in self.requirements
                  for check in req["acceptance"]}
        if not needed <= set(self.acceptance):
            raise WorkerContractError("worker contract drops required acceptance criteria")

    def permits_path(self, path: str, *, write: bool = False) -> bool:
        _path(path)
        if type(write) is not bool:
            raise WorkerContractError("write flag must be boolean")
        if any(part.lower() == ".git" for part in path.split("/")):
            return False
        if any(_matches(path, item) for item in self.forbidden):
            return False
        return any(_matches(path, item) for item in (self.allowed_outputs if write else self.inputs))


class ContractViolation(WorkerContractError):
    def __init__(self, observation: dict[str, Any]):
        self.observation = json.loads(_canonical(observation))
        super().__init__(f"worker contract violation: {observation['field']}")


class AttemptGuard:
    """Thread-safe pre-dispatch accounting, not a process sandbox or watchdog.

    observe MUST acknowledge durable storage before returning. terminate must be
    a host-controlled stop hook. No process-kill guarantee is inferred from it.
    Every worker call must be mediated; arbitrary shell engines are unsupported.
    """
    def __init__(self, contract: WorkerContract, *,
                 observe: Callable[[dict[str, Any]], None],
                 terminate: Callable[[], None],
                 clock: Callable[[], float] = time.monotonic):
        if not isinstance(contract, WorkerContract):
            raise WorkerContractError("WorkerContract required")
        self.contract = contract
        self._observe, self._terminate, self._clock = observe, terminate, clock
        self._lock = threading.RLock()
        self._state = "CREATED"
        self._started: float | None = None
        self._counts = {"tokens": 0, "tool_calls": 0, "file_writes": 0}
        self._reservations: dict[str, int] = {}
        self._ticket = 0

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @property
    def usage(self) -> dict[str, int]:
        with self._lock:
            return {**self._counts, "reserved_tokens": sum(self._reservations.values())}

    @property
    def started_at(self) -> float | None:
        """Monotonic start instant recorded by start(); None before it."""
        with self._lock:
            return self._started

    @property
    def deadline(self) -> float | None:
        """The single wall-clock deadline owned by this guard (monotonic).

        The watchdog reads a plain-float snapshot of this value AFTER
        start() returns; it must never compute its own deadline or block on
        this lock in its polling loop.
        """
        with self._lock:
            if self._started is None:
                return None
            return self._started + self.contract.wall_clock_budget_s

    def _event(self, event: str, **data: Any) -> dict[str, Any]:
        return {"event": event, "schema_version": "factory-attempt-event-v1",
                "task_id": self.contract.task_id, "worker_id": self.contract.worker_id,
                "swarm_id": self.contract.swarm_id, "attempt_id": self.contract.attempt_id,
                "lease_id": self.contract.lease_id, "lease_generation": self.contract.lease_generation,
                "execution_plan_hash": self.contract.execution_plan_hash,
                "contract_hash": self.contract.contract_hash, **data}

    def _emit(self, event: str, **data: Any) -> None:
        try:
            self._observe(self._event(event, **data))
        except Exception:
            self._state = "AUDIT_FAILED"
            try:
                self._terminate()
            except Exception:
                pass
            raise

    def start(self) -> None:
        with self._lock:
            if self._state != "CREATED":
                raise WorkerContractError("attempt cannot be started or restarted")
            self._emit("WorkerContractRecorded", contract=self.contract.to_dict())
            try:
                self._started = _number(self._clock(), "monotonic clock")
            except Exception:
                self._violate("resource", "monotonic_clock", {"reason": "clock_unavailable"})
            self._emit("WorkerAttemptStarted")
            self._state = "RUNNING"

    def _violate(self, boundary: str, field: str, action: Any) -> None:
        self._state = "VIOLATED"
        event = self._event("ContractViolation", reason="contract_violation",
                            boundary=boundary, field=field, action=action)
        # Stop first even when the observation sink has failed. Never claim an OS
        # process is dead merely because the contract's state is now terminal.
        try:
            self._terminate()
            event["stop_hook"] = "returned"
        except Exception:
            event["stop_hook"] = "failed"
        try:
            self._observe(event)
        except Exception:
            event["audit_failed"] = True
        raise ContractViolation(event)

    def _active(self) -> None:
        if self._state != "RUNNING":
            raise WorkerContractError("attempt is not running")
        try:
            now = _number(self._clock(), "monotonic clock")
        except Exception:
            self._violate("resource", "monotonic_clock", {"reason": "clock_unavailable"})
        if now < self._started:
            self._violate("resource", "monotonic_clock", {"reason": "clock_regressed"})
        if now - self._started >= self.contract.wall_clock_budget_s:
            self._violate("resource", "wall_clock_budget_s", {"elapsed_s": now - self._started})

    def check_deadline(self) -> None:
        with self._lock:
            self._active()

    def authorize_tool(self, tool: str) -> None:
        with self._lock:
            self._active()
            if tool not in self.contract.allowed_tools or tool in self.contract.forbidden_tools:
                self._violate("tool", "allowed_tools", {"tool": str(tool)[:96]})
            self._counts["tool_calls"] += 1
            if self._counts["tool_calls"] > self.contract.max_tool_calls:
                self._violate("resource", "max_tool_calls", {"count": self._counts["tool_calls"]})
            self._emit("ToolAuthorized", tool=tool)

    def authorize_path(self, path: str, *, write: bool = False) -> None:
        with self._lock:
            self._active()
            try:
                permitted = self.contract.permits_path(path, write=write)
            except WorkerContractError:
                permitted = False
            if not permitted:
                self._violate("filesystem", "allowed_outputs" if write else "inputs",
                              {"path": str(path)[:1024], "write": write})
            if write:
                self._counts["file_writes"] += 1
                if self._counts["file_writes"] > self.contract.max_file_writes:
                    self._violate("resource", "max_file_writes", {"count": self._counts["file_writes"]})
            self._emit("PathAuthorized", path=path, write=write)

    def reserve_tokens(self, maximum_total: int) -> str:
        with self._lock:
            self._active()
            _integer(maximum_total, "maximum_total", 1)
            if self._counts["tokens"] + sum(self._reservations.values()) + maximum_total > self.contract.token_budget:
                self._violate("resource", "token_budget", {"reservation": maximum_total})
            self._ticket += 1
            ticket = f"call-{self._ticket}"
            self._reservations[ticket] = maximum_total
            self._emit("TokensReserved", ticket=ticket, maximum_total=maximum_total)
            return ticket

    def settle_tokens(self, ticket: str, actual_total: int | None) -> None:
        with self._lock:
            self._active()
            if not isinstance(ticket, str) or ticket not in self._reservations:
                self._violate("resource", "token_budget", {"reason": "unknown_or_replayed_reservation"})
            reserved = self._reservations[ticket]
            if type(actual_total) is not int or actual_total < 0:
                self._violate("resource", "token_budget", {"reason": "unknown_usage"})
            if actual_total > reserved:
                self._counts["tokens"] += actual_total
                del self._reservations[ticket]
                self._violate("resource", "token_budget", {"reason": "reservation_exceeded", "reported": actual_total})
            self._counts["tokens"] += actual_total
            del self._reservations[ticket]
            self._emit("TokensSettled", ticket=ticket, actual_total=actual_total)

    def check_memory(self, resident_bytes: int) -> None:
        with self._lock:
            self._active()
            try:
                _integer(resident_bytes, "resident_bytes")
            except WorkerContractError:
                self._violate("resource", "memory_limit_mb", {"reason": "memory_usage_unavailable"})
            if resident_bytes > self.contract.memory_limit_mb * 1024 * 1024:
                self._violate("resource", "memory_limit_mb", {"resident_bytes": resident_bytes})

    def assert_lease(self, lease_id: str, generation: int) -> None:
        with self._lock:
            self._active()
            if type(generation) is not int or (lease_id, generation) != (
                self.contract.lease_id, self.contract.lease_generation
            ):
                self._violate("lease", "lease_generation", {"reason": "stale_lease"})

    def finish(self) -> None:
        with self._lock:
            self._active()
            if self._reservations:
                self._violate("resource", "token_budget", {"reason": "unsettled_usage"})
            self._emit("WorkerCandidateReady", usage=self.usage)
            self._state = "CANDIDATE"  # Not ACCEPTED: only Station may accept.

    def fail(self, boundary: str, field: str, action: Any) -> None:
        """Executor-detected denial; terminal even if the child has already died.

        The executor may kill the child BEFORE calling this method so that a
        blocked audit writer cannot postpone OS termination.
        """
        with self._lock:
            self._active()
            self._violate(boundary, field, action)

    def cancel(self) -> None:
        with self._lock:
            if self._state != "RUNNING":
                return
            self._state = "CANCELLED"
            try:
                self._terminate()
            finally:
                self._emit("WorkerAttemptCancelled")
