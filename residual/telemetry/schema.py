"""Observation schema and validation for SPEC-SWARM-OBS-006.

Raw observations are the authoritative source for every paper-facing metric.
Metric registries and Prometheus exports are derived views only and MUST NOT
be treated as authoritative state.
"""
from __future__ import annotations

import hashlib
import json
import math

OBSERVATION_SCHEMA_VERSION = "obs006.observation.v1"
REPORT_SCHEMA_VERSION = "obs006.report.v1"

# Observation kinds, one per metric family required by OBS-R1.
KIND_EXECUTION = "execution"
KIND_ACCEPTANCE = "acceptance"
KIND_REJECTION = "rejection"
KIND_VERIFICATION = "verification"
KIND_INTEGRATION = "integration"
KIND_CONFLICT = "conflict"
KIND_RETRY = "retry"
KIND_RESOURCE = "resource"
KIND_ORCHESTRATION_TIMING = "orchestration_timing"

ALL_KINDS = (
    KIND_EXECUTION,
    KIND_ACCEPTANCE,
    KIND_REJECTION,
    KIND_VERIFICATION,
    KIND_INTEGRATION,
    KIND_CONFLICT,
    KIND_RETRY,
    KIND_RESOURCE,
    KIND_ORCHESTRATION_TIMING,
)

# Orchestration phases timed separately per OBS-R5.
PHASE_PLANNING = "planning"
PHASE_DISPATCH = "dispatch"
PHASE_CONTEXT_PACKAGING = "context_packaging"
PHASE_WORKER_RUNTIME = "worker_runtime"
PHASE_VERIFICATION = "verification"
PHASE_INTEGRATION = "integration"

ALL_PHASES = (
    PHASE_PLANNING,
    PHASE_DISPATCH,
    PHASE_CONTEXT_PACKAGING,
    PHASE_WORKER_RUNTIME,
    PHASE_VERIFICATION,
    PHASE_INTEGRATION,
)

# Label keys whose values are NEVER allowed into metric labels (OBS-R3).
FORBIDDEN_LABEL_KEYS = frozenset({
    "task_id", "content_id", "content", "prompt", "input", "output",
    "worker_id", "run_id", "session_id", "trace_id", "span_id", "id",
})

# Default bounded allowlist per label key. Anything not listed is folded
# into the overflow bucket (OBS-R3).
OVERFLOW_BUCKET = "__other__"

DEFAULT_LABEL_ALLOWLIST = {
    "task_class": frozenset({"code", "analysis", "retrieval", "synthesis", "unknown"}),
    "outcome": frozenset({"pass", "fail", "rejected", "unknown", "error", "aborted"}),
    "verdict": frozenset({"pass", "fail", "rejected", "unknown"}),
    "reason": frozenset({"policy", "verification", "contract", "timeout", "conflict", OVERFLOW_BUCKET}),
    "result": frozenset({"integrated", "conflicted", "rejected", "aborted"}),
    "conflict_kind": frozenset({"write_write", "stale_lease", "duplicate", "ordering"}),
    "resource": frozenset({"tokens_input", "tokens_output", "cpu_seconds", "wall_seconds"}),
    "phase": frozenset(ALL_PHASES),
}

# Required fields per observation kind. Observations missing any required
# field, or with wrong types, are corrupt/incomplete evidence and MUST be
# rejected by report generation (OBS-R4).
REQUIRED_FIELDS = {
    KIND_EXECUTION: ("kind", "schema_version", "task_class", "outcome", "worker_seconds"),
    KIND_ACCEPTANCE: ("kind", "schema_version", "task_class"),
    KIND_REJECTION: ("kind", "schema_version", "task_class", "reason"),
    KIND_VERIFICATION: ("kind", "schema_version", "task_class", "verdict", "verification_seconds"),
    KIND_INTEGRATION: ("kind", "schema_version", "result", "integration_seconds"),
    KIND_CONFLICT: ("kind", "schema_version", "conflict_kind"),
    KIND_RETRY: ("kind", "schema_version", "task_class", "attempt"),
    KIND_RESOURCE: ("kind", "schema_version", "resource", "amount"),
    KIND_ORCHESTRATION_TIMING: ("kind", "schema_version", "phase", "seconds"),
}

# Optional fields whose absence is counted as missing data (OBS-R6) but
# does not make the observation corrupt.
TRACKED_OPTIONAL_FIELDS = ("task_class", "reason", "correct")


class EvidenceError(ValueError):
    """Raised when raw evidence is incomplete or corrupt (OBS-R4)."""


def validate_observation(obs) -> dict:
    """Validate a raw observation; raise EvidenceError if incomplete/corrupt."""
    if not isinstance(obs, dict):
        raise EvidenceError(f"observation is not a mapping: {type(obs).__name__}")
    kind = obs.get("kind")
    if kind not in ALL_KINDS:
        raise EvidenceError(f"unknown observation kind: {kind!r}")
    if obs.get("schema_version") != OBSERVATION_SCHEMA_VERSION:
        raise EvidenceError(
            f"observation schema_version mismatch: {obs.get('schema_version')!r}"
        )
    for field in REQUIRED_FIELDS[kind]:
        if field not in obs:
            raise EvidenceError(f"observation kind={kind} missing field {field!r}")
    # Type checks for numeric fields: reject bools (bool is a subclass of
    # int) and non-finite floats (NaN/inf poison aggregates and canonical
    # JSON). Fail closed; no coercion.
    for num_field in ("worker_seconds", "verification_seconds", "integration_seconds",
                      "seconds", "amount"):
        if num_field in obs:
            value = obs[num_field]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise EvidenceError(f"field {num_field!r} must be numeric in kind={kind}")
            if isinstance(value, float) and not math.isfinite(value):
                raise EvidenceError(
                    f"field {num_field!r} must be finite in kind={kind}: {value!r}")
    if kind == KIND_RETRY and (isinstance(obs["attempt"], bool)
                               or not isinstance(obs["attempt"], int)):
        raise EvidenceError("retry attempt must be an integer")
    if kind == KIND_ORCHESTRATION_TIMING and obs["phase"] not in ALL_PHASES:
        raise EvidenceError(f"unknown orchestration phase: {obs['phase']!r}")
    return obs


def canonical_json(obj) -> str:
    """Deterministic JSON serialization used for hashing.

    Non-finite floats (NaN/inf) are never emitted: ``allow_nan=False`` makes
    the encoder raise, which is converted to EvidenceError so that a future
    code path bypassing validate_observation still cannot produce invalid
    strict JSON in a hashed evidence artifact.
    """
    try:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False)
    except ValueError as exc:
        raise EvidenceError(
            f"canonical_json refusing to serialize non-finite float: {exc}"
        ) from exc


def hash_object(obj) -> str:
    """SHA-256 hex digest of the canonical JSON encoding."""
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def hash_observations(observations) -> str:
    """Hash a raw observation set deterministically (order-independent)."""
    canonical = sorted(canonical_json(o) for o in observations)
    return hashlib.sha256("\n".join(canonical).encode("utf-8")).hexdigest()
