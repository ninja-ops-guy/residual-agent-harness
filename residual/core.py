"""Small, explicit contracts. No model-generated code is executed."""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


class ContractError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def strict_json(text: str) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ContractError("duplicate JSON key")
            result[key] = value
        return result

    def invalid(_):
        raise ContractError("non-finite JSON number")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)


def identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_.-]{0,95}", value):
        raise ContractError("invalid identifier")
    return value


def positive_int(value: Any, name: str, allow_zero: bool = False) -> int:
    if type(value) is not int or value < (0 if allow_zero else 1):
        raise ContractError(f"{name} must be a {'nonnegative' if allow_zero else 'positive'} integer")
    return value


@dataclass(frozen=True)
class Artifact:
    id: str
    text: str
    cloud: bool = False

    def __post_init__(self):
        identifier(self.id)
        if not isinstance(self.text, str) or type(self.cloud) is not bool:
            raise ContractError("artifact text/cloud types are invalid")

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    @property
    def lines(self) -> list[str]:
        return self.text.splitlines(keepends=True) or [""]

    def excerpt(self, start: int, end: int) -> dict:
        positive_int(start, "start_line")
        positive_int(end, "end_line")
        if end < start or end > len(self.lines):
            raise ContractError("evidence window outside artifact")
        text = "".join(self.lines[start - 1:end])
        return {"artifact_id": self.id, "artifact_sha256": self.sha256,
                "start_line": start, "end_line": end, "text": text,
                "excerpt_sha256": hashlib.sha256(text.encode()).hexdigest()}


@dataclass(frozen=True)
class Obligation:
    id: str
    instruction: str
    check: str
    evidence: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    parameters: dict = field(default_factory=dict)
    solver: str | None = None
    cloud: bool = True

    def __post_init__(self):
        identifier(self.id)
        for part in self.check.split(":"):
            identifier(part)
        if self.check.count(":") > 1:
            raise ContractError("invalid verifier name")
        if not isinstance(self.instruction, str) or not self.instruction.strip():
            raise ContractError("obligation requires an instruction")
        if type(self.cloud) is not bool or not isinstance(self.parameters, dict):
            raise ContractError("obligation cloud/parameters types are invalid")
        canonical(self.parameters)
        if len(set(self.evidence)) != len(self.evidence) or len(set(self.depends_on)) != len(self.depends_on):
            raise ContractError("duplicate obligation dependencies")


@dataclass(frozen=True)
class Task:
    id: str
    goal: str
    artifacts: dict[str, Artifact]
    obligations: tuple[Obligation, ...]
    structure: str | None = None

    def __post_init__(self):
        identifier(self.id)
        if not isinstance(self.goal, str) or not self.goal.strip() or not self.obligations:
            raise ContractError("task requires a goal and obligations")
        ids = [o.id for o in self.obligations]
        if len(ids) != len(set(ids)):
            raise ContractError("duplicate obligation id")
        for key, artifact in self.artifacts.items():
            if key != artifact.id:
                raise ContractError("artifact key/id mismatch")
        if self.structure is not None and (not isinstance(self.structure, str) or self.structure not in self.artifacts):
            raise ContractError("unknown structural artifact")
        for o in self.obligations:
            if set(o.evidence) - self.artifacts.keys() or set(o.depends_on) - set(ids):
                raise ContractError("unknown artifact or dependency")
        resolved = set()
        while len(resolved) < len(ids):
            ready = {o.id for o in self.obligations if set(o.depends_on) <= resolved}
            if not ready - resolved:
                raise ContractError("obligation dependency cycle")
            resolved |= ready

    @property
    def by_id(self) -> dict[str, Obligation]:
        return {o.id: o for o in self.obligations}

    def cloud_allowed(self, node_id: str) -> bool:
        o = self.by_id[node_id]
        return (o.cloud and all(self.artifacts[a].cloud for a in o.evidence)
                and all(self.cloud_allowed(d) for d in o.depends_on))

    @classmethod
    def load(cls, path: str | Path) -> Task:
        path = Path(path).resolve()
        data = strict_json(path.read_text(encoding="utf-8"))
        if set(data) - {"id", "goal", "artifacts", "obligations", "structure"}:
            raise ContractError("unknown task keys")
        artifacts = {}
        total = 0
        for spec in data.get("artifacts", []):
            if set(spec) - {"id", "path", "text", "cloud"} or ("path" in spec) == ("text" in spec):
                raise ContractError("artifact requires exactly one of path/text")
            if "path" in spec:
                source = (path.parent / spec["path"]).resolve()
                if not source.is_relative_to(path.parent):
                    raise ContractError("artifact path escapes task directory")
                if source.stat().st_size > 8_000_000:
                    raise ContractError("artifact exceeds 8 MB")
                text = source.read_text(encoding="utf-8")
            else:
                text = spec["text"]
            artifact = Artifact(spec["id"], text, spec.get("cloud", False))
            total += len(text.encode())
            if total > 32_000_000:
                raise ContractError("task evidence exceeds 32 MB")
            if artifact.id in artifacts:
                raise ContractError("duplicate artifact id")
            artifacts[artifact.id] = artifact
        obligations = []
        for spec in data["obligations"]:
            spec = dict(spec)
            for key in ("evidence", "depends_on"):
                spec[key] = tuple(spec.get(key, []))
            obligations.append(Obligation(**spec))
        return cls(data["id"], data["goal"], artifacts, tuple(obligations), data.get("structure"))


