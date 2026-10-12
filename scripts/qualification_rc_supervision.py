"""Offline-testable supervision protocol; not an OS watchdog or campaign runner.

Adapters must poll without waiting for the workload. This synchronous controller
cannot preempt an adapter that itself never returns. All observations remain
unqualified until independently implemented/verified external capabilities exist.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re
from typing import Callable, Protocol


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def frozen_copy(value, limit=65536):
    raw = canonical(value)
    if len(raw) > limit:
        raise ValueError("observation_size_limit")
    return json.loads(raw)


def text(value):
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", value):
        raise ValueError("invalid_identity")


def sha256(value):
    if type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("invalid_digest")


def moment(value):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError("invalid_monotonic_time")
    return value


def fields(value, names):
    if type(value) is not dict or set(value) != set(names):
        raise ValueError("invalid_observation_fields")


@dataclass(frozen=True)
class ProcessIdentity:
    host: str
    pid: int
    birth_token: str
    image_sha256: str

    def __post_init__(self):
        text(self.host); text(self.birth_token); sha256(self.image_sha256)
        if type(self.pid) is not int or not 0 < self.pid <= 2**63-1:
            raise ValueError("invalid_process_id")


@dataclass(frozen=True)
class Task:
    task_id: str
    attempt_id: str
    nonce: str
    sequence: int
    deadline: float
    expected_payload_sha256: str

    def __post_init__(self):
        for value in (self.task_id, self.attempt_id, self.nonce): text(value)
        sha256(self.expected_payload_sha256); moment(self.deadline)
        if type(self.sequence) is not int or not 0 <= self.sequence <= 2**31-1:
            raise ValueError("invalid_task_sequence")


@dataclass(frozen=True)
class Requirements:
    run_id: str
    observer: ProcessIdentity
    target: ProcessIdentity
    driver: ProcessIdentity
    start_at: float
    cadence: float
    maximum_gap: float
    poll_budget: float
    tasks: tuple[Task, ...]

    def __post_init__(self):
        text(self.run_id)
        for identity in (self.observer, self.target, self.driver):
            if type(identity) is not ProcessIdentity:
                raise ValueError("process_identity_required")
        if len({(p.host, p.pid) for p in (self.observer, self.target, self.driver)}) != 3:
            raise ValueError("distinct_observer_target_driver_required")
        for value in (self.start_at, self.cadence, self.maximum_gap, self.poll_budget): moment(value)
        if not 0 < self.poll_budget <= self.cadence <= self.maximum_gap:
            raise ValueError("invalid_timing_requirements")
        if type(self.tasks) is not tuple or not 1 <= len(self.tasks) <= 1024:
            raise ValueError("task_plan_required")
        nonces, correlations = set(), set()
        previous = self.start_at
        for index, task in enumerate(self.tasks):
            if type(task) is not Task or task.sequence != index or task.deadline <= previous:
                raise ValueError("invalid_task_plan")
            if task.nonce in nonces or (task.task_id, task.attempt_id) in correlations:
                raise ValueError("duplicate_task_plan")
            nonces.add(task.nonce); correlations.add((task.task_id, task.attempt_id))
            previous = task.deadline


class ProcessHandle(Protocol):
    def poll(self) -> dict:
        """Return identity/state immediately; never wait for the process."""


class DriverHandle(Protocol):
    def poll(self, task: Task) -> dict:
        """Read-only poll; preserve a ready outcome for repeated boundary checks."""


class TimingFault(Exception):
    CODES = {"invalid_monotonic_time", "monotonic_regression", "adapter_poll_budget_exceeded", "observation_gap"}

    def __init__(self, code):
        self.code = code if code in self.CODES else "invalid_monotonic_time"


class LatchedFailure(Exception):
    """Stop an in-flight tick without replacing its first failure."""


class Supervisor:
    """Single-use state machine. No resume, time credit, process start or kill API."""
    MISSING_CAPABILITIES = (
        "os_process_identity_unverified", "adapter_poll_preemption_unverified",
        "external_watchdog_unverified", "workload_attribution_unverified",
        "cross_process_observer_lease_unverified",
    )

    def __init__(self, requirements: Requirements, *, clock: Callable[[], float],
                 observer: ProcessHandle, target: ProcessHandle, driver: DriverHandle,
                 resume_state=None, prior_elapsed=0):
        if type(requirements) is not Requirements:
            raise ValueError("external_requirements_required")
        if resume_state is not None or type(prior_elapsed) not in (int, float) or prior_elapsed != 0:
            raise ValueError("resume_or_time_accumulation_forbidden")
        self.requirements = requirements
        self._clock, self._observer, self._target, self._driver = clock, observer, target, driver
        self._last_clock = None
        self._last_tick = None
        # start_at bounds first coverage; ticks never reset observation history.
        self._last_observation = {role: requirements.start_at
                                  for role in ("observer", "target", "driver")}
        self._index = 0
        self._seen_results = set()
        self._accepted = []
        self._first_failure = None
        self._complete = False

    def report(self):
        return frozen_copy({"schema": "residual.rc-supervision.observations.v1",
            "run_id": self.requirements.run_id,
            "requirements_sha256": hashlib.sha256(canonical(asdict(self.requirements))).hexdigest(),
            "state": "failed" if self._first_failure else "observed_complete" if self._complete else "pending",
            "first_failure": self._first_failure, "accepted": self._accepted,
            "accepted_result_count": len(self._accepted), "rc_qualified": False,
            "missing_capabilities": self.MISSING_CAPABILITIES}, limit=2*1024*1024)

    def _fail(self, reason):
        if self._first_failure is None:
            self._first_failure = {"reason": reason, "task_index": self._index,
                                   "last_monotonic": self._last_clock}
        return self.report()

    def cancel(self):
        # Cancellation invalidates observations; it does not assert target termination.
        return self._fail("cancelled_by_caller")

    def interrupt(self):
        return self._fail("observer_interrupted")

    def _check_active(self):
        if self._first_failure is not None:
            raise LatchedFailure()

    def _check_coverage(self, now):
        if any(now-last > self.requirements.maximum_gap
               for last in self._last_observation.values()):
            raise TimingFault("observation_gap")

    def _now(self):
        try:
            raw = self._clock()
            self._check_active()
            now = moment(raw)
        except (ValueError, OverflowError):
            raise TimingFault("invalid_monotonic_time") from None
        if self._last_clock is not None and now < self._last_clock:
            raise TimingFault("monotonic_regression")
        self._last_clock = now
        return now

    def _poll(self, callback, role):
        started = self._now()
        raw = callback()
        self._check_active()
        result = frozen_copy(raw)
        finished = self._now()
        if finished-started > self.requirements.poll_budget:
            raise TimingFault("adapter_poll_budget_exceeded")
        if finished-self._last_observation[role] > self.requirements.maximum_gap:
            raise TimingFault("observation_gap")
        return result, finished

    def _observe(self, callback, expected, role, driver=False):
        observation, finished = self._poll(callback, role)
        reason = self._process(observation, expected, role, driver=driver)
        self._check_active()
        if reason is None:
            self._last_observation[role] = finished
        return observation, finished, reason

    def _process(self, observation, expected, role, driver=False):
        fields(observation, ("identity", "state", "outcome") if driver else ("identity", "state"))
        identity = observation["identity"]
        if observation["state"] == "absent" and identity is None:
            return role+"_absent"
        fields(identity, ("host", "pid", "birth_token", "image_sha256"))
        # Validate types too: True must not compare equal to PID 1.
        ProcessIdentity(**identity)
        if identity != asdict(expected):
            return role+"_replaced"
        if observation["state"] not in ("alive", "exited", "absent", "cancelled", "failed"):
            return role+"_state_invalid"
        if observation["state"] != "alive":
            return role+"_"+observation["state"]
        return None

    def tick(self):
        if self._first_failure or self._complete:
            return self.report()
        try:
            now = self._now()
            origin = self.requirements.start_at if self._last_tick is None else self._last_tick
            if now < origin:
                return self._fail("monotonic_regression")
            self._check_coverage(now)
            if self._last_tick is not None and now-origin < self.requirements.cadence:
                return self._fail("cadence_violation")
            self._last_tick = now
            task = self.requirements.tasks[self._index]
            if now >= task.deadline:
                return self._fail("task_deadline_missed")
            for handle, expected, role in ((self._observer, self.requirements.observer, "observer"),
                                           (self._target, self.requirements.target, "target")):
                observation, finished, reason = self._observe(handle.poll, expected, role)
                if reason: return self._fail(reason)
                if finished >= task.deadline: return self._fail("task_deadline_missed")
            observation, finished, reason = self._observe(
                lambda: self._driver.poll(task), self.requirements.driver, "driver", driver=True)
            if reason: return self._fail(reason)
            if finished >= task.deadline: return self._fail("task_deadline_missed")
            outcome = observation["outcome"]
            if outcome is None:
                self._check_coverage(finished)
                return self.report()
            fields(outcome, ("task_id", "attempt_id", "nonce", "sequence", "result_id", "status",
                             "payload", "target", "driver"))
            text(outcome["result_id"])
            if outcome["result_id"] in self._seen_results:
                return self._fail("duplicate_result")
            if (type(outcome["sequence"]) is not int or outcome["sequence"] != task.sequence or
                    any(outcome[k] != getattr(task, k) for k in ("task_id", "attempt_id", "nonce"))):
                return self._fail("stale_or_wrong_attempt_result")
            for key, identity in (("target", self.requirements.target), ("driver", self.requirements.driver)):
                fields(outcome[key], ("host", "pid", "birth_token", "image_sha256"))
                ProcessIdentity(**outcome[key])
                if outcome[key] != asdict(identity):
                    return self._fail("result_process_identity_mismatch")
            if outcome["status"] != "succeeded":
                return self._fail("task_result_not_successful")
            payload_digest = hashlib.sha256(canonical(outcome["payload"])).hexdigest()
            if payload_digest != task.expected_payload_sha256:
                return self._fail("result_payload_mismatch")
            # The task driver may have run while target/observer exited/restarted.
            for handle, expected, role in ((self._observer, self.requirements.observer, "observer"),
                                           (self._target, self.requirements.target, "target")):
                boundary, finished, reason = self._observe(handle.poll, expected, role)
                if reason: return self._fail(reason)
                if finished >= task.deadline: return self._fail("task_deadline_missed")
            boundary, finished, reason = self._observe(
                lambda: self._driver.poll(task), self.requirements.driver, "driver", driver=True)
            if reason: return self._fail(reason)
            if finished >= task.deadline: return self._fail("task_deadline_missed")
            if canonical(boundary["outcome"]) != canonical(outcome):
                return self._fail("driver_result_changed")
            self._check_coverage(finished)
            self._check_active()
            self._accepted.append(frozen_copy({"task_id": task.task_id, "attempt_id": task.attempt_id,
                "nonce": task.nonce, "sequence": task.sequence, "result_id": outcome["result_id"],
                "payload_sha256": payload_digest, "observed_at": finished}))
            self._seen_results.add(outcome["result_id"])
            self._index += 1
            self._complete = self._index == len(self.requirements.tasks)
            return self.report()
        except LatchedFailure:
            return self.report()
        except KeyboardInterrupt:
            return self._fail("observer_interrupted")
        except TimingFault as exc:
            return self._fail(exc.code)
        except Exception:
            # Only bounded, fixed reason codes; never persist adapter exception text.
            return self._fail("invalid_clock_or_adapter_observation")