@dataclass(frozen=True)
class Verdict:
    status: str
    code: str
    message: str = ""

    def __post_init__(self):
        if self.status not in {"pass", "fail", "unknown"}:
            raise ContractError("invalid verifier status")

    @classmethod
    def passed(cls):
        return cls("pass", "contract_satisfied")

    @classmethod
    def fail(cls, code: str, message: str = ""):
        return cls("fail", code, message)


@dataclass(frozen=True)
class Context:
    obligation: Obligation
    _artifacts: dict[str, Artifact]
    _accepted: dict[str, Any]

    def evidence(self, artifact_id: str) -> str:
        if artifact_id not in self.obligation.evidence:
            raise ContractError("verifier accessed undeclared evidence")
        return self._artifacts[artifact_id].text

    def dependency(self, node_id: str) -> Any:
        if node_id not in self.obligation.depends_on:
            raise ContractError("verifier accessed undeclared dependency")
        # Plugins cannot mutate a previously accepted value through this interface.
        return strict_json(canonical(self._accepted[node_id]))


Check = Callable[[Any, Context], Verdict]
Solver = Callable[[Context], Any]


class Registry:
    """Plugins are trusted Python code, never model-supplied functions."""
    def __init__(self):
        self.checks: dict[str, tuple[str, Check]] = {}
        self.identities: dict = {}
        self.solvers: dict[str, Solver] = {}
        self.providers: dict[str, Callable] = {}

    def check(self, name: str, function: Check, revision: str, *, identity=None, check_type="mechanical"):
        for part in name.split(":"):
            identifier(part)
        if name.count(":") > 1:
            raise ContractError("invalid verifier name")
        if name in self.checks or not revision:
            raise ContractError("duplicate check or missing revision")
        if identity is not None:
            from .extensions import VerifierRevision
            if not isinstance(identity, VerifierRevision) or check_type not in {"mechanical", "structural", "judge"}:
                raise ContractError("invalid verifier identity")
            self.identities[name] = (identity, check_type)
        self.checks[name] = (revision, function)

    def solver(self, name: str, function: Solver):
        identifier(name)
        if name in self.solvers:
            raise ContractError("duplicate solver")
        self.solvers[name] = function

    def provider(self, name: str, factory: Callable):
        identifier(name)
        if name in self.providers:
            raise ContractError("duplicate provider")
        self.providers[name] = factory


def json_pointer(data: Any, pointer: str) -> Any:
    if pointer == "":
        return data
    if not pointer.startswith("/"):
        raise ContractError("JSON pointer must start with /")
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        data = data[int(token)] if isinstance(data, list) else data[token]
    return data


def register_builtins(registry: Registry):
    from .extensions import VerifierRevision
    identity = VerifierRevision.from_artifact(__file__, configuration={}, policy={"declared_evidence_only": True})
    def extract(ctx):
        p = ctx.obligation.parameters
        return json_pointer(strict_json(ctx.evidence(p["artifact"])), p.get("pointer", ""))

    def sum_values(ctx):
        values = extract(ctx)
        if not isinstance(values, list) or any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ContractError("sum requires finite JSON numbers")
        return sum(values)

    def same_as(compute):
        def check(value, ctx):
            return Verdict.passed() if canonical(value) == canonical(compute(ctx)) else Verdict.fail(
                "value_mismatch", "Recompute the requested value from the declared evidence.")
        return check

    registry.check("json_value", same_as(extract), "1", identity=identity)
    registry.check("json_sum", same_as(sum_values), "1", identity=identity)
    registry.solver("json_value", extract)
    registry.solver("json_sum", sum_values)

    def transition_plan(value, ctx):
        """Validate a proposed plan by simulation, without searching for a plan."""
        spec = extract(ctx)
        if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
            return Verdict.fail("plan_type", "Return a JSON array of action IDs in execution order.")
        if not 0 < len(value) <= spec.get("max_steps", 32):
            return Verdict.fail("plan_length", "The plan must have between one and max_steps actions.")
        state = dict(spec["initial"])
        actions = spec["actions"]
        goal = spec["goal"]
        if not isinstance(actions, dict) or not isinstance(goal, dict) or not goal:
            raise ContractError("plan requires action definitions and a nonempty goal")

        def matches(pattern):
            return all(key in state and canonical(state[key]) == canonical(val) for key, val in pattern.items())

        forbidden = spec.get("forbidden", [])
        if any(matches(pattern) for pattern in forbidden):
            return Verdict("unknown", "initial_state_forbidden", "The task begins in a forbidden state.")
        for i, action_id in enumerate(value):
            if action_id not in actions:
                return Verdict.fail("unknown_action", f"Step {i + 1} references an action absent from the declared action map.")
            action = actions[action_id]
            if not matches(action.get("requires", {})):
                return Verdict.fail("precondition_failed", f"Step {i + 1} has an unsatisfied precondition. Revise the action ordering.")
            state.update(action.get("sets", {}))
            if any(matches(pattern) for pattern in forbidden):
                return Verdict.fail("forbidden_state", f"Step {i + 1} enters a forbidden state.")
        return Verdict.passed() if matches(goal) else Verdict.fail("goal_unsatisfied", "The simulated final state does not satisfy the goal.")

    def dependency_count(ctx):
        value = ctx.dependency(ctx.obligation.parameters["dependency"])
        if not isinstance(value, (list, dict, str)):
            raise ContractError("dependency_count requires a collection")
        return len(value)

    registry.check("transition_plan", transition_plan, "1")
    registry.check("dependency_count", same_as(dependency_count), "1")
    registry.solver("dependency_count", dependency_count)

# ---------------------------------------------------------------------------
# Normative vocabulary (AUTH_INVARIANTS.md; runner design §9).
# ---------------------------------------------------------------------------

FAILURE_CODES = (
    "AMBIGUOUS_ACCEPTANCE_CONDITION",
    "UNBOUND_EVIDENCE_SOURCE",
    "UNRESOLVED_AUTHORITY",
    "UNPROVEN_ACCEPTANCE",
    "STALE_CONTRACT",
    "UNAUTHORIZED_CONTRACT_REINTERPRETATION",
    "UNAPPROVED_ACTION",
    "IMPLICIT_AUTHORITY_COERCION",
)

FAIL_CLOSED_STATES = (
    "NO_AUTHORITY_CHANGE",
    "NO_EXECUTION",
    "NO_IMPLICIT_DEFAULT",
    "NO_PROMOTION",
    "STALE_CONTRACT",
    "UNPROVEN",
)

# Fixed pipeline precedence (AUTH_INVARIANTS.md, compound-attack rule):
# the earliest-triggered invariant in this order is the primary code.
PRECEDENCE = (
    "INV-AUTH-AMB-005",
    "INV-AUTH-CTR-004",
    "INV-AUTH-IDN-002",
    "INV-AUTH-AUT-006",
    "INV-AUTH-EVD-001",
    "INV-AUTH-ACC-003",
)

CODE_TO_INVARIANT = {
    "AMBIGUOUS_ACCEPTANCE_CONDITION": "INV-AUTH-AMB-005",
    "UNAUTHORIZED_CONTRACT_REINTERPRETATION": "INV-AUTH-CTR-004",
    "STALE_CONTRACT": "INV-AUTH-CTR-004",
    "UNRESOLVED_AUTHORITY": "INV-AUTH-IDN-002",
    "UNAPPROVED_ACTION": "INV-AUTH-AUT-006",
    "UNBOUND_EVIDENCE_SOURCE": "INV-AUTH-EVD-001",
    "UNPROVEN_ACCEPTANCE": "INV-AUTH-ACC-003",
    "IMPLICIT_AUTHORITY_COERCION": "INV-AUTH-000",
}

SOURCE_TARGET = {
    "INV-AUTH-EVD-001": ("OBSERVATION", "EVIDENCE"),
    "INV-AUTH-IDN-002": ("IDENTITY", "AUTHORITY"),
    "INV-AUTH-ACC-003": ("TEST_RESULT", "ACCEPTANCE"),
    "INV-AUTH-CTR-004": ("INTERPRETATION", "CONTRACT"),
    "INV-AUTH-AMB-005": ("AMBIGUOUS_INTENT", "EXECUTABLE_AUTHORITY"),
    "INV-AUTH-AUT-006": ("SUGGESTION", "AUTHORIZATION"),
}


def _primary_code(triggered_codes: tuple[str, ...]) -> str:
    """Earliest-triggered invariant in pipeline precedence order."""
    rank = {inv: i for i, inv in enumerate(PRECEDENCE)}
    best: str | None = None
    best_rank = len(PRECEDENCE)
    for code in triggered_codes:
        inv = CODE_TO_INVARIANT.get(code)
        if inv is None or inv == "INV-AUTH-000":
            raise ValueError(f"unknown or generic code in triggered set: {code!r}")
        if rank[inv] < best_rank:
            best, best_rank = code, rank[inv]
    if best is None:  # pragma: no cover - guarded by validation below
        raise ValueError("empty triggered_codes")
    return best


class AuthorityCoercionRejected(ContractError):
    """A rejection at an AUTH coercion boundary, with its type attached.

    Attributes:
        code: primary failure code (earliest in pipeline precedence).
        triggered_codes: all triggered codes, in invariant-ID order.
        fail_closed_state: the fail-closed state the system entered.
        invariant_id: invariant of the primary code.
        reason: human-readable explanation (also the exception message).
    """

    def __init__(
        self,
        *,
        code: str,
        fail_closed_state: str,
        reason: str = "",
        triggered_codes: tuple[str, ...] | list[str] = (),
        invariant_id: str | None = None,
    ) -> None:
        if code not in FAILURE_CODES:
            raise ValueError(f"unknown failure code: {code!r}")
        if fail_closed_state not in FAIL_CLOSED_STATES:
            raise ValueError(f"unknown fail-closed state: {fail_closed_state!r}")
        triggered = tuple(triggered_codes) if triggered_codes else (code,)
        for t in triggered:
            if t not in FAILURE_CODES:
                raise ValueError(f"unknown triggered failure code: {t!r}")
        primary = _primary_code(triggered)
        # triggered_codes are stored in invariant-ID order (deterministic).
        ordered = tuple(sorted(triggered, key=lambda c: CODE_TO_INVARIANT[c]))
        self.code: str = primary
        self.triggered_codes: tuple[str, ...] = ordered
        self.fail_closed_state: str = fail_closed_state
        self.invariant_id: str = invariant_id or CODE_TO_INVARIANT[primary]
        if self.invariant_id != CODE_TO_INVARIANT[primary]:
            raise ValueError(
                f"invariant_id {self.invariant_id!r} does not match "
                f"primary code {primary!r}"
            )
        self.reason: str = reason or primary
        super().__init__(self.reason)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"AuthorityCoercionRejected(code={self.code!r}, "
            f"triggered_codes={self.triggered_codes!r}, "
            f"fail_closed_state={self.fail_closed_state!r}, "
            f"invariant_id={self.invariant_id!r})"
        )
